from django.urls import path
from . import views

app_name = 'contabilidade'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Empresas (CRUD principal)
    path('empresas/', views.EmpresaListView.as_view(), name='empresa_list'),
    path('empresas/nova/', views.EmpresaCreateView.as_view(), name='empresa_create'),
    path('empresas/<int:pk>/', views.EmpresaDetailView.as_view(), name='empresa_detail'),
    path('empresas/<int:pk>/editar/', views.EmpresaUpdateView.as_view(), name='empresa_update'),
    path('empresas/<int:pk>/excluir/', views.EmpresaDeleteView.as_view(), name='empresa_delete'),

    # Usuários da Empresa (submenu dentro da empresa)
    path('empresas/<int:empresa_pk>/usuarios/',
         views.UsuarioEmpresaListView.as_view(), name='usuario_empresa_list'),
    path('empresas/<int:empresa_pk>/usuarios/novo/',
         views.UsuarioEmpresaCreateView.as_view(), name='usuario_empresa_create'),
    path('empresas/<int:empresa_pk>/usuarios/<int:pk>/editar/',
         views.UsuarioEmpresaUpdateView.as_view(), name='usuario_empresa_update'),
    path('empresas/<int:empresa_pk>/usuarios/<int:pk>/excluir/',
         views.UsuarioEmpresaDeleteView.as_view(), name='usuario_empresa_delete'),

    # Certificados da Empresa (submenu dentro da empresa)
    path('empresas/<int:empresa_pk>/certificados/',
         views.CertificadoListView.as_view(), name='certificado_list'),
    path('empresas/<int:empresa_pk>/certificados/novo/',
         views.CertificadoCreateView.as_view(), name='certificado_create'),
    path('empresas/<int:empresa_pk>/certificados/<int:pk>/',
         views.CertificadoDetailView.as_view(), name='certificado_detail'),
    path('empresas/<int:empresa_pk>/certificados/<int:pk>/excluir/',
         views.CertificadoDeleteView.as_view(), name='certificado_delete'),
    path('empresas/<int:empresa_pk>/certificados/<int:pk>/enviar-tecnospeed/',
         views.CertificadoEnviarTecnospeedView.as_view(), name='certificado_enviar_tecnospeed'),

    # Sessões (lista sessões do APP Core)
    path('sessoes/', views.SessaoListView.as_view(), name='sessao_list'),
    path('sessoes/<int:pk>/', views.SessaoDetailView.as_view(), name='sessao_detail'),

    # Notas Fiscais
    path('notas/', views.NotaFiscalListView.as_view(), name='nota_fiscal_list'),
    path('notas/emitir/', views.NotaFiscalCreateView.as_view(), name='nota_fiscal_create'),

    # Usuários do Sistema (funcionários da contabilidade)
    path('usuarios/', views.UsuarioListView.as_view(), name='usuario_list'),
    path('usuarios/novo/', views.UsuarioCreateView.as_view(), name='usuario_create'),
    path('usuarios/<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_update'),
    path('usuarios/<int:pk>/excluir/', views.UsuarioDeleteView.as_view(), name='usuario_delete'),
]
