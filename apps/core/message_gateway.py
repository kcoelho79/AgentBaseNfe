"""
MessageGateway - Pré-processador simples de mensagens.

Responsabilidades:
1. Validar telefone (UsuarioEmpresa ativo)
2. Validar tenant (instance_name pertence à contabilidade do usuário)
3. Rotear para MessageProcessor ou rejeitar
"""

import logging
from dataclasses import dataclass
from typing import Optional

from apps.contabilidade.models import UsuarioEmpresa
from apps.whatsapp_api.models import CanalWhatsApp

logger = logging.getLogger(__name__)


@dataclass
class GatewayResult:
    """Resultado do gateway."""
    success: bool
    response: str = ""
    usuario_empresa: Optional[UsuarioEmpresa] = None
    reject_reason: str = ""


class MessageGateway:
    """
    Pré-processador de mensagens.
    Valida telefone e tenant antes de processar.
    """
    
    MSG_NAO_CADASTRADO = (
        "❌ Seu telefone não está cadastrado em nosso sistema.\n\n"
        "Entre em contato com sua contabilidade para cadastrar seu número."
    )
    
    MSG_CANAL_INVALIDO = (
        "⚠️ Este canal não está configurado para sua empresa."
    )
    
    def __init__(self, send_rejection_message: bool = False):
        """
        Args:
            send_rejection_message: Se True, retorna mensagem de erro.
                                   Se False, retorna string vazia.
        """
        self.send_rejection_message = send_rejection_message
    
    def process(
        self,
        telefone: str,
        mensagem: str,
        instance_name: str = None
    ) -> GatewayResult:
        """
        Valida e processa mensagem.
        
        Args:
            telefone: Número do telefone
            mensagem: Texto da mensagem
            instance_name: Nome da instância (None para chat local)
        """
        # 1. Validar telefone
        usuario = UsuarioEmpresa.objects.filter(
            telefone=telefone,
            is_active=True
        ).select_related('empresa__contabilidade').first()
        
        if not usuario:
            logger.warning(f"Telefone não cadastrado: {telefone}")
            return GatewayResult(
                success=False,
                response=self.MSG_NAO_CADASTRADO if self.send_rejection_message else "",
                reject_reason="telefone_nao_cadastrado"
            )
        
        # 2. Validar tenant (se veio do webhook)
        if instance_name:
            canal_valido = CanalWhatsApp.objects.filter(
                instance_name=instance_name,
                contabilidade=usuario.empresa.contabilidade,
                is_active=True
            ).exists()
            
            if not canal_valido:
                logger.warning(f"Canal inválido para usuário: {instance_name}")
                return GatewayResult(
                    success=False,
                    response=self.MSG_CANAL_INVALIDO if self.send_rejection_message else "",
                    reject_reason="canal_invalido"
                )
        
        # 3. Processar mensagem
        from apps.core.message_processor import MessageProcessor
        
        processor = MessageProcessor()
        response = processor.process(
            telefone=telefone,
            mensagem=mensagem,
            usuario_empresa=usuario
        )
        
        return GatewayResult(
            success=True,
            response=response,
            usuario_empresa=usuario
        )
