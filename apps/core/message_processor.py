import logging
import random
from datetime import datetime
from typing import Dict, Optional
from apps.core.models import DadosNFSe
from apps.core.reponse_builder import ResponseBuilder
from apps.core.agent_extractor import AIExtractor
from apps.core.state_manager import StateManager

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Orquestrador de mensagens para emissão de NFSe.
    
    Fluxo simplificado:
        1. Verifica se tem state
        2. Se estado = 'aguardando_confirmacao' → handle_confirmacao
        3. Senão → coleta de dados
        4. Dentro da coleta: checks → extração → merge → verificação completude
        5. Se completo → handle_dados_completos
        6. Se incompleto → handle_dados_incompletos
    """
    
    def __init__(self):
        self.state_manager = StateManager()
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
            # 1. VERIFICAR SE TEM STATE
            state = self.state_manager.get_state(telefone)
            
            # 2. SE TEM STATE E ESTÁ AGUARDANDO CONFIRMAÇÃO
            if state and state.get('estado') == 'aguardando_confirmacao':
                return self._handle_confirmacao(telefone, mensagem, state)
            
            # 3. SENÃO, CHAMAR COLETA
            return self._processar_coleta(telefone, mensagem, state)
            
        except Exception as e:
            logger.exception('Erro ao processar', extra={'telefone': telefone})
            return 'Erro ao processar. Tente novamente.'
    
    # ==================== COLETA DE DADOS ====================
    
    def _processar_coleta(self, telefone: str, mensagem: str, state: Optional[dict]) -> str:
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
        logger.info("Iniciando coleta de dados", extra={'telefone': telefone})
        
        # 1. DETERMINAR PROTOCOLO
        if not state:
            protocolo_id = self._gerar_protocolo()
            logger.info(f"Protocolo criado: {protocolo_id}", extra={'telefone': telefone})
        else:
            protocolo_id = state['protocolo_id']
        
        # 2. CHECKS (futuro: implementar validações)
        # TODO: self._verificar_cliente(telefone)
        # TODO: self._verificar_intencao(mensagem)
        # TODO: self._verificar_limites_diarios(telefone)
        
        # 3. RECUPERAR DADOS ANTERIORES
        dados_anterior = self.state_manager.get_dados(telefone)
        
        # 4. EXTRAIR com AIExtractor
        logger.info("Extraindo dados com IA", extra={'telefone': telefone})
        dados_extraidos = self.extractor.parse(
            mensagem,
            dados_anterior if dados_anterior else None
        )
        
        # 5. MESCLAR com dados anteriores
        if dados_anterior:
            dados_finais = dados_anterior.merge(dados_extraidos)
            logger.info("Dados mesclados", extra={'telefone': telefone})
        else:
            dados_finais = dados_extraidos
            logger.info("Primeira extração", extra={'telefone': telefone})
        
        # 6. LOG para debug
        logger.debug(f"Dados processados:\n{dados_finais.model_dump_json(indent=2)}")
        
        # 7. VERIFICAR SE DADOS COMPLETOS
        if dados_finais.data_complete:
            return self._handle_dados_completos(telefone, dados_finais, protocolo_id)
        else:
            return self._handle_dados_incompletos(telefone, dados_finais, protocolo_id)
    
    # ==================== HANDLERS ====================
    
    def _handle_dados_completos(self, telefone: str, dados: DadosNFSe, protocolo_id: str) -> str:
        """
        Handler para dados completos.
        
        Ações:
            - Salva estado 'aguardando_confirmacao'
            - Retorna espelho da nota
        """
        logger.info("Dados completos - exibindo espelho", extra={'telefone': telefone})
        
        # Salvar estado
        self.state_manager.update_state(
            telefone=telefone,
            novo_estado='aguardando_confirmacao',
            dados=dados,
            protocolo_id=protocolo_id
        )
        
        # Retornar espelho
        return self.response_builder.build_espelho(dados.to_dict())
    
    def _handle_dados_incompletos(self, telefone: str, dados: DadosNFSe, protocolo_id: str) -> str:
        """
        Handler para dados incompletos.
        
        Ações:
            - Salva estado 'dados_incompletos'
            - Retorna mensagem solicitando dados faltantes
        """
        logger.info("Dados incompletos - solicitando campos", extra={'telefone': telefone})
        
        # Salvar estado
        self.state_manager.update_state(
            telefone=telefone,
            novo_estado='dados_incompletos',
            dados=dados,
            protocolo_id=protocolo_id
        )
        
        # Retornar mensagem com campos faltantes
        return self.response_builder.build_dados_incompletos(dados.user_message)
    
    def _handle_confirmacao(self, telefone: str, mensagem: str, state: dict) -> str:
        """
        Handler para confirmação (SIM/NÃO).
        
        Ações:
            - SIM: transiciona para 'processando' e envia para gateway
            - NÃO: cancela e limpa estado
            - Outra: reexibe espelho
        """
        logger.info("Processando confirmação", extra={'telefone': telefone})
        
        msg_normalizada = mensagem.strip().lower()
        
        # CONFIRMOU
        if msg_normalizada in ['sim', 's', 'ok', 'confirmar', 'confirmo']:
            logger.info("Confirmado - processando emissão", extra={'telefone': telefone})
            
            dados = self.state_manager.get_dados(telefone)
            
            # Atualizar para processando
            self.state_manager.update_state(
                telefone=telefone,
                novo_estado='processando',
                dados=dados,
                protocolo_id=state['protocolo_id']
            )
            
            # Enviar para gateway
            # TODO: self._enviar_para_gateway(dados, state['protocolo_id'])
            self.state_manager.clear_state(telefone)

            
            return self.response_builder.build_confirmacao_processando(state['protocolo_id'])
        
        # CANCELOU
        elif msg_normalizada in ['não', 'nao', 'n', 'cancelar', 'cancela']:
            logger.info("Cancelado pelo usuário", extra={'telefone': telefone})
            self.state_manager.clear_state(telefone)
            
            return self.response_builder.build_cancelado()
        
        # NÃO ENTENDEU
        else:
            logger.warning("Resposta inválida na confirmação", extra={'telefone': telefone})
            dados = self.state_manager.get_dados(telefone)
            
            if dados:
                espelho = self.response_builder.build_espelho(dados.to_dict())
                return f"⚠️ Não entendi sua resposta.\n\n{espelho}\n\n💡 Digite *SIM* para confirmar ou *NÃO* para cancelar."
            
            return "⚠️ Digite *SIM* para confirmar ou *NÃO* para cancelar."
    
    # ==================== UTILIDADES ====================
    
    def _gerar_protocolo(self) -> str:
        """Gera ID único de protocolo (AAMMDDHHMM-XXXXX)."""
        timestamp = datetime.now().strftime('%y%m%d%H%M')
        aleatorio = random.randint(10000, 99999)
        return f"{timestamp}-{aleatorio}"
    
    # ==================== CHECKS (FUTURO) ====================
    
    def _verificar_cliente(self, telefone: str) -> Optional[dict]:
        """[FUTURO] Verifica se cliente existe e está ativo."""
        # TODO: Implementar consulta ao banco
        logger.debug("Verificação de cliente não implementada", extra={'telefone': telefone})
        return None
    
    def _verificar_intencao(self, mensagem: str) -> str:
        """[FUTURO] Detecta intenção da mensagem."""
        # TODO: Implementar detecção de intenção
        logger.debug("Verificação de intenção não implementada")
        return 'emitir_nota'
    
    def _verificar_limites_diarios(self, telefone: str) -> bool:
        """[FUTURO] Verifica se cliente não excedeu limite diário."""
        # TODO: Implementar consulta de limites
        logger.debug("Verificação de limites não implementada", extra={'telefone': telefone})
        return True
    
    def _enviar_para_gateway(self, dados: DadosNFSe, protocolo_id: str) -> dict:
        """[FUTURO] Envia dados para gateway de emissão."""
        # TODO: Implementar integração com gateway
        logger.info(f"Enviando para gateway - Protocolo: {protocolo_id}")
        return {'status': 'pending'}