# Plano de Implementação - Apps Contabilidade e Account

## 1. Visão Geral da Arquitetura

### 1.1 Estrutura de Diretórios Proposta

```
apps/
├── core/                    # (existente) Sistema conversacional NFSe
├── account/                 # NOVO - Autenticação e gerenciamento de conta
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   ├── backends.py          # Backend de autenticação por email
│   └── templates/
│       └── account/
│           ├── login.html
│           ├── register.html
│           └── profile.html
│
├── contabilidade/           # NOVO - Gestão de contabilidades e empresas
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   ├── services/
│   │   └── tecnospeed.py    # Integração com API Tecnospeed
│   └── templates/
│       └── contabilidade/
│           ├── dashboard.html
│           ├── empresa/
│           │   ├── list.html
│           │   ├── form.html
│           │   ├── detail.html
│           │   ├── usuario_list.html
│           │   ├── usuario_form.html
│           │   ├── certificado_list.html
│           │   └── certificado_form.html
│           ├── sessao/
│           │   └── list.html
│           ├── nota_fiscal/
│           │   ├── list.html
│           │   └── form.html
│           └── usuario/
│               ├── list.html
│               └── form.html
│
templates/
├── base.html                # Template base com design system
├── components/
│   ├── navbar.html
│   ├── sidebar.html
│   ├── card.html
│   ├── table.html
│   ├── form.html
│   ├── modal.html
│   └── alerts.html
└── home.html                # Página inicial pública

static/
├── css/
│   └── style.css            # Design system customizado
├── js/
│   └── main.js              # Scripts globais
└── img/
    └── logo.svg             # Logotipo do sistema
```

---

## 2. Design System

### 2.1 Paleta de Cores

```css
:root {
    /* Cores Primárias */
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --primary-color: #667eea;
    --primary-dark: #5a67d8;

    /* Fundo Escuro */
    --bg-dark: #1a1a2e;
    --bg-card: #16213e;
    --bg-input: #0f3460;

    /* Texto */
    --text-primary: #e4e4e7;
    --text-secondary: #a1a1aa;
    --text-muted: #71717a;

    /* Status */
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --info: #3b82f6;

    /* Bordas */
    --border-color: #374151;
}
```

### 2.2 Componentes Bootstrap Customizados

- Cards com fundo `--bg-card` e bordas sutis
- Botões com gradientes e hover effects
- Inputs com fundo escuro e bordas luminosas no focus
- Tabelas responsivas com hover states
- Navbar fixa com glassmorphism
- Sidebar colapsável com ícones

### 2.3 Layout Padrão - Menu Sidebar

```
┌─────────────────────────────────────────────────────────┐
│  NAVBAR (logo, nome usuário, dropdown perfil)           │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│ SIDEBAR  │              CONTEÚDO PRINCIPAL              │
│          │                                              │
│ - Dashb  │  ┌────────────────────────────────────────┐  │
│ - Empres │  │  Breadcrumb / Título da Página         │  │
│ - Sessõe │  ├────────────────────────────────────────┤  │
│ - Notas  │  │                                        │  │
│ - Usuári │  │         Área de Conteúdo               │  │
│          │  │                                        │  │
│          │  └────────────────────────────────────────┘  │
└──────────┴──────────────────────────────────────────────┘
```

### 2.4 Estrutura do Menu Sidebar

```
MENU PRINCIPAL
├── Dashboard
│   └── Visão geral com métricas
│
├── Empresas
│   └── Lista de empresas clientes da contabilidade
│       └── [Detalhe da Empresa] → Submenu interno:
│           ├── Usuários (cadastrar/listar)
│           └── Certificados (cadastrar/listar/deletar)
│
├── Sessões
│   └── Lista sessões do APP Core (filtros por estado)
│       └── Relacionadas aos usuários das empresas
│
├── Notas Fiscais
│   └── Lista notas por CNPJ da empresa
│       └── Opção: Emitir nota manual → Tecnospeed
│
└── Usuários
    └── Funcionários da contabilidade (sistema)
```

---

## 3. App Account - Modelos e Autenticação

### 3.1 Modelo User (Extensão do Django User)

```python
# apps/account/models.py

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    '''Manager customizado para User com email como identificador.'''

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    '''
    Usuário customizado com autenticação por email.
    Cada usuário pertence a uma contabilidade (tenant).
    '''
    username = None  # Remove username
    email = models.EmailField('e-mail', unique=True)

    contabilidade = models.ForeignKey(
        'contabilidade.Contabilidade',
        on_delete=models.CASCADE,
        related_name='usuarios',
        null=True,
        blank=True,
        verbose_name='contabilidade'
    )

    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('gerente', 'Gerente'),
        ('atendente', 'Atendente'),
    ]
    role = models.CharField(
        'função',
        max_length=20,
        choices=ROLE_CHOICES,
        default='atendente'
    )

    phone = models.CharField('telefone', max_length=20, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'

    def __str__(self):
        return self.email
```

### 3.2 Backend de Autenticação por Email

