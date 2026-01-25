# apps/core/session_manager.py
"""
Session Manager - SQLite implementation.

Manages conversation sessions using Django ORM with SessionSnapshot model.
This replaces the previous Redis-based implementation for simplicity.
"""

from datetime import datetime
import logging
from typing import Optional
from django.db import transaction
from apps.core.models import Session
from apps.core.db_models import SessionSnapshot, SessionMessage
from apps.core.states import SessionState

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Gerencia sessões de conversa no SQLite.

    Cada sessão contém:
    - Estado da máquina de estados
    - Dados da nota em construção
    - Histórico completo de mensagens
    - Métricas de uso (IA calls, interações, etc)
    """

    def get_session(self, telefone: str) -> Optional[Session]:
        """
        Recupera sessão ativa do banco de dados.

        Uma sessão é considerada ativa se:
        1. Existe no banco
        2. Não está em estado terminal
        3. Não expirou (baseado no TTL)

        Args:
            telefone: Número de telefone do cliente

        Returns:
            Objeto Session (Pydantic) ou None se não existir sessão ativa
        """
        try:
            # Busca sessão mais recente que não está em estado terminal
            snapshot = (
                SessionSnapshot.objects
                .filter(telefone=telefone)
                .exclude(estado__in=SessionState.terminal_states())
                .order_by('-session_updated_at')
                .first()
            )

            if not snapshot:
                logger.debug('Nenhuma sessão ativa encontrada', extra={'telefone': telefone})
                return None

            # Verificar expiração (lazy expiration)
            if snapshot.is_expired():
                logger.warning(
                    f'Sessão expirada: {snapshot.sessao_id}',
                    extra={'telefone': telefone}
                )
                # Marcar como expirada no banco
                snapshot.estado = SessionState.EXPIRADO.value
                snapshot.snapshot_reason = 'expired'
                snapshot.save()
                return None

            # Converter para Pydantic Session
            session = snapshot.to_session()
            logger.debug(
                f'Sessão recuperada: {session.sessao_id}',
                extra={'telefone': telefone}
            )
            return session

        except Exception as e:
            logger.error(f'Erro ao recuperar sessão: {e}', extra={'telefone': telefone})
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
        self.save_session(session, reason='manual')

        logger.info(
            f'Sessão criada: {session.sessao_id}',
            extra={'telefone': telefone}
        )
        session.add_system_message(f"{datetime.now().strftime('%d/%m/%y %H:%M')} Nova Sessão criada: {session.sessao_id}.")


        return session

    @transaction.atomic
    def save_session(self, session: Session, reason: str = 'manual') -> None:
        """
        Salva sessão no banco de dados.

        Se a sessão já existe, atualiza. Caso contrário, cria nova.
        Também salva todas as mensagens do contexto.

        Args:
            session: Objeto Session para salvar
            reason: Motivo do snapshot (manual, data_complete, confirmed, etc)
        """
        try:
            # Capturar contexto do usuário (apenas na criação)
            usuario_context = None
            existing = SessionSnapshot.objects.filter(sessao_id=session.sessao_id).first()
            
            if not existing:
                # Primeira vez salvando - capturar contexto
                usuario_context = self._get_usuario_context(session.telefone)

            if existing:
                # Atualizar snapshot existente
                existing.update_from_session(session)
                existing.snapshot_reason = reason
                existing.save()

                # Atualizar mensagens (delete and recreate)
                existing.messages.all().delete()
                self._save_messages(existing, session)

                logger.debug(
                    f'Sessão atualizada: {session.sessao_id}',
                    extra={
                        'telefone': session.telefone,
                        'sessao_id': session.sessao_id,
                        'estado': session.estado
                    }
                )
            else:
                # Criar novo snapshot
                snapshot = SessionSnapshot.from_session(session, reason, usuario_context)
                snapshot.save()
                self._save_messages(snapshot, session)

                logger.debug(
                    f'Sessão criada: {session.sessao_id}',
                    extra={
                        'telefone': session.telefone,
                        'sessao_id': session.sessao_id,
                        'estado': session.estado
                    }
                )

        except Exception as e:
            logger.error(
                f'Erro ao salvar sessão: {e}',
                extra={
                    'telefone': session.telefone,
                    'sessao_id': session.sessao_id
                }
            )
            raise
    
    def _get_usuario_context(self, telefone: str) -> dict:
        """
        Busca contexto do usuário (nome e empresa) pelo telefone.
        
        Args:
            telefone: Número de telefone
            
        Returns:
            Dict com nome, empresa_nome e empresa_id (ou dicionário vazio se não encontrar)
        """
        try:
            from apps.contabilidade.models import UsuarioEmpresa
            
            usuario = UsuarioEmpresa.objects.select_related('empresa').filter(
                telefone=telefone,
                is_active=True
            ).first()
            
            if usuario:
                return {
                    'nome': usuario.nome,
                    'empresa_nome': usuario.empresa.nome_fantasia or usuario.empresa.razao_social,
                    'empresa_id': usuario.empresa.id
                }
        except Exception as e:
            logger.warning(f'Erro ao buscar contexto do usuário {telefone}: {e}')
        
        return {}

    def _save_messages(self, snapshot: SessionSnapshot, session: Session) -> None:
        """
        Salva todas as mensagens do contexto da sessão.

        Args:
            snapshot: SessionSnapshot para vincular mensagens
            session: Session com mensagens do contexto
        """
        messages_to_create = []
        for order, msg in enumerate(session.context):
            messages_to_create.append(
                SessionMessage(
                    session=snapshot,
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    order=order
                )
            )

        if messages_to_create:
            SessionMessage.objects.bulk_create(messages_to_create)

    def update_session(self, session: Session) -> None:
        """
        Atualiza sessão existente (alias para save_session).

        Args:
            session: Objeto Session para atualizar
        """
        self.save_session(session)

    def delete_session(self, telefone: str) -> bool:
        """
        Marca sessão como processada (não deleta fisicamente).

        Na nova arquitetura, não deletamos sessões - apenas marcamos
        como estado terminal. Isso preserva o histórico.

        Args:
            telefone: Número de telefone do cliente

        Returns:
            True se havia sessão ativa, False caso contrário
        """
        try:
            # Busca sessão ativa
            snapshot = (
                SessionSnapshot.objects
                .filter(telefone=telefone)
                .exclude(estado__in=SessionState.terminal_states())
                .order_by('-session_updated_at')
                .first()
            )

            if snapshot:
                # Marcar sessão como cancelada
                snapshot.estado = SessionState.CANCELADO_USUARIO.value
                snapshot.snapshot_reason = 'manual_clear'
                snapshot.save()
                logger.info(
                    f'Sessão finalizada: {snapshot.sessao_id}',
                    extra={'telefone': telefone}
                )
                return True

            return False

        except Exception as e:
            logger.error(f'Erro ao finalizar sessão: {e}', extra={'telefone': telefone})
            return False

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
            return session

        return self.create_session(telefone, ttl)

    def get_ttl(self, telefone: str) -> int:
        """
        Retorna o TTL (time to live) restante da sessão em segundos.

        Args:
            telefone: Número de telefone do cliente

        Returns:
            TTL restante em segundos ou 0 se não existir
        """
        try:
            snapshot = (
                SessionSnapshot.objects
                .filter(telefone=telefone)
                .exclude(estado__in=SessionState.terminal_states())
                .order_by('-session_updated_at')
                .first()
            )

            if not snapshot:
                return 0

            from django.utils import timezone
            age_seconds = (timezone.now() - snapshot.session_updated_at).total_seconds()
            remaining = max(0, snapshot.ttl - int(age_seconds))
            return remaining

        except Exception as e:
            logger.error(f'Erro ao obter TTL: {e}', extra={'telefone': telefone})
            return 0
