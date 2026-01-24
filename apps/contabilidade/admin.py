from django.contrib import admin
from .models import Contabilidade, Empresa, UsuarioEmpresa, Certificado


@admin.register(Contabilidade)
class ContabilidadeAdmin(admin.ModelAdmin):
    '''Admin para Contabilidade.'''
    list_display = ['razao_social', 'cnpj', 'email', 'is_active', 'created_at']
    list_filter = ['is_active', 'estado']
    search_fields = ['razao_social', 'cnpj', 'email']
    ordering = ['razao_social']


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    '''Admin para Empresa.'''
    list_display = ['razao_social', 'cpf_cnpj', 'contabilidade', 'nfse_ativo', 'is_active']
    list_filter = ['is_active', 'nfse_ativo', 'simples_nacional', 'contabilidade']
    search_fields = ['razao_social', 'cpf_cnpj', 'nome_fantasia']
    ordering = ['razao_social']
    raw_id_fields = ['contabilidade']


@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    '''Admin para UsuarioEmpresa.'''
    list_display = ['nome', 'telefone', 'empresa', 'is_active', 'created_at']
    list_filter = ['is_active', 'empresa__contabilidade']
    search_fields = ['nome', 'telefone', 'email', 'cpf']
    ordering = ['nome']
    raw_id_fields = ['empresa']


@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    '''Admin para Certificado.'''
    list_display = ['empresa', 'nome_titular', 'validade', 'enviado_tecnospeed', 'is_active']
    list_filter = ['is_active', 'enviado_tecnospeed', 'empresa__contabilidade']
    search_fields = ['nome_titular', 'cnpj_titular', 'empresa__razao_social']
    ordering = ['-created_at']
    raw_id_fields = ['empresa']
    readonly_fields = ['tecnospeed_id', 'data_envio_tecnospeed']