```python
# apps/account/backends.py

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailBackend(ModelBackend):
    '''Backend de autenticação usando email ao invés de username.'''

    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
```

### 3.3 Configuração em settings.py

```python
AUTH_USER_MODEL = 'account.User'

AUTHENTICATION_BACKENDS = [
    'apps.account.backends.EmailBackend',
]

LOGIN_URL = 'account:login'
LOGIN_REDIRECT_URL = 'contabilidade:dashboard'
LOGOUT_REDIRECT_URL = 'home'
```

---

## 4. App Contabilidade - Modelos

### 4.1 Modelo Contabilidade (Tenant)

```python
# apps/contabilidade/models.py

from django.db import models
from django.conf import settings


class Contabilidade(models.Model):
    '''
    Empresa de contabilidade (tenant).
    Cada contabilidade é isolada e tem suas próprias empresas e usuários.
    '''
    cnpj = models.CharField('CNPJ', max_length=18, unique=True)
    razao_social = models.CharField('razão social', max_length=200)
    nome_fantasia = models.CharField('nome fantasia', max_length=200, blank=True)

    # Contato
    email = models.EmailField('e-mail')
    telefone_ddd = models.CharField('DDD', max_length=2, blank=True)
    telefone_numero = models.CharField('telefone', max_length=15, blank=True)

    # Endereço
    cep = models.CharField('CEP', max_length=9, blank=True)
    logradouro = models.CharField('logradouro', max_length=200, blank=True)
    numero = models.CharField('número', max_length=20, blank=True)
    complemento = models.CharField('complemento', max_length=100, blank=True)
    bairro = models.CharField('bairro', max_length=100, blank=True)
    cidade = models.CharField('cidade', max_length=100, blank=True)
    estado = models.CharField('estado', max_length=2, blank=True)

    # Status
    is_active = models.BooleanField('ativo', default=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'contabilidade'
        verbose_name_plural = 'contabilidades'
        ordering = ['razao_social']

    def __str__(self):
        return self.nome_fantasia or self.razao_social
```

### 4.2 Modelo Empresa (Cliente da Contabilidade)

```python
class Empresa(models.Model):
    '''
    Empresa cliente da contabilidade.
    Compatível com a estrutura da API Tecnospeed.
    '''
    contabilidade = models.ForeignKey(
        Contabilidade,
        on_delete=models.CASCADE,
        related_name='empresas',
        verbose_name='contabilidade'
    )

    # Dados Básicos (compatível com Tecnospeed)
    cpf_cnpj = models.CharField('CPF/CNPJ', max_length=18)
    razao_social = models.CharField('razão social', max_length=200)
    nome_fantasia = models.CharField('nome fantasia', max_length=200, blank=True)
    inscricao_municipal = models.CharField('inscrição municipal', max_length=20, blank=True)
    inscricao_estadual = models.CharField('inscrição estadual', max_length=20, blank=True)

    # Regime Tributário
    simples_nacional = models.BooleanField('Simples Nacional', default=False)
    REGIME_CHOICES = [
        (1, 'Simples Nacional'),
        (2, 'Simples Nacional - Excesso'),
        (3, 'Regime Normal'),
    ]
    regime_tributario = models.IntegerField(
        'regime tributário',
        choices=REGIME_CHOICES,
        default=3
    )
    incentivo_fiscal = models.BooleanField('incentivo fiscal', default=False)
    incentivador_cultural = models.BooleanField('incentivador cultural', default=False)
    REGIME_ESPECIAL_CHOICES = [
        (0, 'Nenhum'),
        (1, 'Microempresa Municipal'),
        (2, 'Estimativa'),
        (3, 'Sociedade de Profissionais'),
        (4, 'Cooperativa'),
        (5, 'MEI'),
        (6, 'ME/EPP'),
    ]
    regime_tributario_especial = models.IntegerField(
        'regime tributário especial',
        choices=REGIME_ESPECIAL_CHOICES,
        default=0
    )

    # Endereço
    cep = models.CharField('CEP', max_length=9, blank=True)
    logradouro = models.CharField('logradouro', max_length=200, blank=True)
    numero = models.CharField('número', max_length=20, blank=True)
    complemento = models.CharField('complemento', max_length=100, blank=True)
    bairro = models.CharField('bairro', max_length=100, blank=True)
    tipo_logradouro = models.CharField('tipo logradouro', max_length=50, blank=True)
    tipo_bairro = models.CharField('tipo bairro', max_length=50, blank=True)
    codigo_cidade = models.CharField('código cidade (IBGE)', max_length=7, blank=True)
    descricao_cidade = models.CharField('cidade', max_length=100, blank=True)
    estado = models.CharField('estado', max_length=2, blank=True)
    codigo_pais = models.CharField('código país', max_length=4, default='1058')
    descricao_pais = models.CharField('país', max_length=100, default='Brasil')

    # Contato
    telefone_ddd = models.CharField('DDD', max_length=2, blank=True)
    telefone_numero = models.CharField('telefone', max_length=15, blank=True)
    email = models.EmailField('e-mail', blank=True)

    # NFSe Config
    nfse_ativo = models.BooleanField('NFSe ativo', default=True)
    nfse_producao = models.BooleanField('ambiente produção', default=False)

    # Tecnospeed
    tecnospeed_id = models.CharField(
        'ID empresa Tecnospeed',
        max_length=50,
        blank=True,
        help_text='ID retornado pela API Tecnospeed ao cadastrar empresa'
    )

    # Status
    is_active = models.BooleanField('ativo', default=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'empresa'
        verbose_name_plural = 'empresas'
        ordering = ['razao_social']
        unique_together = ['contabilidade', 'cpf_cnpj']
        indexes = [
            models.Index(fields=['contabilidade', 'cpf_cnpj']),
            models.Index(fields=['contabilidade', 'is_active']),
        ]

    def __str__(self):
        return f'{self.razao_social} ({self.cpf_cnpj})'
```

