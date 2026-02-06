"""
Serviço de integração com Evolution API.
Gerencia instâncias WhatsApp, webhooks e envio de mensagens.
"""

import logging
import requests
from typing import Optional, Dict, Any
from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)


class EvolutionAPIError(Exception):
    """Exceção para erros da Evolution API."""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class EvolutionService:
    """
    Cliente para Evolution API.
    
    Documentação: https://doc.evolution-api.com/
    
    Uso:
        service = EvolutionService()
        result = service.create_instance('minha-instancia')
    """
    
    def __init__(self):
        self.base_url = config('EVOLUTION_API_URL', default='http://10.238.0.103:8080')
        self.api_key = config('EVOLUTION_API_KEY', default='mude-me')
        self.webhook_base_url = config('WEBHOOK_BASE_URL', default='https://agentbase.komputer.com.br')
        
        # Remove trailing slash
        self.base_url = self.base_url.rstrip('/')
        
    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers padrão para requisições."""
        return {
            'Content-Type': 'application/json',
            'apikey': self.api_key
        }
    
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: dict = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Executa requisição para Evolution API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: Endpoint da API (ex: /instance/create)
            data: Dados para enviar (POST/PUT)
            timeout: Timeout em segundos
            
        Returns:
            Dict com resposta da API
            
        Raises:
            EvolutionAPIError: Se houver erro na requisição
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Evolution API Request: {method} {url}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=data,
                timeout=timeout
            )
            
            # Log response
            logger.debug(f"Evolution API Response: {response.status_code}")
            
            # Parse response
            try:
                result = response.json()
            except ValueError:
                result = {'raw': response.text}
            
            # Check for errors
            if response.status_code >= 400:
                error_msg = result.get('message', result.get('error', str(result)))
                logger.error(f"Evolution API Error: {error_msg}")
                raise EvolutionAPIError(
                    message=error_msg,
                    status_code=response.status_code,
                    response=result
                )
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"Evolution API Timeout: {url}")
            raise EvolutionAPIError("Timeout ao conectar com Evolution API")
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Evolution API Connection Error: {e}")
            raise EvolutionAPIError("Erro de conexão com Evolution API")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Evolution API Request Error: {e}")
            raise EvolutionAPIError(f"Erro na requisição: {str(e)}")
    
    # ==================== INSTÂNCIAS ====================
    
    def create_instance(
        self, 
        instance_name: str,
        webhook_url: str = None,
        qrcode: bool = True
    ) -> Dict[str, Any]:
        """
        Cria nova instância WhatsApp.
        
        Args:
            instance_name: Nome único da instância
            webhook_url: URL para receber webhooks (opcional)
            qrcode: Se deve gerar QR Code automaticamente
            
        Returns:
            Dict com dados da instância criada
        """
        data = {
            "instanceName": instance_name,
            "qrcode": qrcode,
            "integration": "WHATSAPP-BAILEYS"
        }
        
        # Configurar webhook se fornecido
        if webhook_url:
            data["webhook"] = {
                "url": webhook_url,
                "byEvents": False,
                "base64": False,
                "headers": {},
                "events": [
                    "MESSAGES_UPSERT",
                    "CONNECTION_UPDATE",
                    "QRCODE_UPDATED"
                ]
            }
        
        result = self._request('POST', '/instance/create', data)
        logger.info(f"Instância criada: {instance_name}")
        logger.debug(f"Create instance response keys: {result.keys() if isinstance(result, dict) else type(result)}")
        logger.debug(f"Create instance response: {str(result)[:500]}")
        return result
    
    def get_instance(self, instance_name: str) -> Dict[str, Any]:
        """
        Obtém informações de uma instância.
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            Dict com dados da instância
        """
        return self._request('GET', f'/instance/fetchInstances?instanceName={instance_name}')
    
    def delete_instance(self, instance_name: str) -> Dict[str, Any]:
        """
        Remove uma instância.
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            Dict com resultado da operação
        """
        result = self._request('DELETE', f'/instance/delete/{instance_name}')
        logger.info(f"Instância removida: {instance_name}")
        return result
    
    def restart_instance(self, instance_name: str) -> Dict[str, Any]:
        """
        Reinicia uma instância.
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            Dict com resultado da operação
        """
        result = self._request('PUT', f'/instance/restart/{instance_name}')
        logger.info(f"Instância reiniciada: {instance_name}")
        return result
    
    def logout_instance(self, instance_name: str) -> Dict[str, Any]:
        """
        Desconecta (logout) uma instância.
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            Dict com resultado da operação
        """
        result = self._request('DELETE', f'/instance/logout/{instance_name}')
        logger.info(f"Instância desconectada: {instance_name}")
        return result
    
    # ==================== CONEXÃO ====================
    
    def connect_instance(self, instance_name: str) -> Dict[str, Any]:
        """
        Inicia conexão e retorna QR Code.
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            Dict com QR Code em base64
        """
        result = self._request('GET', f'/instance/connect/{instance_name}')
        logger.info(f"QR Code gerado para: {instance_name}")
        return result
    
    def get_connection_state(self, instance_name: str) -> Dict[str, Any]:
        """
        Verifica estado da conexão.
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            Dict com estado (open, close, connecting)
        """
        return self._request('GET', f'/instance/connectionState/{instance_name}')
    
    # ==================== WEBHOOK ====================
    
    def set_webhook(
        self, 
        instance_name: str, 
        webhook_url: str,
        events: list = None
    ) -> Dict[str, Any]:
        """
        Configura webhook para uma instância.
        
        Args:
            instance_name: Nome da instância
            webhook_url: URL para receber eventos
            events: Lista de eventos (opcional)
            
        Returns:
            Dict com resultado da configuração
        """
        if events is None:
            events = [
                "MESSAGES_UPSERT",
                "CONNECTION_UPDATE",
                "QRCODE_UPDATED"
            ]
        
        data = {
            "url": webhook_url,
            "webhook_by_events": False,
            "webhook_base64": False,
            "events": events
        }
        
        result = self._request('PUT', f'/webhook/set/{instance_name}', data)
        logger.info(f"Webhook configurado para {instance_name}: {webhook_url}")
        return result
    
    def get_webhook(self, instance_name: str) -> Dict[str, Any]:
        """
        Obtém configuração de webhook.
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            Dict com configuração do webhook
        """
        return self._request('GET', f'/webhook/find/{instance_name}')
    
    # ==================== MENSAGENS ====================
    
    def send_text_message(
        self, 
        instance_name: str, 
        phone_number: str, 
        message: str
    ) -> Dict[str, Any]:
        """
        Envia mensagem de texto.
        
        Args:
            instance_name: Nome da instância
            phone_number: Número do destinatário (com código do país)
            message: Texto da mensagem
            
        Returns:
            Dict com resultado do envio
        """
        # Normalizar número (remover caracteres especiais)
        phone = ''.join(filter(str.isdigit, phone_number))
        
        # Adicionar @s.whatsapp.net se necessário
        if not phone.endswith('@s.whatsapp.net'):
            phone = f"{phone}@s.whatsapp.net"
        
        data = {
            "number": phone,
            "text": message
        }
        
        result = self._request('POST', f'/message/sendText/{instance_name}', data)
        logger.info(f"Mensagem enviada para {phone_number} via {instance_name}")
        return result
    
    # ==================== HELPERS ====================
    
    def get_webhook_url_for_instance(self, instance_name: str) -> str:
        """
        Gera URL de webhook para uma instância.
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            URL completa do webhook
        """
        return f"{self.webhook_base_url}/whatsapp/webhook/{instance_name}/"
    
    def create_instance_with_webhook(self, instance_name: str) -> Dict[str, Any]:
        """
        Cria instância já configurada com webhook.
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            Dict com dados da instância e webhook
        """
        webhook_url = self.get_webhook_url_for_instance(instance_name)
        
        # Criar instância
        result = self.create_instance(
            instance_name=instance_name,
            webhook_url=webhook_url,
            qrcode=True
        )
        
        return {
            'instance': result,
            'webhook_url': webhook_url
        }
    
    def check_connection(self) -> bool:
        """
        Verifica se a Evolution API está acessível.
        
        Returns:
            True se conectado, False caso contrário
        """
        try:
            self._request('GET', '/instance/fetchInstances', timeout=5)
            return True
        except EvolutionAPIError:
            return False
