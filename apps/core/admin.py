# apps/core/admin.py
"""
Admin interface for session persistence.

Provides:
- SessionSnapshot list with key fields
- SessionMessage inline for conversation timeline
- Filters for telefone, estado, data_complete, etc.
- Search functionality
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.core.db_models import SessionSnapshot, SessionMessage


class SessionMessageInline(admin.TabularInline):
    """
    Inline para exibir mensagens da conversa na timeline.

    Mostra timestamp formatado, role e conteúdo da mensagem.
    """
    model = SessionMessage
    extra = 0
    readonly_fields = ['timestamp_formatted', 'role_badge', 'content']
    fields = ['timestamp_formatted', 'role_badge', 'content']
    ordering = ['order', 'timestamp']
    can_delete = False

    def timestamp_formatted(self, obj):
        """Formata timestamp como dd/mm/yy hh:mm:ss"""
        if obj.timestamp:
            return obj.timestamp.strftime('%d/%m/%y %H:%M:%S')
        return '-'
    timestamp_formatted.short_description = 'Data/Hora'

    def role_badge(self, obj):
        """Exibe role com badge colorido"""
        colors = {
            'user': '#28a745',       # verde
            'assistant': '#007bff',  # azul
            'system': '#6c757d',     # cinza
        }
        labels = {
            'user': 'Usuário',
            'assistant': 'Bot',
            'system': 'Sistema',
        }
        color = colors.get(obj.role, '#6c757d')
        label = labels.get(obj.role, obj.role)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, label
        )
    role_badge.short_description = 'Papel'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SessionSnapshot)
class SessionSnapshotAdmin(admin.ModelAdmin):
    """
    Admin para SessionSnapshot.

    Exibe lista de sessões com campos principais e permite
    filtros por telefone, estado, status dos campos, etc.
    """

    # Campos exibidos na lista
    list_display = [
        'sessao_id',
        'telefone',
        'estado_badge',
        'cnpj_status_badge',
        'cnpj_display',
        'valor_status_badge',
        'valor_formatted',
        'descricao_status_badge',
        'descricao_preview',
        'data_complete_badge',
        'interaction_count',
        'ai_calls_count',
        'session_created_at',
    ]

    # Campos para busca
    search_fields = [
        'sessao_id',
        'telefone',
        'cnpj',
        'cnpj_razao_social',
        'descricao',
    ]

    # Filtros laterais
    list_filter = [
        'estado',
        'data_complete',
        'snapshot_reason',
        'cnpj_status',
        'valor_status',
        'descricao_status',
        'session_created_at',
    ]

    # Ordenação padrão
    ordering = ['-session_created_at']

    # Campos somente leitura (todos, pois são snapshots)
    readonly_fields = [
        'sessao_id',
        'telefone',
        'estado',
        'cnpj_status',
        'cnpj',
        'cnpj_razao_social',
        'cnpj_issue',
        'valor_status',
        'valor',
        'valor_formatted',
        'valor_issue',
        'descricao_status',
        'descricao',
        'descricao_issue',
        'data_complete',
        'missing_fields',
        'invalid_fields',
        'interaction_count',
        'bot_message_count',
        'ai_calls_count',
        'session_created_at',
        'session_updated_at',
        'snapshot_created_at',
        'snapshot_reason',
    ]

    # Inlines para mensagens
    inlines = [SessionMessageInline]

    # Organização dos campos no formulário de detalhe
    fieldsets = (
        ('Identificação', {
            'fields': ('sessao_id', 'telefone', 'estado', 'snapshot_reason')
        }),
        ('Dados do CNPJ', {
            'fields': ('cnpj_status', 'cnpj', 'cnpj_razao_social', 'cnpj_issue')
        }),
        ('Dados do Valor', {
            'fields': ('valor_status', 'valor', 'valor_formatted', 'valor_issue')
        }),
        ('Dados da Descrição', {
            'fields': ('descricao_status', 'descricao', 'descricao_issue')
        }),
        ('Status de Completude', {
            'fields': ('data_complete', 'missing_fields', 'invalid_fields')
        }),
        ('Métricas', {
            'fields': ('interaction_count', 'bot_message_count', 'ai_calls_count')
        }),
        ('Timestamps', {
            'fields': ('session_created_at', 'session_updated_at', 'snapshot_created_at')
        }),
    )

    # Paginação
    list_per_page = 25

    # Desabilitar adição/deleção manual
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Permitir deleção apenas para superusers
        return request.user.is_superuser

    # ==================== MÉTODOS DE DISPLAY CUSTOMIZADOS ====================

    def estado_badge(self, obj):
        """Exibe estado com badge colorido"""
        colors = {
            'coleta': '#17a2b8',
            'dados_incompletos': '#ffc107',
            'dados_completos': '#28a745',
            'aguardando_confirmacao': '#007bff',
            'processando': '#6f42c1',
            'aprovado': '#28a745',
            'rejeitado': '#dc3545',
            'erro': '#dc3545',
            'cancelado_usuario': '#fd7e14',
            'expirado': '#6c757d',
        }
        color = colors.get(obj.estado, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px; white-space: nowrap;">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    estado_badge.admin_order_field = 'estado'

    def cnpj_status_badge(self, obj):
        """Exibe status do CNPJ com badge"""
        return self._status_badge(obj.cnpj_status)
    cnpj_status_badge.short_description = 'CNPJ Status'
    cnpj_status_badge.admin_order_field = 'cnpj_status'

    def cnpj_display(self, obj):
        """Exibe CNPJ formatado"""
        if obj.cnpj:
            # Formata CNPJ: XX.XXX.XXX/XXXX-XX
            cnpj = obj.cnpj
            if len(cnpj) == 14:
                return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
            return cnpj
        return '-'
    cnpj_display.short_description = 'CNPJ'
    cnpj_display.admin_order_field = 'cnpj'

    def valor_status_badge(self, obj):
        """Exibe status do valor com badge"""
        return self._status_badge(obj.valor_status)
    valor_status_badge.short_description = 'Valor Status'
    valor_status_badge.admin_order_field = 'valor_status'

    def descricao_status_badge(self, obj):
        """Exibe status da descrição com badge"""
        return self._status_badge(obj.descricao_status)
    descricao_status_badge.short_description = 'Desc. Status'
    descricao_status_badge.admin_order_field = 'descricao_status'

    def descricao_preview(self, obj):
        """Exibe preview da descrição (50 chars)"""
        if obj.descricao:
            preview = obj.descricao[:50]
            if len(obj.descricao) > 50:
                preview += '...'
            return preview
        return '-'
    descricao_preview.short_description = 'Descrição'

    def data_complete_badge(self, obj):
        """Exibe status de completude com ícone"""
        if obj.data_complete:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">&#10004;</span>'
            )
        return format_html(
            '<span style="color: #dc3545;">&#10008;</span>'
        )
    data_complete_badge.short_description = 'Completo'
    data_complete_badge.admin_order_field = 'data_complete'

    def _status_badge(self, status):
        """Helper para criar badge de status"""
        colors = {
            'validated': '#28a745',
            'null': '#6c757d',
            'error': '#dc3545',
            'warning': '#ffc107',
        }
        labels = {
            'validated': 'OK',
            'null': '-',
            'error': 'Erro',
            'warning': 'Atenção',
        }
        color = colors.get(status, '#6c757d')
        label = labels.get(status, status)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 1px 6px; '
            'border-radius: 3px; font-size: 10px;">{}</span>',
            color, label
        )


@admin.register(SessionMessage)
class SessionMessageAdmin(admin.ModelAdmin):
    """
    Admin para SessionMessage (acesso direto às mensagens).

    Permite busca e filtro por mensagens individuais.
    """

    list_display = [
        'session_link',
        'timestamp_formatted',
        'role_badge',
        'content_preview',
    ]

    search_fields = [
        'content',
        'session__sessao_id',
        'session__telefone',
    ]

    list_filter = [
        'role',
        'timestamp',
    ]

    ordering = ['-timestamp']

    readonly_fields = [
        'session',
        'role',
        'content',
        'timestamp',
        'order',
    ]

    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def session_link(self, obj):
        """Link para a sessão"""
        from django.urls import reverse
        url = reverse('admin:core_sessionsnapshot_change', args=[obj.session.id])
        return format_html('<a href="{}">{}</a>', url, obj.session.sessao_id)
    session_link.short_description = 'Sessão'

    def timestamp_formatted(self, obj):
        """Formata timestamp como dd/mm/yy hh:mm:ss"""
        if obj.timestamp:
            return obj.timestamp.strftime('%d/%m/%y %H:%M:%S')
        return '-'
    timestamp_formatted.short_description = 'Data/Hora'
    timestamp_formatted.admin_order_field = 'timestamp'

    def role_badge(self, obj):
        """Exibe role com badge colorido"""
        colors = {
            'user': '#28a745',
            'assistant': '#007bff',
            'system': '#6c757d',
        }
        labels = {
            'user': 'Usuário',
            'assistant': 'Bot',
            'system': 'Sistema',
        }
        color = colors.get(obj.role, '#6c757d')
        label = labels.get(obj.role, obj.role)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, label
        )
    role_badge.short_description = 'Papel'
    role_badge.admin_order_field = 'role'

    def content_preview(self, obj):
        """Preview do conteúdo (100 chars)"""
        if obj.content:
            preview = obj.content[:100]
            if len(obj.content) > 100:
                preview += '...'
            return preview
        return '-'
    content_preview.short_description = 'Conteúdo'