### 4.3 Modelo UsuarioEmpresa (Pessoa Física autorizada)

```python
class UsuarioEmpresa(models.Model):
    '''
    Pessoa física autorizada a solicitar emissão de notas para uma Empresa.
    São os usuários que interagem via WhatsApp.
    '''
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='usuarios_autorizados',
        verbose_name='empresa'
    )

    nome = models.CharField('nome', max_length=200)
    cpf = models.CharField('CPF', max_length=14, blank=True)
    telefone = models.CharField('telefone (WhatsApp)', max_length=20)
    email = models.EmailField('e-mail', blank=True)

    # Endereço (opcional)
    cep = models.CharField('CEP', max_length=9, blank=True)
    logradouro = models.CharField('logradouro', max_length=200, blank=True)
    numero = models.CharField('número', max_length=20, blank=True)
    complemento = models.CharField('complemento', max_length=100, blank=True)
    bairro = models.CharField('bairro', max_length=100, blank=True)
    cidade = models.CharField('cidade', max_length=100, blank=True)
    estado = models.CharField('estado', max_length=2, blank=True)

    is_active = models.BooleanField('ativo', default=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'usuário da empresa'
        verbose_name_plural = 'usuários da empresa'
        ordering = ['nome']
        unique_together = ['empresa', 'telefone']

    def __str__(self):
        return f'{self.nome} - {self.telefone}'
```

### 4.4 Modelo Certificado (Gestão de Certificados Digitais)

```python
class Certificado(models.Model):
    '''
    Certificado digital para assinatura de NFSe.
    Pertence a uma Empresa (cliente da contabilidade).
    '''
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='certificados',
        verbose_name='empresa'
    )

    arquivo = models.FileField(
        'arquivo (.pfx)',
        upload_to='certificados/',
        help_text='Arquivo do certificado digital no formato .pfx'
    )
    senha = models.CharField(
        'senha',
        max_length=100,
        help_text='Senha do certificado (armazenada de forma segura)'
    )

    # Dados extraídos do certificado
    nome_titular = models.CharField('nome titular', max_length=200, blank=True)
    cnpj_titular = models.CharField('CNPJ titular', max_length=18, blank=True)
    validade = models.DateField('data validade', null=True, blank=True)

    # Integração Tecnospeed
    tecnospeed_id = models.CharField(
        'ID Tecnospeed',
        max_length=50,
        blank=True,
        help_text='ID retornado ao enviar para Tecnospeed'
    )
    enviado_tecnospeed = models.BooleanField('enviado para Tecnospeed', default=False)
    data_envio_tecnospeed = models.DateTimeField(
        'data envio Tecnospeed',
        null=True,
        blank=True
    )

    is_active = models.BooleanField('ativo', default=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'certificado digital'
        verbose_name_plural = 'certificados digitais'
        ordering = ['-created_at']

    def __str__(self):
        return f'Certificado {self.empresa.razao_social} - {self.validade}'

    @property
    def is_valid(self):
        '''Verifica se o certificado está dentro da validade.'''
        from django.utils import timezone
        if not self.validade:
            return False
        return self.validade >= timezone.now().date()

    @property
    def days_to_expire(self):
        '''Dias até a expiração do certificado.'''
        from django.utils import timezone
        if not self.validade:
            return None
        delta = self.validade - timezone.now().date()
        return delta.days
```

---

## 5. URLs e Views

### 5.1 URLs Principais (config/urls.py)

```python
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Home pública
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Apps
    path('account/', include('apps.account.urls', namespace='account')),
    path('app/', include('apps.contabilidade.urls', namespace='contabilidade')),

    # API existente (core)
    path('chat/', include('apps.core.urls')),
]
```

### 5.2 URLs Account (apps/account/urls.py)

```python
from django.urls import path
from . import views

app_name = 'account'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
]
```

### 5.3 URLs Contabilidade (apps/contabilidade/urls.py)

