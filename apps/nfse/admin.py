from django.contrib import admin
from .models import ClienteTomador, EmpresaClienteTomador, NFSeEmissao, NFSeProcessada


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


@admin.register(EmpresaClienteTomador)
class EmpresaClienteTomadorAdmin(admin.ModelAdmin):
    list_display = [
        'empresa_display', 
        'cliente_tomador_display',
        'apelido',
        'total_notas_display',
        'total_valor_display',
        'primeira_nota_em', 
        'ultima_nota_em',
        'is_active'
    ]
    search_fields = [
        'empresa__razao_social',
        'cliente_tomador__razao_social',
        'cliente_tomador__cnpj',
        'apelido'
    ]
    list_filter = ['is_active', 'primeira_nota_em', 'empresa']
    readonly_fields = ['primeira_nota_em', 'ultima_nota_em']
    autocomplete_fields = ['empresa', 'cliente_tomador']
    
    fieldsets = (
        ('Relacionamento', {
            'fields': ('empresa', 'cliente_tomador', 'is_active')
        }),
        ('Customização', {
            'fields': ('apelido', 'observacoes')
        }),
        ('Metadados', {
            'fields': ('primeira_nota_em', 'ultima_nota_em'),
            'classes': ('collapse',)
        }),
    )
    
    def empresa_display(self, obj):
        return obj.empresa.razao_social
    empresa_display.short_description = 'Empresa'
    empresa_display.admin_order_field = 'empresa__razao_social'
    
    def cliente_tomador_display(self, obj):
        return f"{obj.cliente_tomador.cnpj} - {obj.cliente_tomador.razao_social}"
    cliente_tomador_display.short_description = 'Cliente Tomador'
    cliente_tomador_display.admin_order_field = 'cliente_tomador__razao_social'
    
    def total_notas_display(self, obj):
        """Mostra total de notas no list_display."""
        return obj.total_notas
    total_notas_display.short_description = 'Total Notas'
    
    def total_valor_display(self, obj):
        """Mostra valor total no list_display."""
        return f"R$ {obj.total_valor_emitido:,.2f}"
    total_valor_display.short_description = 'Valor Total'


@admin.register(NFSeEmissao)
class NFSeEmissaoAdmin(admin.ModelAdmin):
    list_display = ['id_integracao', 'status', 'prestador', 'tomador', 'valor_servico', 'created_at']
    search_fields = ['id_integracao', 'prestador__razao_social', 'tomador__razao_social']
    list_filter = ['status', 'created_at']
    readonly_fields = ['created_at', 'enviado_em', 'processado_em', 'payload_enviado', 'resposta_gateway']
    autocomplete_fields = ['prestador', 'tomador']
    
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
