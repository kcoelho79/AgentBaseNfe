"""
Models para acesso READONLY ao banco de dados da Evolution API.

IMPORTANTE:
- Estes models são UNMANAGED (managed = False)
- O Django NÃO cria/altera estas tabelas
- São apenas para LEITURA de dados
- Requer EVOLUTION_DB_ENABLED=True no .env
- Requer DATABASE_ENABLED=true no .env da Evolution

Estrutura baseada na Evolution API v2.x com PostgreSQL.
"""

from django.db import models
from django.conf import settings


class EvolutionInstance(models.Model):
    """
    Instâncias WhatsApp na Evolution API.
    Tabela: Instance
    """
    id = models.CharField(primary_key=True, max_length=255)
    name = models.CharField(max_length=255)
    connection_status = models.CharField(max_length=50, db_column='connectionStatus')
    owner_jid = models.CharField(max_length=100, blank=True, null=True, db_column='ownerJid')
    profile_name = models.CharField(max_length=255, blank=True, null=True, db_column='profileName')
    profile_pic_url = models.TextField(blank=True, null=True, db_column='profilePicUrl')
    integration = models.CharField(max_length=50, blank=True, null=True)
    number = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(db_column='createdAt', blank=True, null=True)
    updated_at = models.DateTimeField(db_column='updatedAt', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Instance'
        verbose_name = 'Instância Evolution'
        verbose_name_plural = 'Instâncias Evolution'

    def __str__(self):
        return f"{self.name} ({self.connection_status})"


class EvolutionChat(models.Model):
    """
    Chats/Conversas na Evolution API.
    Tabela: Chat
    """
    id = models.CharField(primary_key=True, max_length=255)
    instance_id = models.CharField(max_length=255, db_column='instanceId')
    remote_jid = models.CharField(max_length=255, db_column='remoteJid')
    name = models.CharField(max_length=255, blank=True, null=True)
    labels = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(db_column='createdAt', blank=True, null=True)
    updated_at = models.DateTimeField(db_column='updatedAt', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Chat'
        verbose_name = 'Chat Evolution'
        verbose_name_plural = 'Chats Evolution'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name or self.remote_jid}"
    
    @property
    def phone_number(self):
        """Extrai número de telefone do remoteJid."""
        if self.remote_jid:
            return self.remote_jid.replace('@s.whatsapp.net', '').replace('@lid', '')
        return ''
    
    @property
    def is_group(self):
        """Verifica se é um grupo."""
        return '@g.us' in (self.remote_jid or '')


class EvolutionMessage(models.Model):
    """
    Mensagens na Evolution API.
    Tabela: Message
    
    IMPORTANTE: O campo 'key' é JSONB contendo:
    {
        "id": "message_id",
        "remoteJid": "5511999999999@s.whatsapp.net",
        "fromMe": true/false,
        "participant": "..."  (apenas em grupos)
    }
    """
    id = models.TextField(primary_key=True)
    instance_id = models.TextField(db_column='instanceId')
    
    # Campo key é JSONB contendo remoteJid, fromMe, id, participant
    key = models.JSONField()
    
    # Conteúdo
    push_name = models.CharField(max_length=255, blank=True, null=True, db_column='pushName')
    participant = models.CharField(max_length=255, blank=True, null=True)
    message = models.JSONField(blank=True, null=True)
    message_type = models.CharField(max_length=50, db_column='messageType', blank=True, null=True)
    context_info = models.JSONField(blank=True, null=True, db_column='contextInfo')
    source = models.CharField(max_length=50, blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=50, blank=True, null=True)
    session_id = models.TextField(blank=True, null=True, db_column='sessionId')
    
    # Timestamps
    message_timestamp = models.BigIntegerField(db_column='messageTimestamp', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Message'
        verbose_name = 'Mensagem Evolution'
        verbose_name_plural = 'Mensagens Evolution'
        ordering = ['-message_timestamp']

    def __str__(self):
        direction = '→' if self.key_from_me else '←'
        remote = self.key_remote_jid or 'unknown'
        return f"{direction} {remote[:20]}..."
    
    # ===== Properties para extrair dados do campo key (JSONB) =====
    
    @property
    def key_id(self):
        """ID da mensagem do campo key."""
        if self.key:
            return self.key.get('id', '')
        return ''
    
    @property
    def key_remote_jid(self):
        """remoteJid do campo key."""
        if self.key:
            return self.key.get('remoteJid', '')
        return ''
    
    @property
    def key_from_me(self):
        """fromMe do campo key (bool)."""
        if self.key:
            return self.key.get('fromMe', False)
        return False
    
    @property
    def key_participant(self):
        """participant do campo key (grupos)."""
        if self.key:
            return self.key.get('participant', '')
        return ''
    
    @property
    def phone_number(self):
        """Extrai número de telefone do remoteJid."""
        remote_jid = self.key_remote_jid
        if remote_jid:
            return remote_jid.replace('@s.whatsapp.net', '').replace('@lid', '').replace('@g.us', '')
        return ''
    
    @property
    def text_content(self):
        """Extrai texto da mensagem."""
        if not self.message:
            return ''
        
        # Tentar diferentes formatos de mensagem
        msg = self.message
        return (
            msg.get('conversation') or
            msg.get('extendedTextMessage', {}).get('text') or
            msg.get('imageMessage', {}).get('caption') or
            msg.get('videoMessage', {}).get('caption') or
            f"[{self.message_type or 'mídia'}]"
        )
    
    @property
    def is_group(self):
        """Verifica se é mensagem de grupo."""
        return '@g.us' in (self.key_remote_jid or '')


class EvolutionContact(models.Model):
    """
    Contatos na Evolution API.
    Tabela: Contact
    """
    id = models.CharField(primary_key=True, max_length=255)
    instance_id = models.CharField(max_length=255, db_column='instanceId')
    remote_jid = models.CharField(max_length=255, db_column='remoteJid')
    push_name = models.CharField(max_length=255, blank=True, null=True, db_column='pushName')
    profile_pic_url = models.TextField(blank=True, null=True, db_column='profilePicUrl')
    created_at = models.DateTimeField(db_column='createdAt', blank=True, null=True)
    updated_at = models.DateTimeField(db_column='updatedAt', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Contact'
        verbose_name = 'Contato Evolution'
        verbose_name_plural = 'Contatos Evolution'
        ordering = ['push_name']

    def __str__(self):
        return self.push_name or self.remote_jid
    
    @property
    def phone_number(self):
        """Extrai número de telefone."""
        if self.remote_jid:
            return self.remote_jid.replace('@s.whatsapp.net', '').replace('@lid', '')
        return ''


# ==================== DATABASE ROUTER ====================

class EvolutionDBRouter:
    """
    Router para direcionar models Evolution para o banco 'evolution'.
    
    Adicione em settings.py:
    DATABASE_ROUTERS = ['apps.whatsapp_api.models_evolution.EvolutionDBRouter']
    """
    
    evolution_models = {
        'evolutioninstance',
        'evolutionchat', 
        'evolutionmessage',
        'evolutioncontact',
    }
    
    def db_for_read(self, model, **hints):
        if model._meta.model_name in self.evolution_models:
            return 'evolution'
        return None
    
    def db_for_write(self, model, **hints):
        if model._meta.model_name in self.evolution_models:
            # Bloquear escrita - readonly
            return None
        return None
    
    def allow_relation(self, obj1, obj2, **hints):
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name in self.evolution_models:
            return False
        return None