```python
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

    # Notas Fiscais
    path('notas/', views.NotaFiscalListView.as_view(), name='nota_fiscal_list'),
    path('notas/emitir/', views.NotaFiscalCreateView.as_view(), name='nota_fiscal_create'),

    # Usuários do Sistema (funcionários da contabilidade)
    path('usuarios/', views.UsuarioListView.as_view(), name='usuario_list'),
    path('usuarios/novo/', views.UsuarioCreateView.as_view(), name='usuario_create'),
    path('usuarios/<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_update'),
    path('usuarios/<int:pk>/excluir/', views.UsuarioDeleteView.as_view(), name='usuario_delete'),
]
```

---

## 6. Views Principais

### 6.1 Mixin para Isolamento Multi-tenant

```python
# apps/contabilidade/mixins.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from .models import Empresa


class TenantMixin(LoginRequiredMixin):
    '''
    Mixin que filtra querysets pela contabilidade do usuário logado.
    '''

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.request.user, 'contabilidade') and self.request.user.contabilidade:
            return qs.filter(contabilidade=self.request.user.contabilidade)
        return qs.none()

    def form_valid(self, form):
        if hasattr(form.instance, 'contabilidade'):
            form.instance.contabilidade = self.request.user.contabilidade
        return super().form_valid(form)


class EmpresaContextMixin(TenantMixin):
    '''
    Mixin para views que operam dentro do contexto de uma empresa.
    Adiciona a empresa ao contexto e valida acesso.
    '''

    def get_empresa(self):
        empresa_pk = self.kwargs.get('empresa_pk')
        return get_object_or_404(
            Empresa,
            pk=empresa_pk,
            contabilidade=self.request.user.contabilidade
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = self.get_empresa()
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(empresa=self.get_empresa())

    def form_valid(self, form):
        form.instance.empresa = self.get_empresa()
        return super().form_valid(form)
```

### 6.2 Dashboard View

```python
# apps/contabilidade/views.py

from django.views.generic import TemplateView
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from .mixins import TenantMixin
from .models import Empresa, Certificado


class DashboardView(TenantMixin, TemplateView):
    template_name = 'contabilidade/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contabilidade = self.request.user.contabilidade

        if contabilidade:
            hoje = timezone.now().date()
            inicio_mes = hoje.replace(day=1)

            # Métricas básicas
            context['total_empresas'] = Empresa.objects.filter(
                contabilidade=contabilidade,
                is_active=True
            ).count()

            context['certificados_vencendo'] = Certificado.objects.filter(
                empresa__contabilidade=contabilidade,
                validade__lte=hoje + timedelta(days=30),
                validade__gte=hoje,
                is_active=True
            ).count()

            # TODO: Integrar com SessionSnapshot para métricas de notas
            context['notas_mes'] = 0
            context['notas_hoje'] = 0
            context['notas_sucesso'] = 0
            context['notas_erro'] = 0

        return context
```

### 6.3 Empresa Views (CRUD)

```python
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from .models import Empresa
from .forms import EmpresaForm


class EmpresaListView(TenantMixin, ListView):
    model = Empresa
    template_name = 'contabilidade/empresa/list.html'
    context_object_name = 'empresas'
    paginate_by = 20


class EmpresaCreateView(TenantMixin, CreateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'contabilidade/empresa/form.html'
    success_url = reverse_lazy('contabilidade:empresa_list')


class EmpresaDetailView(TenantMixin, DetailView):
    model = Empresa
    template_name = 'contabilidade/empresa/detail.html'
    context_object_name = 'empresa'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona contagem de usuários e certificados
        context['total_usuarios'] = self.object.usuarios_autorizados.filter(is_active=True).count()
        context['total_certificados'] = self.object.certificados.filter(is_active=True).count()
        return context


class EmpresaUpdateView(TenantMixin, UpdateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'contabilidade/empresa/form.html'

    def get_success_url(self):
        return reverse_lazy('contabilidade:empresa_detail', kwargs={'pk': self.object.pk})


class EmpresaDeleteView(TenantMixin, DeleteView):
    model = Empresa
    template_name = 'contabilidade/empresa/confirm_delete.html'
    success_url = reverse_lazy('contabilidade:empresa_list')
```

### 6.4 Sessões View (Lista sessões do APP Core)

```python
from apps.core.db_models import SessionSnapshot


class SessaoListView(TenantMixin, ListView):
    model = SessionSnapshot
    template_name = 'contabilidade/sessao/list.html'
    context_object_name = 'sessoes'
    paginate_by = 20

    def get_queryset(self):
        '''
        Filtra sessões pelos telefones dos usuários das empresas
        da contabilidade do usuário logado.
        '''
        contabilidade = self.request.user.contabilidade
        if not contabilidade:
            return SessionSnapshot.objects.none()

        # Busca telefones dos usuários das empresas desta contabilidade
        from .models import UsuarioEmpresa
        telefones = UsuarioEmpresa.objects.filter(
            empresa__contabilidade=contabilidade,
            is_active=True
        ).values_list('telefone', flat=True)

        qs = SessionSnapshot.objects.filter(telefone__in=telefones)

        # Filtro por estado
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Lista de estados para filtro
        context['estados'] = [
            ('coleta', 'Coleta'),
            ('dados_incompletos', 'Dados Incompletos'),
            ('dados_completos', 'Dados Completos'),
            ('aguardando_confirmacao', 'Aguardando Confirmação'),
            ('processando', 'Processando'),
            ('cancelado_usuario', 'Cancelado'),
            ('erro', 'Erro'),
            ('expirado', 'Expirado'),
        ]
        context['estado_selecionado'] = self.request.GET.get('estado', '')
        return context
```

