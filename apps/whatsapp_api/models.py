from django.db import models
from apps.contabilidade.models import Contabilidade


class CanalWhatsApp(models.Model):
    """
    Canal de WhatsApp vinculado a uma contabilidade (tenant).
    Representa uma instância na Evolution API.
    """
    
    STATUS_CHOICES = [
        ('disconnected', 'Desconectado'),
        ('connecting', 'Conectando'),
        ('connected', 'Conectado'),
        ('qrcode', 'Aguardando QR Code'),
    ]
    
    contabilidade = models.ForeignKey(
        Contabilidade,
        on_delete=models.CASCADE,
        related_name='canais_whatsapp',
        verbose_name='contabilidade'
    )
    
    # Identificação
    nome = models.CharField(
        'nome',
        max_length=100,
        help_text='Nome identificador do canal'
    )
    
    # Evolution API
    instance_name = models.CharField(
        'nome da instância',
        max_length=100,
        unique=True,
        help_text='Nome único da instância na Evolution API'
    )
    instance_id = models.CharField(
        'ID da instância',
        max_length=100,
        blank=True,
        help_text='ID retornado pela Evolution API'
    )
    
    # Webhook
    webhook_url = models.URLField(
        'URL do webhook',
        blank=True,
        help_text='URL configurada para receber eventos'
    )
    
    # Status
    status = models.CharField(
        'status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='disconnected'
    )
    
    # Dados da conexão
    phone_number = models.CharField(
        'número conectado',
        max_length=20,
        blank=True,
        help_text='Número do WhatsApp conectado'
    )
    qrcode_base64 = models.TextField(
        'QR Code',
        blank=True,
        help_text='QR Code em base64 para conexão'
    )
    
    # Controle
    is_active = models.BooleanField('ativo', default=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)
    
    class Meta:
        verbose_name = 'canal WhatsApp'
        verbose_name_plural = 'canais WhatsApp'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contabilidade', 'is_active']),
            models.Index(fields=['instance_name']),
        ]
    
    def __str__(self):
        return f'{self.nome} ({self.instance_name})'
    
    @property
    def is_connected(self):
        """Verifica se o canal está conectado."""
        return self.status == 'connected'


class WebhookLog(models.Model):
    """
    Log de eventos recebidos via webhook.
    Usado para debug e auditoria.
    """
    
    canal = models.ForeignKey(
        CanalWhatsApp,
        on_delete=models.CASCADE,
        related_name='webhook_logs',
        verbose_name='canal',
        null=True,
        blank=True
    )
    
    # Evento
    event_type = models.CharField(
        'tipo do evento',
        max_length=50,
        help_text='Tipo do evento recebido (messages.upsert, connection.update, etc)'
    )
    instance_name = models.CharField(
        'nome da instância',
        max_length=100,
        blank=True
    )
    
    # Payload
    payload = models.JSONField(
        'payload',
        help_text='Payload completo do webhook'
    )
    
    # Processamento
    processed = models.BooleanField(
        'processado',
        default=False,
        help_text='Se o evento foi processado com sucesso'
    )
    error_message = models.TextField(
        'mensagem de erro',
        blank=True,
        help_text='Erro ocorrido durante processamento'
    )
    
    # Dados extraídos (para mensagens)
    phone_from = models.CharField(
        'telefone origem',
        max_length=20,
        blank=True
    )
    message_text = models.TextField(
        'texto da mensagem',
        blank=True
    )
    response_text = models.TextField(
        'texto da resposta',
        blank=True
    )
    
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    
    class Meta:
        verbose_name = 'log de webhook'
        verbose_name_plural = 'logs de webhook'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['canal', 'event_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['processed']),
        ]
    
    def __str__(self):
        return f'{self.event_type} - {self.created_at}'
