"""
Gateway Mock para simular emissão de NFSe (testes).
"""
import uuid
from datetime import date
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class MockNFSeGateway:
    """Gateway fake para testes de emissão de NFSe."""
    
    @staticmethod
    def emitir_nfse(payload: Dict) -> Dict:
        """
        Simula emissão de NFSe.
        
        Args:
            payload: JSON de emissão
            
        Returns:
            Resposta fake simulando TecnoSpeed
        """
        id_integracao = payload.get('idIntegracao')
        valor = payload['servico'][0]['valor']['servico']
        prestador = payload['prestador']['cpfCnpj']
        tomador = payload['tomador']['cpfCnpj']
        
        logger.info(f"[MOCK] Emitindo NFSe para {id_integracao}")
        
        # Gera dados fake
        numero = f"{uuid.uuid4().int % 999999:06d}"
        chave = f"41{date.today().strftime('%y%m')}{prestador}55805000{numero}0000000001"
        protocolo = f"{uuid.uuid4().int % 999999999999999:015d}"
        
        resposta = {
            "id": str(uuid.uuid4()),
            "emissao": date.today().strftime('%d/%m/%Y'),
            "status": "CONCLUIDO",
            "destinada": False,
            "emitente": prestador,
            "destinatario": tomador,
            "valor": float(valor),
            "dataAutorizacao": date.today().strftime('%d/%m/%Y'),
            "numero": numero,
            "serie": "001",
            "chave": chave,
            "protocolo": protocolo,
            "mensagem": "Autorizado o uso da NFSe (SIMULAÇÃO - MOCK)",
            "xml": f"https://mock.api.tecnospeed.com.br/nfse/{id_integracao}/xml",
            "pdf": f"https://mock.api.tecnospeed.com.br/nfse/{id_integracao}/pdf",
            "cStat": 100,
            "documento": "nfse"
        }
        
        logger.info(f"[MOCK] NFSe {numero} emitida com sucesso")
        return resposta