### 6.5 Notas Fiscais Views

```python
class NotaFiscalListView(TenantMixin, ListView):
    '''
    Lista notas fiscais baseado nos SessionSnapshots com estado 'processando'.
    Filtrado pelos CNPJs das empresas da contabilidade.
    '''
    model = SessionSnapshot
    template_name = 'contabilidade/nota_fiscal/list.html'
    context_object_name = 'notas'
    paginate_by = 20

    def get_queryset(self):
        contabilidade = self.request.user.contabilidade
        if not contabilidade:
            return SessionSnapshot.objects.none()

        # Busca CNPJs das empresas desta contabilidade
        cnpjs = Empresa.objects.filter(
            contabilidade=contabilidade,
            is_active=True
        ).values_list('cpf_cnpj', flat=True)

        # Normaliza CNPJs (remove pontuação)
        cnpjs_normalizados = [c.replace('.', '').replace('/', '').replace('-', '') for c in cnpjs]

        qs = SessionSnapshot.objects.filter(
            cnpj__in=cnpjs_normalizados,
            estado='processando'
        )

        # Filtro por empresa
        empresa_id = self.request.GET.get('empresa')
        if empresa_id:
            empresa = Empresa.objects.filter(pk=empresa_id, contabilidade=contabilidade).first()
            if empresa:
                cnpj_normalizado = empresa.cpf_cnpj.replace('.', '').replace('/', '').replace('-', '')
                qs = qs.filter(cnpj=cnpj_normalizado)

        return qs.order_by('-created_at')


class NotaFiscalCreateView(TenantMixin, TemplateView):
    '''
    View para emissão manual de nota fiscal.
    '''
    template_name = 'contabilidade/nota_fiscal/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contabilidade = self.request.user.contabilidade
        context['empresas'] = Empresa.objects.filter(
            contabilidade=contabilidade,
            is_active=True,
            nfse_ativo=True
        )
        return context
```

---

## 7. Templates Base

### 7.1 Template Base (templates/base.html)

```html
{% load static %}
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AgentNFe{% endblock %}</title>

    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
    <!-- Custom CSS -->
    <link href="{% static 'css/style.css' %}" rel="stylesheet">

    {% block extra_css %}{% endblock %}
</head>
<body class="bg-dark">
    {% if user.is_authenticated %}
        {% include 'components/navbar.html' %}

        <div class="container-fluid">
            <div class="row">
                {% include 'components/sidebar.html' %}

                <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4 py-4">
                    {% include 'components/alerts.html' %}
                    {% block content %}{% endblock %}
                </main>
            </div>
        </div>
    {% else %}
        {% block public_content %}{% endblock %}
    {% endif %}

    <!-- Bootstrap 5 JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <!-- Custom JS -->
    <script src="{% static 'js/main.js' %}"></script>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

### 7.2 Sidebar Component (templates/components/sidebar.html)

```html
{% load static %}
<nav id="sidebar" class="col-md-3 col-lg-2 d-md-block sidebar collapse">
    <div class="position-sticky pt-3">
        <ul class="nav flex-column">
            <!-- Dashboard -->
            <li class="nav-item">
                <a class="nav-link {% if request.resolver_match.url_name == 'dashboard' %}active{% endif %}"
                   href="{% url 'contabilidade:dashboard' %}">
                    <i class="bi bi-speedometer2 me-2"></i>
                    Dashboard
                </a>
            </li>

            <!-- Empresas -->
            <li class="nav-item">
                <a class="nav-link {% if 'empresa' in request.resolver_match.url_name %}active{% endif %}"
                   href="{% url 'contabilidade:empresa_list' %}">
                    <i class="bi bi-building me-2"></i>
                    Empresas
                </a>
            </li>

            <!-- Sessões -->
            <li class="nav-item">
                <a class="nav-link {% if 'sessao' in request.resolver_match.url_name %}active{% endif %}"
                   href="{% url 'contabilidade:sessao_list' %}">
                    <i class="bi bi-chat-dots me-2"></i>
                    Sessões
                </a>
            </li>

            <!-- Notas Fiscais -->
            <li class="nav-item">
                <a class="nav-link {% if 'nota_fiscal' in request.resolver_match.url_name %}active{% endif %}"
                   href="{% url 'contabilidade:nota_fiscal_list' %}">
                    <i class="bi bi-file-earmark-text me-2"></i>
                    Notas Fiscais
                </a>
            </li>

            <!-- Usuários do Sistema -->
            <li class="nav-item">
                <a class="nav-link {% if request.resolver_match.url_name == 'usuario_list' %}active{% endif %}"
                   href="{% url 'contabilidade:usuario_list' %}">
                    <i class="bi bi-people me-2"></i>
                    Usuários
                </a>
            </li>
        </ul>
    </div>
