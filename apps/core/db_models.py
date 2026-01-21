# apps/core/db_models.py
"""
Django ORM models for persistent session storage.

These models mirror the Pydantic Session structure but are designed
for SQLite3 persistence and admin interface queries.
"""

from django.db import models
from django.utils import timezone


class SessionSnapshot(models.Model):
    """
    Snapshot persistente de uma sessão de conversa para emissão de NFSe.

    Salva automaticamente quando:
    - Dados estão completos (data_complete=True)
    - Sessão expira (mesmo incompleta, para log)
    - Usuário confirma ou cancela
    """

    # Identificação
    sessao_id = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name='ID da Sessão'
    )
    telefone = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name='Telefone'
    )

    # Estado da sessão
    ESTADO_CHOICES = [
        ('coleta', 'Coletando Dados'),
        ('dados_incompletos', 'Dados Incompletos'),
        ('dados_completos', 'Dados Completos'),
        ('aguardando_confirmacao', 'Aguardando Confirmação'),
        ('processando', 'Processando'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
        ('erro', 'Erro'),
        ('cancelado_usuario', 'Cancelado pelo Usuário'),
        ('expirado', 'Expirado'),
    ]
    estado = models.CharField(
        max_length=25,
        choices=ESTADO_CHOICES,
        default='coleta',
        db_index=True,
        verbose_name='Estado'
    )

    # Dados do CNPJ
    STATUS_CHOICES = [
        ('validated', 'Validado'),
        ('null', 'Não Informado'),
        ('error', 'Erro'),
        ('warning', 'Atenção'),
    ]
    cnpj_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='null',
        verbose_name='Status CNPJ'
    )
    cnpj = models.CharField(
        max_length=18,
        blank=True,
        null=True,
        verbose_name='CNPJ'
    )
    cnpj_razao_social = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Razão Social'
    )
    cnpj_issue = models.TextField(
        blank=True,
        null=True,
        verbose_name='Problema CNPJ'
    )

    # Dados do Valor
    valor_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='null',
        verbose_name='Status Valor'
    )
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Valor'
    )
    valor_formatted = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name='Valor Formatado'
    )
    valor_issue = models.TextField(
        blank=True,
        null=True,
        verbose_name='Problema Valor'
    )

    # Dados da Descrição
    descricao_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='null',
        verbose_name='Status Descrição'
    )
    descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descrição'
    )
    descricao_issue = models.TextField(
        blank=True,
        null=True,
        verbose_name='Problema Descrição'
    )

    # Status de completude
    data_complete = models.BooleanField(
        default=False,
        verbose_name='Dados Completos'
    )
    missing_fields = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Campos Faltantes'
    )
    invalid_fields = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Campos Inválidos'
    )

    # Métricas
    interaction_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Total Interações'
    )
    bot_message_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Mensagens Bot'
    )
    ai_calls_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Chamadas IA'
    )

    # Timestamps
    session_created_at = models.DateTimeField(
        verbose_name='Sessão Criada Em'
    )
    session_updated_at = models.DateTimeField(
        verbose_name='Sessão Atualizada Em'
    )
    snapshot_created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Snapshot Criado Em'
    )

    # Motivo do snapshot
    SNAPSHOT_REASON_CHOICES = [
        ('data_complete', 'Dados Completos'),
        ('confirmed', 'Confirmado pelo Usuário'),
        ('cancelled', 'Cancelado pelo Usuário'),
        ('expired', 'Sessão Expirada'),
        ('error', 'Erro na Sessão'),
        ('manual', 'Salvo Manualmente'),
    ]
    snapshot_reason = models.CharField(
        max_length=20,
        choices=SNAPSHOT_REASON_CHOICES,
        default='manual',
        verbose_name='Motivo do Snapshot'
    )

    class Meta:
        verbose_name = 'Sessão Persistida'
        verbose_name_plural = 'Sessões Persistidas'
        ordering = ['-session_created_at']
        indexes = [
            models.Index(fields=['telefone', 'estado']),
            models.Index(fields=['data_complete']),
            models.Index(fields=['session_created_at']),
        ]

    def __str__(self):
        return f"{self.sessao_id} - {self.telefone} ({self.estado})"

    @classmethod
    def from_session(cls, session, reason: str = 'manual') -> 'SessionSnapshot':
        """
        Cria um SessionSnapshot a partir de um objeto Session (Pydantic).

        Args:
            session: Objeto Session do Pydantic
            reason: Motivo do snapshot (data_complete, confirmed, cancelled, expired, error)

        Returns:
            Instância de SessionSnapshot (não salva automaticamente)
        """
        invoice = session.invoice_data

        return cls(
            sessao_id=session.sessao_id,
            telefone=session.telefone,
            estado=session.estado,
            # CNPJ
            cnpj_status=invoice.cnpj.status,
            cnpj=invoice.cnpj.cnpj,
            cnpj_razao_social=invoice.cnpj.razao_social,
            cnpj_issue=invoice.cnpj.cnpj_issue,
            # Valor
            valor_status=invoice.valor.status,
            valor=invoice.valor.valor,
            valor_formatted=invoice.valor.valor_formatted,
            valor_issue=invoice.valor.valor_issue,
            # Descrição
            descricao_status=invoice.descricao.status,
            descricao=invoice.descricao.descricao,
            descricao_issue=invoice.descricao.descricao_issue,
            # Completude
            data_complete=invoice.data_complete,
            missing_fields=invoice.missing_fields,
            invalid_fields=invoice.invalid_fields,
            # Métricas
            interaction_count=session.interaction_count,
            bot_message_count=session.bot_message_count,
            ai_calls_count=session.ai_calls_count,
            # Timestamps
            session_created_at=session.created_at,
            session_updated_at=session.updated_at,
            # Reason
            snapshot_reason=reason,
        )


class SessionMessage(models.Model):
    """
    Mensagem individual de uma sessão (timeline de conversa).

    Cada mensagem armazena o papel (user/assistant/system),
    conteúdo e timestamp para reconstrução da timeline.
    """

    session = models.ForeignKey(
        SessionSnapshot,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Sessão'
    )

    ROLE_CHOICES = [
        ('user', 'Usuário'),
        ('assistant', 'Assistente'),
        ('system', 'Sistema'),
    ]
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name='Papel'
    )

    content = models.TextField(
        verbose_name='Conteúdo'
    )

    timestamp = models.DateTimeField(
        verbose_name='Data/Hora'
    )

    # Ordem da mensagem na conversa (para garantir ordenação correta)
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem'
    )

    class Meta:
        verbose_name = 'Mensagem'
        verbose_name_plural = 'Mensagens'
        ordering = ['session', 'order', 'timestamp']
        indexes = [
            models.Index(fields=['session', 'timestamp']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        content_preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"[{self.role}] {content_preview}"
