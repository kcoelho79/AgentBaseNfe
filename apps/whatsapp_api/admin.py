from django.contrib import admin
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
