import json
import logging
from typing import Optional, Dict
from django.core.cache import cache
from django.utils import timezone
from apps.core.models import DadosNFSe

logger = logging.getLogger(__name__)


class StateManager:
    """
    Gerencia estados de conversas no Redis.

    Estados gerenciados:
    - coleta: Coletando dados iniciais
    - dados_incompletos: Faltam campos obrigatórios
    - dados_completos: Todos os campos preenchidos
    - validado: Dados validados
    - aguardando_confirmacao: Aguardando confirmação do cliente
    - confirmado: Cliente confirmou emissão
    - processando: Processando emissão NFSe
    - enviado_gateway: Enviado ao gateway
    - aprovado: NFSe aprovada
    - rejeitado: NFSe rejeitada
    - erro: Erro no processamento
    - expirado: Sessão expirada
    - cancelado_usuario: Cancelado pelo usuário
    """

    def __init__(self):
        self.prefix = 'protocolo_state'

    def _get_key(self, telefone: str) -> str:
        """Gera chave Redis para o telefone."""
        return f'{self.prefix}:{telefone}'

    def get_state(self, telefone: str) -> Optional[Dict]:
        """
        Recupera estado do Redis.

        Args:
            telefone: Número de telefone do cliente

        Returns:
            Dict com dados do estado ou None se não existir
        """
        key = self._get_key(telefone)
        data = cache.get(key)
      
        if not data:
            logger.debug(f'Nenhum estado encontrado para telefone', extra={'telefone': telefone})
            return None
        
        deserialized_data = json.loads(data) 
        logger.debug(f'Estado recuperado: {deserialized_data.get("protocolo_id")}', extra={'telefone': telefone})
        return deserialized_data
 

    def get_dados(self, telefone: str) -> Optional[DadosNFSe]:
        """ retorna os dados extraidos        """
        state = self.get_state(telefone)
        if not state or not state.get('dados'):
            return None
        return DadosNFSe.from_dict(state['dados'])

    def update_state(
        self,
        telefone: str,
        novo_estado: str,
        dados: DadosNFSe,
        protocolo_id: str,
        ttl: int = 3600
    ) -> None:
        """ atualiza ou cria estado no Redis. """
        key = self._get_key(telefone)

        # Recuperar estado anterior para preservar tentativas
        state_anterior = self.get_state(telefone)
        tentativas = state_anterior.get('tentativas', 0) if state_anterior else 0

        state_data = {
            'estado': novo_estado,
            'dados': dados.to_dict(),  # Serializa DadosNFSe automaticamente
            'protocolo_id': protocolo_id,
            'timestamp': timezone.now().isoformat(),
            'tentativas': tentativas
        }

        # Salvar no Redis com TTL
        cache.set(key, json.dumps(state_data), timeout=ttl)

        logger.info(
            'Estado atualizado',
            extra={
                'telefone': telefone,
                'novo_estado': novo_estado,
                'ttl': ttl
            }
        )

    def clear_state(self, telefone: str) -> None:
        """Remove estado do Redis."""
        key = self._get_key(telefone)
        cache.delete(key)
        logger.info('Estado removido', extra={'telefone': telefone})

    def increment_tentativa(self, telefone: str) -> int:
        """
        Incrementa contador de tentativas.

        Args:
            telefone: Número de telefone do cliente

        Returns:
            Número de tentativas após incremento
        """
        state = self.get_state(telefone)
        if state:
            state['tentativas'] += 1
            key = self._get_key(telefone)
            # Manter o mesmo TTL
            ttl = cache.ttl(key) or 3600
            cache.set(key, json.dumps(state), timeout=ttl)

            logger.info(
                'Tentativa incrementada',
                extra={
                    'telefone': telefone,
                    'tentativas': state['tentativas']
                }
            )
            return state['tentativas']
        return 0

    def get_ttl(self, telefone: str) -> int:
        """
        Retorna o TTL (time to live) do estado em segundos.

        Args:
            telefone: Número de telefone do cliente

        Returns:
            TTL em segundos ou 0 se não existir
        """
        key = self._get_key(telefone)
        ttl = cache.ttl(key)
        return ttl if ttl is not None else 0
