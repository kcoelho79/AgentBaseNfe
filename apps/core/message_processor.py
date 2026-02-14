import logging
import random
from datetime import datetime
from typing import Dict, Optional
from django.conf import settings as django_settings

from apps.core.models import DadosNFSe, Session
from apps.core.reponse_builder import ResponseBuilder
from apps.core.agent_extractor import AIExtractor
from apps.core.session_manager import SessionManager
from apps.core.states import SessionState
from apps.contabilidade.models import UsuarioEmpresa

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Orquestrador de mensagens para emissão de NFSe.

    Suporta dois modos:
    - Legado: AIExtractor faz tudo (extração + resposta)
    - Hibrido: Classificador + Extrator focado + SmartResponseBuilder

    Modo controlado por USE_HYBRID_AI no settings.py ou por telefone em HYBRID_AI_PHONES.
    """


    def __init__(self):
        self.session_manager = SessionManager()
        self.response_builder = ResponseBuilder()

        # Modo legado (sempre disponivel)
        self.extractor = AIExtractor()

        # Modo hibrido (carrega sob demanda)
        self._hybrid_loaded = False
        self._use_hybrid_global = getattr(django_settings, 'USE_HYBRID_AI', False)
        self._hybrid_phones = getattr(django_settings, 'HYBRID_AI_PHONES', [])

        if self._use_hybrid_global or self._hybrid_phones:
            self._load_hybrid()

    def _load_hybrid(self):
        """Carrega componentes do modo hibrido."""
        try:
            from apps.core.hybrid.classifier import MessageClassifier
            from apps.core.hybrid.extractor import FocusedExtractor
            from apps.core.hybrid.smart_response import SmartResponseBuilder
            from apps.core.hybrid.conversational import ConversationalAI

            self.classifier = MessageClassifier()
            self.focused_extractor = FocusedExtractor()
            self.smart_response = SmartResponseBuilder()
            self.conversational_ai = ConversationalAI()
            self._hybrid_loaded = True
            logger.info("[hybrid] Componentes hibridos carregados com sucesso")
        except Exception as e:
            logger.exception("[hybrid] Erro ao carregar componentes hibridos, usando modo legado")
            self._hybrid_loaded = False

    def _should_use_hybrid(self, telefone: str) -> bool:
        """Decide se usa modo hibrido para este telefone."""
        if not self._hybrid_loaded:
            return False
        if self._use_hybrid_global:
            return True
        if telefone in self._hybrid_phones:
            return True
        return False

    # ==================== PROCESSAMENTO PRINCIPAL ====================

    def process(
        self,
        telefone: str,
        mensagem: str,
        usuario_empresa: UsuarioEmpresa = None
    ) -> str:
        """
        Processa mensagem através do fluxo linear.

        Args:
            telefone: Telefone do cliente
            mensagem: Texto da mensagem enviada
            usuario_empresa: Usuário já validado pelo Gateway (opcional para retrocompatibilidade)

        Returns:
            Resposta para o cliente
        """
        logger.info('Processando mensagem', extra={'telefone': telefone})

        try:
            # Se não veio do Gateway, buscar (retrocompatibilidade)
            if usuario_empresa is None:
                usuario_empresa = UsuarioEmpresa.objects.filter(
                    telefone=telefone,
                    is_active=True
                ).select_related('empresa__contabilidade').first()

                if not usuario_empresa:
                    logger.warning(f'Telefone {telefone} não cadastrado', extra={'telefone': telefone})
                    return ""

            contabilidade = usuario_empresa.empresa.contabilidade
            logger.info(
                f'Usuario: {usuario_empresa.nome} | '
                f'Empresa: {usuario_empresa.empresa.razao_social} | '
                f'Contabilidade: {contabilidade.razao_social}',
                extra={'telefone': telefone}
            )

            session = self.session_manager.get_or_create_session(telefone)

            # Propagar empresa_id na sessao para historico
            if not session.empresa_id:
                session.empresa_id = usuario_empresa.empresa_id

            # ADICIONAR MENSAGEM DO USUARIO
            session.add_user_message(mensagem)

            # VERIFICAR ESTADO E ROTEAR
            if session.estado == SessionState.AGUARDANDO_CONFIRMACAO.value:
                resposta = self._handle_confirmacao(session, mensagem)
            elif self._should_use_hybrid(telefone):
                resposta = self._processar_hybrid(session, mensagem, usuario_empresa)
            else:
                resposta = self._processar_coleta(session, mensagem)

            # ADICIONAR RESPOSTA DO BOT AO CONTEXTO
            session.add_bot_message(resposta)

            # SALVAR SESSÃO ATUALIZADA
            self.session_manager.save_session(session)
            logger.debug(f"{50 * '='}\n==========  INICIO DUMP SESSÃO  ========== \n\
                         \n{session.model_dump_json(indent=2)}\n{50 * '='}\n \
            ==========  FIM DUMP SESSÃO  ==========")

            return resposta

        except Exception as e:
            logger.exception('Erro ao processar', extra={'telefone': telefone})
            return 'Erro ao processar. Tente novamente.'

    # ==================== MODO HIBRIDO ====================

    def _processar_hybrid(self, session: Session, mensagem: str, usuario_empresa=None) -> str:
        """
        Processa mensagem usando arquitetura hibrida.

        Fluxo:
            1. Verificar sugestao pendente
            2. Classificar mensagem (sem IA)
            3. Rotear para handler adequado
            4. Gerar resposta
        """
        # Verificar se ha sugestao pendente e usuario aceitou
        if session.pending_suggestion and mensagem.strip().lower() in ('sim', 's'):
            return self._aplicar_sugestao(session)

        tipo = self.classifier.classify(mensagem)
        logger.info(f"[hybrid] Mensagem classificada como '{tipo}'", extra={'telefone': session.telefone})

        # Limpar sugestao pendente se usuario enviou outra coisa
        if session.pending_suggestion:
            session.pending_suggestion = None

        if tipo == 'saudacao':
            return self.smart_response.build_saudacao(session)

        elif tipo == 'agradecimento':
            return self.smart_response.build_agradecimento()

        elif tipo == 'cancelamento':
            # Cancelamento durante coleta
            session.update_estado(SessionState.CANCELADO_USUARIO.value)
            session.add_system_message(f"{datetime.now().strftime('%d/%m/%y %H:%M')} Cancelado pelo usuario.")
            self.session_manager.save_session(session, reason='cancelled')
            return self.smart_response.build_cancelado()

        elif tipo == 'repetir_nota':
            return self._handle_repetir_nota(session, usuario_empresa)

        elif tipo == 'pergunta':
            # IA conversacional para perguntas (com historico)
            session.increment_ai_calls()
            return self.conversational_ai.respond(
                mensagem, session, empresa_id=session.empresa_id
            )

        else:
            # tipo == 'dados' -> extracao focada
            return self._processar_coleta_hybrid(session, mensagem)

    def _processar_coleta_hybrid(self, session: Session, mensagem: str) -> str:
        """
        Coleta de dados usando extrator focado + SmartResponseBuilder.
        """
        logger.info("[hybrid] Extracao focada", extra={'telefone': session.telefone})

        # Preparar historico para contexto
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in session.get_conversation_history(limit=6)
        ]

        # EXTRAIR com FocusedExtractor
        dados_extraidos = self.focused_extractor.parse(
            mensagem,
            session.invoice_data if session.invoice_data else None,
            conversation_history=history,
        )

        session.increment_ai_calls()

        # MESCLAR com dados anteriores
        if session.invoice_data:
            dados_finais = session.invoice_data.merge(dados_extraidos)
            logger.info("[hybrid] Dados mesclados", extra={'telefone': session.telefone})
        else:
            dados_finais = dados_extraidos
            logger.info("[hybrid] Primeira extracao", extra={'telefone': session.telefone})

        # Atualizar invoice_data na sessao
        session.update_invoice_data(dados_finais)

        logger.debug(f"[hybrid] Dados processados:\n{dados_finais.model_dump_json(indent=2)}")

        # SUGESTAO DE DESCRICAO: se CNPJ validado e descricao faltando, sugerir do historico
        if (
            session.empresa_id
            and dados_finais.cnpj.status == 'validated'
            and dados_finais.descricao.status == 'null'
        ):
            try:
                from apps.core.history.invoice_history import InvoiceHistoryService
                sugestao = InvoiceHistoryService.get_descricao_sugerida(
                    session.empresa_id, dados_finais.cnpj.cnpj
                )
                if sugestao:
                    logger  .info(f"[hybrid] Sugestao de descricao encontrada: {sugestao[:50]}")
                    session.pending_suggestion = {
                        'tipo': 'descricao',
                        'valor': sugestao,
                    }
                    session.update_estado(SessionState.DADOS_INCOMPLETOS.value)
                    return self.smart_response.build_sugestao_descricao(dados_finais, sugestao)
            except Exception as e:
                logger.warning(f"[hybrid] Erro ao buscar sugestao: {e}")

        # GERAR RESPOSTA com SmartResponseBuilder
        if dados_finais.data_complete:
            logger.info("[hybrid] Dados completos - espelho", extra={'telefone': session.telefone})
            session.update_estado(SessionState.AGUARDANDO_CONFIRMACAO.value)
            return self.smart_response.build_espelho(dados_finais.to_dict())
        else:
            session.update_estado(SessionState.DADOS_INCOMPLETOS.value)
            logger.info("[hybrid] Dados incompletos", extra={'telefone': session.telefone})
            return self.smart_response.build_smart_response(dados_finais)

    # ==================== HANDLERS DE HISTORICO ====================

    def _handle_repetir_nota(self, session: Session, usuario_empresa) -> str:
        """Repete a ultima nota emitida pela empresa."""
        empresa_id = session.empresa_id
        if not empresa_id:
            return "Nao consegui identificar sua empresa. Tente novamente."

        try:
            from apps.core.history.invoice_history import InvoiceHistoryService

            emissao = InvoiceHistoryService.get_ultima_nota(empresa_id)
            if not emissao:
                logger.info("[hybrid] Nenhuma nota anterior encontrada", extra={'telefone': session.telefone})
                return "Nao encontrei notas anteriores para sua empresa. Me passe os dados: CNPJ, valor e descricao."

            # Converter emissao em DadosNFSe
            dados = InvoiceHistoryService.dados_nfse_from_emissao(emissao)
            session.update_invoice_data(dados)
            session.update_estado(SessionState.AGUARDANDO_CONFIRMACAO.value)

            razao_social = emissao.tomador.razao_social if emissao.tomador else "N/A"
            logger.info(
                f"[hybrid] Repetindo nota: {emissao.id_integracao} para {razao_social}",
                extra={'telefone': session.telefone}
            )

            return self.smart_response.build_repetir_nota(
                dados.to_dict(),
                emissao.created_at,
                razao_social,
            )
        except Exception as e:
            logger.exception("[hybrid] Erro ao repetir nota")
            return "Erro ao buscar nota anterior. Tente novamente."

    def _aplicar_sugestao(self, session: Session) -> str:
        """Aplica sugestao pendente (ex: descricao do historico)."""
        sugestao = session.pending_suggestion
        session.pending_suggestion = None

        if not sugestao or sugestao.get('tipo') != 'descricao':
            return self.smart_response.build_smart_response(session.invoice_data)

        from apps.core.models import DescricaoExtraida, DadosNFSe

        descricao_valor = sugestao['valor']
        logger.info(f"[hybrid] Aplicando sugestao de descricao: {descricao_valor[:50]}")

        # Criar descricao validada
        nova_descricao = DescricaoExtraida(
            descricao_extracted=descricao_valor,
            descricao=descricao_valor,
            status='validated',
        )

        # Reconstruir DadosNFSe com a descricao
        dados_finais = DadosNFSe(
            cnpj=session.invoice_data.cnpj,
            valor=session.invoice_data.valor,
            descricao=nova_descricao,
        )

        session.update_invoice_data(dados_finais)

        if dados_finais.data_complete:
            session.update_estado(SessionState.AGUARDANDO_CONFIRMACAO.value)
            return self.smart_response.build_espelho(dados_finais.to_dict())
        else:
            session.update_estado(SessionState.DADOS_INCOMPLETOS.value)
            return self.smart_response.build_smart_response(dados_finais)

    # ==================== MODO LEGADO (ORIGINAL) ====================

    def _processar_coleta(self, session: Session, mensagem: str ) -> str:
        """
        Processa coleta de dados (modo legado).

        Fluxo:
            1. Checks (futuro: validações, regras de negócio)
            2. Extração com AIExtractor
            3. Merge com dados anteriores
            4. Verificar se dados_complete
            5. Se completo → handle_dados_completos
            6. Se incompleto → handle_dados_incompletos
        """
        logger.info("Iniciando coleta de dados", extra={'telefone': session.telefone})


        # EXTRAIR com AIExtractor
        logger.info("Extraindo dados com IA", extra={'telefone': session.telefone})

        dados_extraidos = self.extractor.parse(
            mensagem,
            session.invoice_data if session.invoice_data else None
        )

        # Incrementar contador de chamadas de IA
        session.increment_ai_calls()

        # MESCLAR com dados anteriores
        if session.invoice_data:
            dados_finais = session.invoice_data.merge(dados_extraidos)
            logger.info("Dados mesclados", extra={'telefone': session.telefone})
        else:
            dados_finais = dados_extraidos
            logger.info("Primeira extração", extra={'telefone': session.telefone})

        # Atualizar invoice_data na sessão
        session.update_invoice_data(dados_finais)


        # LOG para debug
        logger.debug(f"Dados processados:\n{dados_finais.model_dump_json(indent=2)}")

        #  VERIFICAR SE DADOS COMPLETOS
        if dados_finais.data_complete:
            logger.info("Dados completos - exibindo espelho", extra={'telefone': session.telefone})
            session.update_estado(SessionState.AGUARDANDO_CONFIRMACAO.value)

            # Sessão será salva automaticamente pelo save_session no final do processo
            return self.response_builder.build_espelho(dados_finais.to_dict())
        else:
            session.update_estado(SessionState.DADOS_INCOMPLETOS.value)
            logger.info("Dados incompletos - solicitando campos", extra={'telefone': session.telefone})
            return self.response_builder.build_dados_incompletos(dados_finais.user_message)


    # ==================== HANDLERS ====================


    def _handle_confirmacao(self, session: Session, mensagem: str) -> str:
        """Handler para confirmação (SIM/NÃO)."""
        logger.info("Processando confirmação", extra={'telefone': session.telefone})
        msg_normalizada = mensagem.strip().lower()

        # CONFIRMOU
        if msg_normalizada in ['sim', 's', 'ok', 'confirmar', 'confirmo']:
            logger.info("Confirmado - processando emissão", extra={'telefone': session.telefone})
            session.update_estado(SessionState.PROCESSANDO.value)
            session.add_system_message(f"{datetime.now().strftime('%d/%m/%y %H:%M')} usuario nota confirmada.")

            # Salvar sessão com estado final (confirmed)
            self.session_manager.save_session(session, reason='confirmed')

            # ✅ NOVO: Disparar emissão de NFSe
            try:
                from apps.nfse.services.emissao import NFSeEmissaoService
                logger.info("Iniciando emissão de NFSe", extra={'sessao_id': session.sessao_id})
                nfse = NFSeEmissaoService.emitir_de_sessao(session.sessao_id)
                logger.info(f"NFSe emitida com sucesso: {nfse.numero}", extra={'sessao_id': session.sessao_id})
                return self.response_builder.build_nfse_emitida(nfse)
            except Exception as e:
                logger.exception("Erro ao emitir NFSe", extra={'sessao_id': session.sessao_id})
                return "❌ Erro ao processar emissão da nota fiscal. Nossa equipe foi notificada e entrará em contato."

        # CANCELOU
        elif msg_normalizada in ['não', 'nao', 'n', 'cancelar', 'cancela']:
            logger.info("Cancelado pelo usuário", extra={'telefone': session.telefone})
            session.update_estado(SessionState.CANCELADO_USUARIO.value)
            session.add_system_message(f"{datetime.now().strftime('%d/%m/%y %H:%M')} Solicitação cancelada pelo usuário.")

            # Salvar sessão com estado final (cancelled)
            self.session_manager.save_session(session, reason='cancelled')

            return self.response_builder.build_cancelado()

        # NÃO ENTENDEU
        else:
            logger.warning("Resposta inválida na confirmação", extra={'telefone': session.telefone})
            espelho = self.response_builder.build_espelho(session.invoice_data.to_dict())
            return f"⚠️ Não entendi sua resposta.\n\n{espelho}\n\n💡 Digite *SIM* para confirmar ou *NÃO* para cancelar."


