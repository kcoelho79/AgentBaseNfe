import json
import logging
from typing import Optional, Dict
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Gerencia dados no Redis.

    """

    def __init__(self, chave:str, prefix:str = 'protocolo_state'):
        self.prefix = prefix
        self.chave = chave

    def _get_key(self ) -> str:
        """Gera chave Redis para o telefone."""
        return f'{self.prefix}:{self.chave}'

    def get_state(self) -> Optional[Dict]:
        """
        Recupera estado do Redis.

        Returns:
            Dict com dados do estado ou None se não existir
        """
        key = self._get_key()
        data = cache.get(key)

        if data:
            logger.debug(f'Estado recuperado: {data}', extra={'chave': self.chave})
            return json.loads(data) if isinstance(data, str) else data

        return None

    def update_state(
        self,
        chave: str,
        novo_estado: str,
        dados: Dict,
        protocolo_id: str,
        ttl: int = 3600
    ) -> None:
        """
        Atualiza ou cria estado no Redis.

        Args:
            chave: chave do cliente
            novo_estado: Novo estado da conversa
            dados: Dados extraídos/parciais
            protocolo_id: UUID do protocolo
            ttl: Time to live em segundos (default: 1h)
        """
        key = self._get_key()

        # Recuperar estado anterior para preservar tentativas
        state_anterior = self.get_state()
        tentativas = state_anterior.get('tentativas', 0) if state_anterior else 0

        state_data = {
            'estado': novo_estado,
            'dados': dados,
            'protocolo_id': protocolo_id,
            'timestamp': timezone.now().isoformat(),
            'tentativas': tentativas
        }

        # Salvar no Redis com TTL
        cache.set(key, json.dumps(state_data), timeout=ttl)

        logger.info(
            'Estado atualizado',
            extra={
                'chave': self.chave,
                'novo_estado': novo_estado,
                'ttl': ttl
            }
        )

    def clear_state(self) -> None:
        """Remove estado do Redis."""
        key = self._get_key()
        cache.delete(key)
        logger.info('Estado removido', extra={'chave': self.chave})

    def increment_tentativa(self) -> int:
        """
        Incrementa contador de tentativas.

        Returns:
            Número de tentativas após incremento
        """
        state = self.get_state()
        if state:
            state['tentativas'] += 1
            key = self._get_key()
            # Manter o mesmo TTL
            ttl = cache.ttl(key) or 3600
            cache.set(key, json.dumps(state), timeout=ttl)

            logger.info(
                'Tentativa incrementada',
                extra={
                    'chave': self.chave,
                    'tentativas': state['tentativas']
                }
            )
            return state['tentativas']
        return 0

    def get_ttl(self) -> int:
        """
        Retorna o TTL (time to live) do estado em segundos.
        Returns:
            TTL em segundos ou 0 se não existir
        """
        key = self._get_key()
        ttl = cache.ttl(key)
        return ttl if ttl is not None else 0