</nav>
```

### 7.3 Detalhe da Empresa com Submenu (templates/contabilidade/empresa/detail.html)

```html
{% extends 'base.html' %}

{% block title %}{{ empresa.razao_social }} - AgentNFe{% endblock %}

{% block content %}
<div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pb-2 mb-3 border-bottom border-secondary">
    <h1 class="h2 text-light">{{ empresa.nome_fantasia|default:empresa.razao_social }}</h1>
    <div class="btn-toolbar">
        <a href="{% url 'contabilidade:empresa_update' empresa.pk %}" class="btn btn-outline-primary me-2">
            <i class="bi bi-pencil me-1"></i> Editar
        </a>
        <a href="{% url 'contabilidade:empresa_list' %}" class="btn btn-outline-secondary">
            <i class="bi bi-arrow-left me-1"></i> Voltar
        </a>
    </div>
</div>

<!-- Submenu da Empresa -->
<ul class="nav nav-tabs mb-4">
    <li class="nav-item">
        <a class="nav-link active" data-bs-toggle="tab" href="#dados">
            <i class="bi bi-info-circle me-1"></i> Dados
        </a>
    </li>
    <li class="nav-item">
        <a class="nav-link" href="{% url 'contabilidade:usuario_empresa_list' empresa.pk %}">
            <i class="bi bi-people me-1"></i> Usuários
            <span class="badge bg-secondary">{{ total_usuarios }}</span>
        </a>
    </li>
    <li class="nav-item">
        <a class="nav-link" href="{% url 'contabilidade:certificado_list' empresa.pk %}">
            <i class="bi bi-shield-lock me-1"></i> Certificados
            <span class="badge bg-secondary">{{ total_certificados }}</span>
        </a>
    </li>
</ul>

<!-- Conteúdo dos Dados da Empresa -->
<div class="tab-content">
    <div class="tab-pane fade show active" id="dados">
        <div class="row">
            <div class="col-md-6">
                <div class="card bg-card mb-4">
                    <div class="card-header">
                        <i class="bi bi-building me-2"></i> Dados Cadastrais
                    </div>
                    <div class="card-body">
                        <dl class="row mb-0">
                            <dt class="col-sm-4">CNPJ</dt>
                            <dd class="col-sm-8">{{ empresa.cpf_cnpj }}</dd>

                            <dt class="col-sm-4">Razão Social</dt>
                            <dd class="col-sm-8">{{ empresa.razao_social }}</dd>

                            <dt class="col-sm-4">Nome Fantasia</dt>
                            <dd class="col-sm-8">{{ empresa.nome_fantasia|default:"-" }}</dd>

                            <dt class="col-sm-4">Insc. Municipal</dt>
                            <dd class="col-sm-8">{{ empresa.inscricao_municipal|default:"-" }}</dd>

                            <dt class="col-sm-4">Insc. Estadual</dt>
                            <dd class="col-sm-8">{{ empresa.inscricao_estadual|default:"-" }}</dd>
                        </dl>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card bg-card mb-4">
                    <div class="card-header">
                        <i class="bi bi-receipt me-2"></i> Regime Tributário
                    </div>
                    <div class="card-body">
                        <dl class="row mb-0">
                            <dt class="col-sm-5">Simples Nacional</dt>
                            <dd class="col-sm-7">
                                {% if empresa.simples_nacional %}
                                    <span class="badge bg-success">Sim</span>
                                {% else %}
                                    <span class="badge bg-secondary">Não</span>
                                {% endif %}
                            </dd>

                            <dt class="col-sm-5">Regime</dt>
                            <dd class="col-sm-7">{{ empresa.get_regime_tributario_display }}</dd>

                            <dt class="col-sm-5">Regime Especial</dt>
                            <dd class="col-sm-7">{{ empresa.get_regime_tributario_especial_display }}</dd>

                            <dt class="col-sm-5">NFSe Ativo</dt>
                            <dd class="col-sm-7">
                                {% if empresa.nfse_ativo %}
                                    <span class="badge bg-success">Sim</span>
                                {% else %}
                                    <span class="badge bg-secondary">Não</span>
                                {% endif %}
                            </dd>
                        </dl>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### 7.4 Página Home (templates/home.html)

