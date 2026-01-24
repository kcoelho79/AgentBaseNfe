from django.contrib import admin
from .models import ClienteTomador, NFSeEmissao, NFSeProcessada


@admin.register(ClienteTomador)
class ClienteTomadorAdmin(admin.ModelAdmin):
    list_display = ['cnpj', 'razao_social', 'cidade', 'estado', 'created_at']
    search_fields = ['cnpj', 'razao_social', 'nome_fantasia']
    list_filter = ['estado', 'created_at']
    readonly_fields = ['created_at', 'updated_at', 'dados_receita_raw']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('cnpj', 'razao_social', 'nome_fantasia')
        }),
        ('Contato', {
            'fields': ('email', 'telefone')
        }),
        ('Inscrições', {
            'fields': ('inscricao_municipal', 'inscricao_estadual')
        }),
        ('Endereço', {
            'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 
                      'cidade', 'codigo_cidade', 'estado')
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at', 'dados_receita_raw'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NFSeEmissao)
class NFSeEmissaoAdmin(admin.ModelAdmin):
    list_display = ['id_integracao', 'status', 'prestador', 'tomador', 'valor_servico', 'created_at']
    search_fields = ['id_integracao', 'prestador__razao_social', 'tomador__razao_social']
    list_filter = ['status', 'created_at']
    readonly_fields = ['created_at', 'enviado_em', 'processado_em', 'payload_enviado', 'resposta_gateway']
    
    fieldsets = (
        ('Controle', {
            'fields': ('id_integracao', 'status', 'session')
        }),
        ('Partes', {
            'fields': ('prestador', 'tomador')
        }),
        ('Serviço', {
            'fields': ('codigo_servico', 'codigo_tributacao', 'descricao_servico', 'cnae')
        }),
        ('Valores', {
            'fields': ('valor_servico', 'desconto_condicionado', 'desconto_incondicionado')
        }),
        ('ISS', {
            'fields': ('tipo_tributacao', 'exigibilidade', 'aliquota')
        }),
        ('Processamento', {
            'fields': ('created_at', 'enviado_em', 'processado_em', 'erro_mensagem'),
            'classes': ('collapse',)
        }),
        ('Dados Técnicos', {
            'fields': ('payload_enviado', 'resposta_gateway'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NFSeProcessada)
class NFSeProcessadaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'emitente', 'destinatario', 'valor', 'data_emissao', 'status']
    search_fields = ['numero', 'chave', 'protocolo', 'emitente', 'destinatario']
    list_filter = ['status', 'data_emissao', 'data_autorizacao']
    readonly_fields = ['created_at', 'updated_at', 'webhook_payload']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('emissao', 'id_externo', 'numero', 'serie', 'chave', 'protocolo')
        }),
        ('Status', {
            'fields': ('status', 'mensagem', 'c_stat')
        }),
        ('Partes', {
            'fields': ('emitente', 'destinatario', 'valor')
        }),
        ('Datas', {
            'fields': ('data_emissao', 'data_autorizacao')
        }),
        ('Arquivos', {
            'fields': ('url_xml', 'url_pdf')
        }),
        ('Metadados', {
            'fields': ('destinada', 'documento', 'created_at', 'updated_at', 'webhook_payload'),
            'classes': ('collapse',)
        }),
    )
