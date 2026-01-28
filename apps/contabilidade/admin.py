from django.contrib import admin
from django.utils.html import format_html
from .models import Contabilidade, Empresa, UsuarioEmpresa, Certificado


class UsuarioEmpresaInline(admin.TabularInline):
    '''Inline para exibir usuários autorizados dentro da Empresa.'''
    model = UsuarioEmpresa
    extra = 0
    fields = ['nome', 'telefone', 'email', 'cpf', 'is_active']
    readonly_fields = []
    show_change_link = True


@admin.register(Contabilidade)
class ContabilidadeAdmin(admin.ModelAdmin):
    '''Admin para Contabilidade.'''
    list_display = ['razao_social', 'cnpj', 'email', 'total_empresas', 'is_active', 'created_at']
    list_filter = ['is_active', 'estado']
    search_fields = ['razao_social', 'cnpj', 'email']
    ordering = ['razao_social']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Dados Básicos', {
            'fields': ('razao_social', 'nome_fantasia', 'cnpj')
        }),
        ('Contato', {
            'fields': ('email', 'telefone_ddd', 'telefone_numero')
        }),
        ('Endereço', {
            'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def total_empresas(self, obj):
        count = obj.empresas.count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    total_empresas.short_description = 'Total Empresas'


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    '''Admin para Empresa.'''
    list_display = ['razao_social', 'cpf_cnpj', 'contabilidade', 'total_usuarios', 'nfse_ativo', 'is_active']
    list_filter = ['is_active', 'nfse_ativo', 'simples_nacional', 'contabilidade']
    search_fields = ['razao_social', 'cpf_cnpj', 'nome_fantasia']
    ordering = ['razao_social']
    raw_id_fields = ['contabilidade']
    readonly_fields = ['tecnospeed_id', 'created_at', 'updated_at']
    inlines = [UsuarioEmpresaInline]
    
    fieldsets = (
        ('Dados Básicos', {
            'fields': ('contabilidade', 'razao_social', 'nome_fantasia', 'cpf_cnpj')
        }),
        ('Inscrições', {
            'fields': ('inscricao_municipal', 'inscricao_estadual')
        }),
        ('Regime Tributário', {
            'fields': ('simples_nacional', 'regime_tributario', 'regime_tributario_especial', 'incentivo_fiscal', 'incentivador_cultural')
        }),
        ('Endereço', {
            'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'tipo_logradouro', 'tipo_bairro', 'codigo_cidade', 'descricao_cidade', 'estado', 'codigo_pais', 'descricao_pais'),
            'classes': ('collapse',)
        }),
        ('Contato', {
            'fields': ('telefone_ddd', 'telefone_numero', 'email')
        }),
        ('NFS-e', {
            'fields': ('nfse_ativo', 'nfse_producao')
        }),
        ('Integração Tecnospeed', {
            'fields': ('tecnospeed_id',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def total_usuarios(self, obj):
        count = obj.usuarios_autorizados.count()
        ativos = obj.usuarios_autorizados.filter(is_active=True).count()
        if count > 0:
            return format_html(
                '<span style="font-weight: bold;">{}</span> <span style="color: green;">({} ativos)</span>',
                count, ativos
            )
        return format_html('<span style="color: #999;">0</span>')
    total_usuarios.short_description = 'Usuários'


@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    '''Admin para UsuarioEmpresa - Usuários autorizados das empresas.'''
    list_display = ['nome', 'telefone_formatado', 'get_empresa', 'get_contabilidade', 'email', 'is_active', 'created_at']
    list_filter = ['is_active', 'empresa__contabilidade', 'empresa']
    search_fields = ['nome', 'telefone', 'email', 'cpf', 'empresa__razao_social']
    ordering = ['-created_at']
    raw_id_fields = ['empresa']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Dados Básicos', {
            'fields': ('empresa', 'nome', 'cpf')
        }),
        ('Contato (WhatsApp)', {
            'fields': ('telefone', 'email')
        }),
        ('Endereço', {
            'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def telefone_formatado(self, obj):
        if obj.telefone:
            # Formata como +55 11 98929-3612
            tel = obj.telefone
            if len(tel) >= 12:
                return format_html(
                    '<span style="color: #25D366;"><i class="bi bi-whatsapp"></i> +{} {} {}</span>',
                    tel[:2], tel[2:4], tel[4:]
                )
            return format_html('<span style="color: #25D366;">+{}</span>', tel)
        return '-'
    telefone_formatado.short_description = 'WhatsApp'
    
    def get_empresa(self, obj):
        if obj.empresa:
            return format_html(
                '<a href="/admin/contabilidade/empresa/{}/change/">{}</a>',
                obj.empresa.pk,
                obj.empresa.razao_social
            )
        return '-'
    get_empresa.short_description = 'Empresa'
    get_empresa.admin_order_field = 'empresa__razao_social'
    
    def get_contabilidade(self, obj):
        if obj.empresa and obj.empresa.contabilidade:
            return obj.empresa.contabilidade.razao_social
        return '-'
    get_contabilidade.short_description = 'Contabilidade'
    get_contabilidade.admin_order_field = 'empresa__contabilidade__razao_social'


@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    '''Admin para Certificado Digital.'''
    list_display = ['get_empresa', 'nome_titular', 'cnpj_titular', 'validade', 'status_tecnospeed', 'is_active', 'created_at']
    list_filter = ['is_active', 'enviado_tecnospeed', 'empresa__contabilidade', 'validade']
    search_fields = ['nome_titular', 'cnpj_titular', 'empresa__razao_social']
    ordering = ['-created_at']
    raw_id_fields = ['empresa']
    readonly_fields = ['tecnospeed_id', 'data_envio_tecnospeed', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Empresa', {
            'fields': ('empresa',)
        }),
        ('Dados do Certificado', {
            'fields': ('arquivo', 'senha', 'nome_titular', 'cnpj_titular', 'validade')
        }),
        ('Integração Tecnospeed', {
            'fields': ('enviado_tecnospeed', 'tecnospeed_id', 'data_envio_tecnospeed'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def get_empresa(self, obj):
        if obj.empresa:
            return format_html(
                '<a href="/admin/contabilidade/empresa/{}/change/">{}</a>',
                obj.empresa.pk,
                obj.empresa.razao_social
            )
        return '-'
    get_empresa.short_description = 'Empresa'
    get_empresa.admin_order_field = 'empresa__razao_social'
    
    def status_tecnospeed(self, obj):
        if obj.enviado_tecnospeed:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Enviado</span><br><small>{}</small>',
                obj.data_envio_tecnospeed.strftime('%d/%m/%Y %H:%M') if obj.data_envio_tecnospeed else ''
            )
        return format_html('<span style="color: #999;">Não enviado</span>')
    status_tecnospeed.short_description = 'Tecnospeed'
