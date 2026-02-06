from django.contrib import admin
from django.conf import settings
from django.utils.html import format_html
from .models import CanalWhatsApp, WebhookLog


@admin.register(CanalWhatsApp)
class CanalWhatsAppAdmin(admin.ModelAdmin):
    list_display = ['nome', 'instance_name', 'contabilidade', 'status', 'phone_number', 'is_active', 'created_at']
    list_filter = ['status', 'is_active', 'contabilidade']
    search_fields = ['nome', 'instance_name', 'phone_number']
    readonly_fields = ['instance_id', 'qrcode_base64', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('contabilidade', 'nome', 'instance_name')
        }),
        ('Evolution API', {
            'fields': ('instance_id', 'webhook_url', 'status', 'phone_number')
        }),
        ('QR Code', {
            'fields': ('qrcode_base64',),
            'classes': ('collapse',)
        }),
        ('Controle', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'instance_name', 'phone_from', 'processed', 'created_at']
    list_filter = ['event_type', 'processed', 'canal']
    search_fields = ['instance_name', 'phone_from', 'message_text']
    readonly_fields = ['canal', 'event_type', 'instance_name', 'payload', 'phone_from', 
                       'message_text', 'response_text', 'created_at']
    
    fieldsets = (
        ('Evento', {
            'fields': ('canal', 'event_type', 'instance_name')
        }),
        ('Mensagem', {
            'fields': ('phone_from', 'message_text', 'response_text')
        }),
        ('Processamento', {
            'fields': ('processed', 'error_message')
        }),
        ('Payload', {
            'fields': ('payload',),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('created_at',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


# ==================== EVOLUTION DATABASE ADMIN ====================

if getattr(settings, 'EVOLUTION_DB_ENABLED', False):
    from .models_evolution import (
        EvolutionInstance,
        EvolutionChat,
        EvolutionMessage,
        EvolutionContact
    )
    
    @admin.register(EvolutionInstance)
    class EvolutionInstanceAdmin(admin.ModelAdmin):
        """Admin readonly para instâncias da Evolution."""
        list_display = ['name', 'connection_status', 'owner_jid', 'profile_name', 'created_at']
        list_filter = ['connection_status', 'integration']
        search_fields = ['name', 'owner_jid', 'profile_name']
        readonly_fields = [f.name for f in EvolutionInstance._meta.fields]
        
        def has_add_permission(self, request):
            return False
        
        def has_change_permission(self, request, obj=None):
            return False
        
        def has_delete_permission(self, request, obj=None):
            return False
    
    
    @admin.register(EvolutionChat)
    class EvolutionChatAdmin(admin.ModelAdmin):
        """Admin readonly para chats da Evolution."""
        list_display = ['name', 'phone_number_display', 'instance_id', 'is_group_display', 'updated_at']
        list_filter = ['instance_id']
        search_fields = ['name', 'remote_jid']
        readonly_fields = [f.name for f in EvolutionChat._meta.fields]
        
        @admin.display(description='Telefone')
        def phone_number_display(self, obj):
            return obj.phone_number
        
        @admin.display(description='Grupo', boolean=True)
        def is_group_display(self, obj):
            return obj.is_group
        
        def has_add_permission(self, request):
            return False
        
        def has_change_permission(self, request, obj=None):
            return False
        
        def has_delete_permission(self, request, obj=None):
            return False
    
    
    @admin.register(EvolutionMessage)
    class EvolutionMessageAdmin(admin.ModelAdmin):
        """Admin readonly para mensagens da Evolution."""
        list_display = ['direction_display', 'phone_number_display', 'text_preview', 'message_type', 'timestamp_display']
        list_filter = ['message_type', 'instance_id', 'status']
        search_fields = ['push_name', 'id']
        readonly_fields = [f.name for f in EvolutionMessage._meta.fields] + [
            'text_content_display', 'key_remote_jid_display', 'key_from_me_display'
        ]
        
        @admin.display(description='Direção')
        def direction_display(self, obj):
            if obj.key_from_me:
                return format_html('<span style="color: green;">→ Enviada</span>')
            return format_html('<span style="color: blue;">← Recebida</span>')
        
        @admin.display(description='Telefone')
        def phone_number_display(self, obj):
            name = obj.push_name or ''
            phone = obj.phone_number
            if name:
                return f"{name} ({phone})"
            return phone
        
        @admin.display(description='Texto')
        def text_preview(self, obj):
            text = obj.text_content
            if len(text) > 50:
                return text[:50] + '...'
            return text
        
        @admin.display(description='Timestamp')
        def timestamp_display(self, obj):
            if obj.message_timestamp:
                from datetime import datetime
                return datetime.fromtimestamp(obj.message_timestamp)
            return '-'
        
        @admin.display(description='Conteúdo Completo')
        def text_content_display(self, obj):
            return obj.text_content
        
        @admin.display(description='Remote JID')
        def key_remote_jid_display(self, obj):
            return obj.key_remote_jid
        
        @admin.display(description='Enviada por mim', boolean=True)
        def key_from_me_display(self, obj):
            return obj.key_from_me
            return obj.text_content
        
        def has_add_permission(self, request):
            return False
        
        def has_change_permission(self, request, obj=None):
            return False
        
        def has_delete_permission(self, request, obj=None):
            return False
    
    
    @admin.register(EvolutionContact)
    class EvolutionContactAdmin(admin.ModelAdmin):
        """Admin readonly para contatos da Evolution."""
        list_display = ['push_name', 'phone_number_display', 'instance_id', 'updated_at']
        list_filter = ['instance_id']
        search_fields = ['push_name', 'remote_jid']
        readonly_fields = [f.name for f in EvolutionContact._meta.fields]
        
        @admin.display(description='Telefone')
        def phone_number_display(self, obj):
            return obj.phone_number
        
        def has_add_permission(self, request):
            return False
        
        def has_change_permission(self, request, obj=None):
            return False
        
        def has_delete_permission(self, request, obj=None):
            return False