```html
{% extends 'base.html' %}
{% load static %}

{% block public_content %}
<div class="min-vh-100 d-flex align-items-center justify-content-center">
    <div class="text-center">
        <!-- Logo -->
        <div class="mb-4">
            <img src="{% static 'img/logo.svg' %}" alt="AgentNFe" height="80">
        </div>

        <h1 class="display-5 text-white mb-2">AgentNFe</h1>
        <p class="text-secondary mb-4">Sistema de Emissão de Notas Fiscais via WhatsApp</p>
        <p class="text-muted small mb-5">Versão 1.0.0</p>

        <div class="d-grid gap-3 d-sm-flex justify-content-sm-center">
            <a href="{% url 'account:login' %}" class="btn btn-primary btn-lg px-4">
                <i class="bi bi-box-arrow-in-right me-2"></i>Entrar
            </a>
            <a href="{% url 'account:register' %}" class="btn btn-outline-light btn-lg px-4">
                <i class="bi bi-person-plus me-2"></i>Cadastrar-se
            </a>
        </div>
    </div>
</div>
{% endblock %}
```

---

## 8. Serviço Tecnospeed

### 8.1 Cliente API Tecnospeed

```python
# apps/contabilidade/services/tecnospeed.py

import httpx
from django.conf import settings


class TecnospeedClient:
    '''Cliente para integração com API Tecnospeed PlugNotas.'''

    BASE_URL = 'https://api.sandbox.plugnotas.com.br'

    def __init__(self):
        self.api_key = getattr(settings, 'TECNOSPEED_API_KEY', '')

    def _headers(self):
        return {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
        }

    def cadastrar_certificado(self, arquivo_base64: str, senha: str) -> dict:
        '''
        Cadastra certificado digital na Tecnospeed.

        Args:
            arquivo_base64: Conteúdo do arquivo .pfx em base64
            senha: Senha do certificado

        Returns:
            dict com 'id' do certificado cadastrado
        '''
        url = f'{self.BASE_URL}/certificado'
        payload = {
            'arquivo': arquivo_base64,
            'senha': senha,
        }

        with httpx.Client() as client:
            response = client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            return response.json()

    def consultar_certificado(self, certificado_id: str) -> dict:
        '''Consulta informações de um certificado.'''
        url = f'{self.BASE_URL}/certificado/{certificado_id}'

        with httpx.Client() as client:
            response = client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()

    def deletar_certificado(self, certificado_id: str) -> bool:
        '''Remove certificado da Tecnospeed.'''
        url = f'{self.BASE_URL}/certificado/{certificado_id}'

        with httpx.Client() as client:
            response = client.delete(url, headers=self._headers())
            return response.status_code == 200

    def cadastrar_empresa(self, dados: dict) -> dict:
        '''
        Cadastra empresa na Tecnospeed.

        Args:
            dados: Dicionário com dados da empresa no formato Tecnospeed

        Returns:
            dict com 'id' da empresa cadastrada
        '''
        url = f'{self.BASE_URL}/empresa'

        with httpx.Client() as client:
            response = client.post(url, json=dados, headers=self._headers())
            response.raise_for_status()
            return response.json()

    def atualizar_empresa(self, empresa_id: str, dados: dict) -> dict:
        '''Atualiza dados de uma empresa.'''
        url = f'{self.BASE_URL}/empresa/{empresa_id}'

        with httpx.Client() as client:
            response = client.patch(url, json=dados, headers=self._headers())
            response.raise_for_status()
            return response.json()
```

---

## 9. Formulários

### 9.1 Formulário de Login

```python
# apps/account/forms.py

from django import forms
from django.contrib.auth import authenticate


class LoginForm(forms.Form):
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'seu@email.com',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '********',
        })
    )

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user = authenticate(email=email, password=password)
            if self.user is None:
                raise forms.ValidationError('E-mail ou senha inválidos.')
            if not self.user.is_active:
                raise forms.ValidationError('Esta conta está desativada.')

        return self.cleaned_data
```

### 9.2 Formulário de Cadastro (Registro)

```python
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password_confirm = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    # Dados da contabilidade (para primeiro usuário)
    contabilidade_cnpj = forms.CharField(
        label='CNPJ da Contabilidade',
        max_length=18,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    contabilidade_razao_social = forms.CharField(
        label='Razão Social',
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('As senhas não conferem.')

        return self.cleaned_data
```

### 9.3 Formulário Empresa

```python
# apps/contabilidade/forms.py

from django import forms
from .models import Empresa, UsuarioEmpresa, Certificado


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        exclude = ['contabilidade', 'tecnospeed_id', 'created_at', 'updated_at']
        widgets = {
            'cpf_cnpj': forms.TextInput(attrs={'class': 'form-control'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'inscricao_municipal': forms.TextInput(attrs={'class': 'form-control'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control'}),
            'simples_nacional': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'regime_tributario': forms.Select(attrs={'class': 'form-select'}),
            'incentivo_fiscal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incentivador_cultural': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'regime_tributario_especial': forms.Select(attrs={'class': 'form-select'}),
            'cep': forms.TextInput(attrs={'class': 'form-control'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao_cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
            'telefone_ddd': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
            'telefone_numero': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'nfse_ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'nfse_producao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UsuarioEmpresaForm(forms.ModelForm):
    class Meta:
        model = UsuarioEmpresa
        exclude = ['empresa', 'created_at', 'updated_at']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cep': forms.TextInput(attrs={'class': 'form-control'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CertificadoForm(forms.ModelForm):
    class Meta:
        model = Certificado
        fields = ['arquivo', 'senha']
        widgets = {
            'arquivo': forms.FileInput(attrs={'class': 'form-control'}),
            'senha': forms.PasswordInput(attrs={'class': 'form-control'}),
        }
```

