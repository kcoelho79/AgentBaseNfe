# apps/core/session_manager.py (renomeado de state_manager.py)

import json
import logging
from typing import Optional
from django.core.cache import cache
from apps.core.models import Session, DadosNFSe

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Gerencia sessões de conversa no Redis.
    
    Cada sessão contém:
    - Estado da máquina de estados
    - Dados da nota em construção
    - Histórico completo de mensagens
    - Métricas de uso (IA calls, interações, etc)
    """

    def __init__(self):
        self.prefix = 'session'

    def _get_key(self, telefone: str) -> str:
        """Gera chave Redis para o telefone."""
        return f'{self.prefix}:{telefone}'

    def get_session(self, telefone: str) -> Optional[Session]:
        """
        Recupera sessão do Redis.

        Args:
            telefone: Número de telefone do cliente

        Returns:
            Objeto Session ou None se não existir
        """
        key = self._get_key(telefone)
        data = cache.get(key)
      
        if not data:
            logger.debug('Nenhuma sessão encontrada', extra={'telefone': telefone})
            return None
        
        try:
            session = Session.from_json(data)
            logger.debug(f'Sessão recuperada: {session.sessao_id}', extra={'telefone': telefone})
            return session
        except Exception as e:
            logger.error(f'Erro ao deserializar sessão: {e}', extra={'telefone': telefone})
            return None

    def create_session(self, telefone: str, ttl: int = 3600) -> Session:
        """
        Cria nova sessão.

        Args:
            telefone: Número de telefone do cliente
            ttl: Tempo de vida em segundos

        Returns:
            Nova sessão criada
        """
        session = Session(telefone=telefone, ttl=ttl)
        self.save_session(session)
        
        logger.info(
            f'Sessão criada: {session.sessao_id}',
            extra={'telefone': telefone}
        )
        
        return session

    def save_session(self, session: Session) -> None:
        """
        Salva sessão no Redis.

        Args:
            session: Objeto Session para salvar
        """
        key = self._get_key(session.telefone)
        cache.set(key, session.to_json(), timeout=session.ttl)
        
        logger.debug(
            'Sessão salva',
            extra={
                'telefone': session.telefone,
                'sessao_id': session.sessao_id,
                'estado': session.estado
            }
        )

    def update_session(self, session: Session) -> None:
        """
        Atualiza sessão existente (alias para save_session).
        
        Args:
            session: Objeto Session para atualizar
        """
        self.save_session(session)

    def delete_session(self, telefone: str) -> bool:
        """
        Remove sessão do Redis.

        Args:
            telefone: Número de telefone do cliente

        Returns:
            True se removeu, False se não existia
        """
        key = self._get_key(telefone)
        existed = cache.delete(key)
        
        logger.info('Sessão removida', extra={'telefone': telefone})
        return bool(existed)

    def get_or_create_session(self, telefone: str, ttl: int = 3600) -> Session:
        """
        Recupera sessão existente ou cria nova.

        Args:
            telefone: Número de telefone do cliente
            ttl: Tempo de vida em segundos (só usado se criar nova)

        Returns:
            Sessão existente ou nova
        """
        session = self.get_session(telefone)
        
        if session:
            # Verificar se expirou
            if session.is_expired():
                logger.warning('Sessão expirada, criando nova', extra={'telefone': telefone})
                self.delete_session(telefone)
                return self.create_session(telefone, ttl)
            return session
        
        return self.create_session(telefone, ttl)

    def get_ttl(self, telefone: str) -> int:
        """
        Retorna o TTL (time to live) da sessão em segundos.

        Args:
            telefone: Número de telefone do cliente

        Returns:
            TTL em segundos ou 0 se não existir
        """
        key = self._get_key(telefone)
        ttl = cache.ttl(key)
        return ttl if ttl is not None else 0