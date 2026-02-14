# apps/core/db_models.py
"""
Django ORM models for persistent session storage.

These models mirror the Pydantic Session structure but are designed
for SQLite3 persistence and admin interface queries.
"""

from django.db import models
from django.utils import timezone
from apps.core.states import SessionState


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
    
    # Contexto do usuário/empresa (capturado no momento da criação)
    usuario_nome = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Nome do Usuário'
    )
    empresa_nome = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Nome da Empresa'
    )
    empresa_id = models.IntegerField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name='ID da Empresa'
    )

    # Sugestao pendente (historico)
    pending_suggestion = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Sugestao Pendente'
    )

    # Estado da sessão
    estado = models.CharField(
        max_length=25,
        choices=SessionState.choices(),
        default=SessionState.COLETA.value,
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
    cnpj_extracted = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name='CNPJ Extraído'
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
    cnpj_error_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Tipo Erro CNPJ'
    )

    # Dados do Valor
    valor_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='null',
        verbose_name='Status Valor'
    )
    valor_extracted = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Valor Extraído'
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
    valor_error_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Tipo Erro Valor'
    )

    # Dados da Descrição
    descricao_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='null',
        verbose_name='Status Descrição'
    )
    descricao_extracted = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descrição Extraída'
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
    descricao_error_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Tipo Erro Descrição'
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
    user_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='Mensagem ao Usuário'
    )
    
    # Integração NFSe
    id_integracao = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        verbose_name='ID Integração NFSe'
    )

    # TTL e Expiração
    ttl = models.PositiveIntegerField(
        default=3600,
        verbose_name='TTL (segundos)'
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
            # Index for active session lookup (by telefone with recent update)
            models.Index(fields=['telefone', '-session_updated_at']),
        ]

    def __str__(self):
        return f"{self.sessao_id} - {self.telefone} ({self.estado})"

    @classmethod
    def from_session(cls, session, reason: str = 'manual', usuario_context: dict = None) -> 'SessionSnapshot':
        """
        Cria um SessionSnapshot a partir de um objeto Session (Pydantic).

        Args:
            session: Objeto Session do Pydantic
            reason: Motivo do snapshot (data_complete, confirmed, cancelled, expired, error)
            usuario_context: Dict opcional com nome, empresa_nome e empresa_id

        Returns:
            Instância de SessionSnapshot (não salva automaticamente)
        """
        invoice = session.invoice_data
        
        # Extrai contexto do usuário se fornecido
        usuario_nome = None
        empresa_nome = None
        empresa_id = session.empresa_id  # Priorizar empresa_id da sessao Pydantic
        if usuario_context:
            usuario_nome = usuario_context.get('nome')
            empresa_nome = usuario_context.get('empresa_nome')
            if not empresa_id:
                empresa_id = usuario_context.get('empresa_id')

        return cls(
            sessao_id=session.sessao_id,
            telefone=session.telefone,
            usuario_nome=usuario_nome,
            empresa_nome=empresa_nome,
            empresa_id=empresa_id,
            pending_suggestion=session.pending_suggestion,
            estado=session.estado,
            # CNPJ
            cnpj_status=invoice.cnpj.status,
            cnpj_extracted=invoice.cnpj.cnpj_extracted,
            cnpj=invoice.cnpj.cnpj,
            cnpj_razao_social=invoice.cnpj.razao_social,
            cnpj_issue=invoice.cnpj.cnpj_issue,
            cnpj_error_type=invoice.cnpj.error_type,
            # Valor
            valor_status=invoice.valor.status,
            valor_extracted=invoice.valor.valor_extracted,
            valor=invoice.valor.valor,
            valor_formatted=invoice.valor.valor_formatted,
            valor_issue=invoice.valor.valor_issue,
            valor_error_type=invoice.valor.error_type,
            # Descrição
            descricao_status=invoice.descricao.status,
            descricao_extracted=invoice.descricao.descricao_extracted,
            descricao=invoice.descricao.descricao,
            descricao_issue=invoice.descricao.descricao_issue,
            descricao_error_type=invoice.descricao.error_type,
            # Completude
            data_complete=invoice.data_complete,
            missing_fields=invoice.missing_fields,
            invalid_fields=invoice.invalid_fields,
            user_message=invoice.user_message,
            # TTL
            ttl=session.ttl,
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

    def to_session(self):
        """
        Converte SessionSnapshot de volta para um objeto Session (Pydantic).

        Returns:
            Objeto Session do Pydantic
        """
        from apps.core.models import Session, DadosNFSe, CNPJExtraido, ValorExtraido, DescricaoExtraida, Message

        # Reconstruct invoice_data
        invoice_data = DadosNFSe(
            cnpj=CNPJExtraido(
                cnpj_extracted=self.cnpj_extracted,
                cnpj=self.cnpj,
                razao_social=self.cnpj_razao_social,
                cnpj_issue=self.cnpj_issue,
                error_type=self.cnpj_error_type,
                status=self.cnpj_status,
            ),
            valor=ValorExtraido(
                valor_extracted=self.valor_extracted,
                valor=self.valor,
                valor_formatted=self.valor_formatted,
                valor_issue=self.valor_issue,
                error_type=self.valor_error_type,
                status=self.valor_status,
            ),
            descricao=DescricaoExtraida(
                descricao_extracted=self.descricao_extracted,
                descricao=self.descricao,
                descricao_issue=self.descricao_issue,
                error_type=self.descricao_error_type,
                status=self.descricao_status,
            ),
            data_complete=self.data_complete,
            missing_fields=self.missing_fields or [],
            invalid_fields=self.invalid_fields or [],
            user_message=self.user_message or '',
        )

        # Reconstruct context from SessionMessage
        context = []
        for msg in self.messages.all().order_by('order', 'timestamp'):
            context.append(Message(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
            ))

        # Reconstruct Session
        return Session(
            sessao_id=self.sessao_id,
            telefone=self.telefone,
            empresa_id=self.empresa_id,
            pending_suggestion=self.pending_suggestion,
            estado=self.estado,
            invoice_data=invoice_data,
            interaction_count=self.interaction_count,
            bot_message_count=self.bot_message_count,
            ai_calls_count=self.ai_calls_count,
            context=context,
            created_at=self.session_created_at,
            updated_at=self.session_updated_at,
            ttl=self.ttl,
        )

    def is_expired(self) -> bool:
        """
        Verifica se a sessão expirou baseado no TTL.

        Returns:
            True se expirou, False caso contrário
        """
        from django.utils import timezone
        age_seconds = (timezone.now() - self.session_updated_at).total_seconds()
        return age_seconds > self.ttl

    def update_from_session(self, session) -> None:
        """
        Atualiza os campos do snapshot a partir de um objeto Session.

        Args:
            session: Objeto Session do Pydantic
        """
        invoice = session.invoice_data

        self.estado = session.estado
        self.pending_suggestion = session.pending_suggestion
        if session.empresa_id:
            self.empresa_id = session.empresa_id
        # CNPJ
        self.cnpj_status = invoice.cnpj.status
        self.cnpj_extracted = invoice.cnpj.cnpj_extracted
        self.cnpj = invoice.cnpj.cnpj
        self.cnpj_razao_social = invoice.cnpj.razao_social
        self.cnpj_issue = invoice.cnpj.cnpj_issue
        self.cnpj_error_type = invoice.cnpj.error_type
        # Valor
        self.valor_status = invoice.valor.status
        self.valor_extracted = invoice.valor.valor_extracted
        self.valor = invoice.valor.valor
        self.valor_formatted = invoice.valor.valor_formatted
        self.valor_issue = invoice.valor.valor_issue
        self.valor_error_type = invoice.valor.error_type
        # Descrição
        self.descricao_status = invoice.descricao.status
        self.descricao_extracted = invoice.descricao.descricao_extracted
        self.descricao = invoice.descricao.descricao
        self.descricao_issue = invoice.descricao.descricao_issue
        self.descricao_error_type = invoice.descricao.error_type
        # Completude
        self.data_complete = invoice.data_complete
        self.missing_fields = invoice.missing_fields
        self.invalid_fields = invoice.invalid_fields
        self.user_message = invoice.user_message
        # TTL
        self.ttl = session.ttl
        # Métricas
        self.interaction_count = session.interaction_count
        self.bot_message_count = session.bot_message_count
        self.ai_calls_count = session.ai_calls_count
        # Timestamps
        self.session_updated_at = session.updated_at


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