---

## 10. Migrações Necessárias

### 10.1 Ordem de Execução

1. Criar app `account`
2. Criar app `contabilidade`
3. Configurar `AUTH_USER_MODEL` em settings.py
4. Executar `makemigrations account` (primeiro, pois User é dependência)
5. Executar `makemigrations contabilidade`
6. Executar `migrate`

### 10.2 Configuração settings.py

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps do projeto
    'apps.account',
    'apps.contabilidade',
    'apps.core',
]

AUTH_USER_MODEL = 'account.User'
```

---

## 11. Fluxo de Registro e Onboarding

### 11.1 Fluxo de Primeiro Acesso

```
1. Usuário acessa /account/register/
2. Preenche dados pessoais (email, nome, telefone)
3. Preenche dados da contabilidade (CNPJ, razão social)
4. Sistema cria:
   - Contabilidade (tenant)
   - User com role='admin' vinculado à contabilidade
5. Redireciona para login
6. Após login, vai para dashboard
```

### 11.2 Fluxo de Adição de Novo Usuário

```
1. Admin acessa /app/usuarios/novo/
2. Preenche dados do novo usuário
3. Sistema cria User vinculado à mesma contabilidade
4. Novo usuário recebe email com credenciais (futuro)
```

---

## 12. Checklist de Implementação

### Fase 1: Estrutura Base
- [ ] Criar app `account`
- [ ] Criar app `contabilidade`
- [ ] Configurar modelo User customizado
- [ ] Configurar backend de autenticação por email
- [ ] Executar migrações iniciais

### Fase 2: Templates e Design System
- [ ] Criar template base com design system
- [ ] Criar componentes (navbar, sidebar, cards, forms)
- [ ] Criar página home pública
- [ ] Criar logo SVG

### Fase 3: Autenticação
- [ ] Implementar view de login
- [ ] Implementar view de registro
- [ ] Implementar view de logout
- [ ] Implementar view de perfil

### Fase 4: Contabilidade - CRUD Empresas
- [ ] Implementar listagem de empresas
- [ ] Implementar cadastro de empresa
- [ ] Implementar edição de empresa
- [ ] Implementar exclusão de empresa
- [ ] Implementar detalhe da empresa (com submenu)

### Fase 5: Contabilidade - Usuários Empresa
- [ ] Implementar listagem de usuários da empresa
- [ ] Implementar cadastro de usuário empresa
- [ ] Implementar edição de usuário empresa
- [ ] Implementar exclusão de usuário empresa

### Fase 6: Certificados Digitais
- [ ] Implementar upload de certificado
- [ ] Implementar listagem de certificados
- [ ] Implementar envio para Tecnospeed
- [ ] Implementar exclusão de certificado

### Fase 7: Sessões
- [ ] Implementar listagem de sessões
- [ ] Implementar filtros por estado

### Fase 8: Notas Fiscais
- [ ] Implementar listagem de notas
- [ ] Implementar formulário de emissão manual

### Fase 9: Usuários do Sistema
- [ ] Implementar listagem de usuários (funcionários)
- [ ] Implementar cadastro de usuário
- [ ] Implementar edição de usuário
- [ ] Implementar exclusão de usuário

### Fase 10: Dashboard
- [ ] Implementar métricas de empresas
- [ ] Implementar métricas de certificados
- [ ] Integrar métricas de sessões/notas

---

## 13. Considerações Técnicas

### 13.1 Segurança
- Senhas de certificados serão armazenadas com criptografia (Fernet)
- Arquivos de certificado em diretório protegido
- Isolamento multi-tenant em todas as queries
- CSRF protection em todos os forms

### 13.2 Performance
- Índices em campos frequentemente consultados
- Paginação em listagens
- Cache de dados da contabilidade na sessão

### 13.3 Manutenibilidade
- Class-Based Views para padronização
- Mixins para comportamentos compartilhados
- Forms separados dos models
- Services para integrações externas

---

## Aprovação

**Documento atualizado com as alterações solicitadas:**

1. Menu Sidebar reorganizado:
   - Dashboard
   - Empresas (antes Clientes)
   - Sessões (lista sessões do APP Core filtradas por usuários das empresas)
   - Notas Fiscais (lista por CNPJ, emissão manual)
   - Usuários (funcionários da contabilidade)

2. Certificados como submenu dentro da área da Empresa (no detalhe)

3. Nomenclatura alterada:
   - ClientePJ → Empresa
   - UsuarioCliente → UsuarioEmpresa

4. Detalhe da Empresa com submenu:
   - Aba Dados (informações da empresa)
   - Aba Usuários (cadastrar/listar usuários da empresa)
   - Aba Certificados (cadastrar/listar/deletar certificados)

**Aguardando validação para iniciar implementação.**
