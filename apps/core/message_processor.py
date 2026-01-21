import logging
import random
from datetime import datetime
from typing import Dict, Optional
from apps.core.models import DadosNFSe, Session
from apps.core.reponse_builder import ResponseBuilder
from apps.core.agent_extractor import AIExtractor
from apps.core.session_manager import SessionManager

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Orquestrador de mensagens para emissão de NFSe
    """
    
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.extractor = AIExtractor()
        self.response_builder = ResponseBuilder()
    
    # ==================== PROCESSAMENTO PRINCIPAL ====================
    
    def process(self, telefone: str, mensagem: str) -> str:
        """
        Processa mensagem através do fluxo linear.
        
        Args:
            telefone: Telefone do cliente
            mensagem: Texto da mensagem enviada
            
        Returns:
            Resposta para o cliente
        """
        logger.info('Processando mensagem', extra={'telefone': telefone})
        
        try:
            # 1. RECUPERAR OU CRIAR A SESSAO
            session = self.session_manager.get_or_create_session(telefone)

            # 2. ADICIONAR MENSAGEM DO USUARIO
            session.add_user_message(mensagem)
            
            # 2. VERIFICAR ESTADO E ROTEAR
            if session.estado == 'aguardando_confirmacao':
                resposta = self._handle_confirmacao(session, mensagem)
            else:
                resposta = self._processar_coleta(session, mensagem)
            
            # 4. ADICIONAR RESPOSTA DO BOT AO CONTEXTO
            session.add_bot_message(resposta)

            # 5. SALVAR SESSÃO ATUALIZADA
            self.session_manager.save_session(session)
            logger.debug(f"SESSÃO SALVA:\n\n{session.model_dump_json(indent=2)}\n\n")

            return resposta

        except Exception as e:
            logger.exception('Erro ao processar', extra={'telefone': telefone})
            return 'Erro ao processar. Tente novamente.'
    
    # ==================== COLETA DE DADOS ====================
    
    def _processar_coleta(self, session: Session, mensagem: str ) -> str:
        """
        Processa coleta de dados.
        
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
            session.update_estado('aguardando_confirmacao')
            # Sessão será salva automaticamente pelo save_session no final do processo
            return self.response_builder.build_espelho(dados_finais.to_dict())
        else:
            session.update_estado('dados_incompletos')
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
            session.update_estado('processando')
            session.add_system_message(f"{datetime.now()} usuario nota confirmada.")

            # Salvar sessão com estado final (confirmed)
            self.session_manager.save_session(session, reason='confirmed')

            return self.response_builder.build_confirmacao_processando(session.sessao_id)

        # CANCELOU
        elif msg_normalizada in ['não', 'nao', 'n', 'cancelar', 'cancela']:
            logger.info("Cancelado pelo usuário", extra={'telefone': session.telefone})
            session.update_estado('cancelado_usuario')
            session.add_system_message(f"{datetime.now()} Solicitação cancelada pelo usuário.")

            # Salvar sessão com estado final (cancelled)
            self.session_manager.save_session(session, reason='cancelled')

            return self.response_builder.build_cancelado()
        
        # NÃO ENTENDEU
        else:
            logger.warning("Resposta inválida na confirmação", extra={'telefone': session.telefone})         
            espelho = self.response_builder.build_espelho(session.invoice_data.to_dict())
            return f"⚠️ Não entendi sua resposta.\n\n{espelho}\n\n💡 Digite *SIM* para confirmar ou *NÃO* para cancelar."
            
    
    