# apps/core/session_persistence.py
"""
Service for persisting sessions to SQLite database.

This module provides functions to save Session objects (Pydantic)
to the SQLite database as SessionSnapshot (Django ORM) records.

Usage:
    from apps.core.session_persistence import SessionPersistence, SnapshotReason

    # Save with specific reason
    SessionPersistence.save_session(session, SnapshotReason.CONFIRMED)
    SessionPersistence.save_session(session, SnapshotReason.CANCELLED)
    SessionPersistence.save_session(session, SnapshotReason.EXPIRED)
    SessionPersistence.save_session(session, SnapshotReason.ERROR)

    # Save only if data is complete
    SessionPersistence.save_if_complete(session)
"""

import logging
from enum import Enum
from typing import Optional
from django.db import transaction
from apps.core.db_models import SessionSnapshot, SessionMessage
from apps.core.models import Session


class SnapshotReason(str, Enum):
    """Reasons for saving a session snapshot."""
    DATA_COMPLETE = 'data_complete'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'
    ERROR = 'error'
    MANUAL = 'manual'

logger = logging.getLogger(__name__)


class SessionPersistence:
    """
    Service for persisting sessions to SQLite database.

    Provides methods to save sessions at different lifecycle points
    while avoiding duplicates and maintaining data integrity.
    """

    @staticmethod
    def exists(sessao_id: str) -> bool:
        """
        Check if a session already exists in the database.

        Args:
            sessao_id: Session ID to check

        Returns:
            True if exists, False otherwise
        """
        return SessionSnapshot.objects.filter(sessao_id=sessao_id).exists()

    @staticmethod
    @transaction.atomic
    def save_session(session: Session, reason: SnapshotReason = SnapshotReason.MANUAL) -> Optional[SessionSnapshot]:
        """
        Save a session to the database.

        If the session already exists, updates the existing record.
        Also saves all messages in the conversation context.

        Args:
            session: Pydantic Session object
            reason: SnapshotReason enum value

        Returns:
            SessionSnapshot instance or None if save failed
        """
        reason_value = reason.value if isinstance(reason, SnapshotReason) else reason
        try:
            # Check for existing session
            existing = SessionSnapshot.objects.filter(sessao_id=session.sessao_id).first()

            if existing:
                # Update existing snapshot
                snapshot = SessionPersistence._update_snapshot(existing, session, reason_value)
                logger.info(
                    f"Sessão atualizada no banco: {session.sessao_id}",
                    extra={
                        'telefone': session.telefone,
                        'sessao_id': session.sessao_id,
                        'reason': reason_value
                    }
                )
            else:
                # Create new snapshot
                snapshot = SessionPersistence._create_snapshot(session, reason_value)
                logger.info(
                    f"Sessão salva no banco: {session.sessao_id}",
                    extra={
                        'telefone': session.telefone,
                        'sessao_id': session.sessao_id,
                        'reason': reason_value
                    }
                )

            return snapshot

        except Exception as e:
            logger.error(
                f"Erro ao salvar sessão no banco: {e}",
                extra={
                    'telefone': session.telefone,
                    'sessao_id': session.sessao_id,
                    'reason': reason_value
                }
            )
            return None

    @staticmethod
    def _create_snapshot(session: Session, reason: str) -> SessionSnapshot:
        """
        Create a new SessionSnapshot from a Session.

        Args:
            session: Pydantic Session object
            reason: Reason for saving

        Returns:
            Created SessionSnapshot instance
        """
        snapshot = SessionSnapshot.from_session(session, reason)
        snapshot.save()

        # Save all messages
        SessionPersistence._save_messages(snapshot, session)

        return snapshot

    @staticmethod
    def _update_snapshot(existing: SessionSnapshot, session: Session, reason: str) -> SessionSnapshot:
        """
        Update an existing SessionSnapshot with new data.

        Args:
            existing: Existing SessionSnapshot
            session: Pydantic Session object with new data
            reason: Reason for update

        Returns:
            Updated SessionSnapshot instance
        """
        invoice = session.invoice_data

        # Update fields
        existing.estado = session.estado
        existing.cnpj_status = invoice.cnpj.status
        existing.cnpj = invoice.cnpj.cnpj
        existing.cnpj_razao_social = invoice.cnpj.razao_social
        existing.cnpj_issue = invoice.cnpj.cnpj_issue
        existing.valor_status = invoice.valor.status
        existing.valor = invoice.valor.valor
        existing.valor_formatted = invoice.valor.valor_formatted
        existing.valor_issue = invoice.valor.valor_issue
        existing.descricao_status = invoice.descricao.status
        existing.descricao = invoice.descricao.descricao
        existing.descricao_issue = invoice.descricao.descricao_issue
        existing.data_complete = invoice.data_complete
        existing.missing_fields = invoice.missing_fields
        existing.invalid_fields = invoice.invalid_fields
        existing.interaction_count = session.interaction_count
        existing.bot_message_count = session.bot_message_count
        existing.ai_calls_count = session.ai_calls_count
        existing.session_updated_at = session.updated_at
        existing.snapshot_reason = reason

        existing.save()

        # Update messages (delete old and recreate)
        existing.messages.all().delete()
        SessionPersistence._save_messages(existing, session)

        return existing

    @staticmethod
    def _save_messages(snapshot: SessionSnapshot, session: Session) -> None:
        """
        Save all messages from session context to database.

        Args:
            snapshot: SessionSnapshot to link messages to
            session: Session with context messages
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

    @staticmethod
    def save_if_complete(session: Session) -> Optional[SessionSnapshot]:
        """
        Save session only if data is complete.

        Args:
            session: Pydantic Session object

        Returns:
            SessionSnapshot if saved, None otherwise
        """
        if session.invoice_data.data_complete:
            return SessionPersistence.save_session(session, SnapshotReason.DATA_COMPLETE)
        return None

    @staticmethod
    def get_by_telefone(telefone: str, limit: int = 10) -> list:
        """
        Get sessions by phone number.

        Args:
            telefone: Phone number to search
            limit: Maximum number of results

        Returns:
            List of SessionSnapshot objects
        """
        return list(
            SessionSnapshot.objects
            .filter(telefone=telefone)
            .order_by('-session_created_at')[:limit]
        )

    @staticmethod
    def get_by_sessao_id(sessao_id: str) -> Optional[SessionSnapshot]:
        """
        Get session by session ID.

        Args:
            sessao_id: Session ID to search

        Returns:
            SessionSnapshot or None
        """
        return SessionSnapshot.objects.filter(sessao_id=sessao_id).first()

    @staticmethod
    def get_complete_sessions(limit: int = 50) -> list:
        """
        Get all sessions with complete data.

        Args:
            limit: Maximum number of results

        Returns:
            List of SessionSnapshot objects
        """
        return list(
            SessionSnapshot.objects
            .filter(data_complete=True)
            .order_by('-session_created_at')[:limit]
        )

    @staticmethod
    def get_sessions_by_estado(estado: str, limit: int = 50) -> list:
        """
        Get sessions by state.

        Args:
            estado: Session state to filter
            limit: Maximum number of results

        Returns:
            List of SessionSnapshot objects
        """
        return list(
            SessionSnapshot.objects
            .filter(estado=estado)
            .order_by('-session_created_at')[:limit]
        )
