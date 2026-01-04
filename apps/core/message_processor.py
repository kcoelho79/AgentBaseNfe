import json
import logging
import random
from datetime import datetime
from typing import Dict
from apps.core.models import DadosNFSe
from apps.core.reponse_builder import ResponseBuilder
from apps.core.agent_extractor import AIExtractor
from apps.core.state_manager import StateManager

logger = logging.getLogger(__name__)

class MessageProcessor:
    """
    Orquesta processamento de mensagens

    step:
        -   Identifica Cliente
        -   Gerencia estado da conversa
        -   Extrai dados com IA
        -   Constroi respostas

    """
    def __init__(self):
        self.state_manager = StateManager()
        self.agent_extractor = AIExtractor()
        self.reponse_builder= ResponseBuilder()
        

    def process(self, telefone: str, mensagem:str) -> str:
        """
        Processa mensagem e retorna resposta para o cliente
        
        Args:
            telefone: Telefone do cliente
            mensagem: Texto da mensagem enviada

        Returns:
            Texto da resposta a ser enviado para o cliente
        """

        logger.info('Iniciando processamento', extra={'telefone':telefone})

        try:
            #1 TODO busca cliente (não implementado)
            #2 TODO verificar intenção (não implementado)

            #3 buscar estado (coletando, dados_incompleto, aguardando_confirmação)
            protocolo = self.state_manager.get_state(telefone)      

            if protocolo:
                estado = protocolo.get('estado')
                
                if estado == "aguardando_confirmação":
                    mensagem = f"aguardando  configrmassao para  emissão da NFSe."
                    mensagem += json.dumps(protocolo.get('dados'), indent=2, ensure_ascii=False)
                    return mensagem
                    self._handle_confirmacao(telefone, mensagem, protocolo)
                else:
                    #estado em processamento
                    pass
            else:
                protocolo = {}
                protocolo['protocolo_id'] = self._gerar_num_protocolo()
                logger.info(f"telefone: {telefone} - Protocolo Criado num: {protocolo['protocolo_id']} ")    
            return self._handle_nova_mensagem(telefone, mensagem, protocolo)
                     

        except Exception as e:
            logger.exception('Erro no processamento', extra={'telefone': telefone})
            return 'Erro ao processar mensagem. Tente novamente em alguns instantes.'
    
    
    def _handle_nova_mensagem(self, telefone:str, mensagem:str, protocolo ) -> str:   
        # Recuperar dados anteriores como objeto DadosNFSe
        dados_anterior = self.state_manager.get_dados(telefone)

        # Extrair novos dados (já retorna DadosNFSe validado pela OpenAI)
        dados_extraidos = self.agent_extractor.parse(
            mensagem, 
            dados_anterior.to_dict() if dados_anterior else None
        )

        if dados_anterior:
            dados_mesclados = dados_anterior.merge(dados_extraidos)
            logger.info("Dados mesclados com anteriores")

        else:
            dados_mesclados = dados_extraidos
            logger.info("primeira mensagem, sem dados anteriores")

         # Log dos dados mesclados
        logger.info(f"Dados finais:\n{dados_mesclados.model_dump_json(indent=2)}")

        if not dados_mesclados.data_complete:
            
            # DADOS INCOMPLETOS
            self.state_manager.update_state(
                telefone=telefone,
                novo_estado='dados_incompletos',
                dados=dados_mesclados,
                protocolo_id=protocolo['protocolo_id']
            )
            # Construir mensagem solicitando dados faltantes
            return dados_extraidos.user_message
        
        else:
            # DADOS COMPLETOS - Montar espelho de nota
            logger.info(f"Dados completos para telefone {telefone}")
            
            self.state_manager.update_state(
                telefone=telefone,
                novo_estado='aguardando_confirmacao',
                dados=dados_mesclados,
                protocolo_id=protocolo['protocolo_id']
            )
            
            return self.reponse_builder.build_espelho(dados_mesclados.to_dict())

     
    def _gerar_num_protocolo(self) -> str:
        """Gera ID  protocolo data formatada + sequencial"""
    
        data = datetime.now().strftime('%y%m%d%H%M')  
        aleatorio = random.randint(10000, 99999)  
        return f"{data}-{aleatorio}"
        
    
    