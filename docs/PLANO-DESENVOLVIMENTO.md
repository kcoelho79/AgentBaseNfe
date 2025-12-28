# PLANO DE DESENVOLVIMENTO - AgentBase NFe

## Visão Geral do Projeto

**Sistema:** AgentBase NFe - SaaS para emissão de NFSe via WhatsApp usando IA
**Stack:** Django 5.0, PostgreSQL 16, Redis 7, Celery, OpenAI API, Bootstrap 5
**Arquitetura:** Multi-tenant, Event-driven, Async processing

---

## SPRINT 1: Setup Inicial e Infraestrutura Base

**Objetivo:** Preparar ambiente de desenvolvimento e estrutura básica do projeto
**Duração estimada:** 3-5 dias

### 1.1 Configuração do Ambiente

- [ ] **1.1.1** Criar ambiente virtual Python 3.11+
  - Executar: `python -m venv venv`
  - Ativar: `source venv/bin/activate`
  - Verificar versão: `python --version`

- [ ] **1.1.2** Criar arquivo `requirements/base.txt`
  - Adicionar: `Django==5.0.0`
  - Adicionar: `psycopg2-binary==2.9.9`
  - Adicionar: `python-decouple==3.8`
  - Adicionar: `django-redis==5.4.0`
  - Adicionar: `celery[redis]==5.3.4`
  - Adicionar: `openai==1.3.0`
  - Adicionar: `requests==2.31.0`
  - Adicionar: `pillow==10.1.0`

- [ ] **1.1.3** Criar arquivo `requirements/development.txt`
  - Incluir: `-r base.txt`
  - Adicionar: `django-debug-toolbar==4.2.0`
  - Adicionar: `ipython==8.18.0`
  - Adicionar: `black==23.11.0`
  - Adicionar: `flake8==6.1.0`

- [ ] **1.1.4** Instalar dependências
  - Executar: `pip install -r requirements/development.txt`
  - Verificar instalação: `pip list`

### 1.2 Criação do Projeto Django

- [ ] **1.2.1** Criar projeto Django
  - Executar: `django-admin startproject config .`
  - Verificar estrutura criada

- [ ] **1.2.2** Criar diretório `apps/` na raiz
  - Executar: `mkdir apps`
  - Criar `apps/__init__.py`

- [ ] **1.2.3** Configurar `config/settings.py` - Estrutura Base
  - Importar: `from decouple import config`
  - Configurar: `SECRET_KEY = config('SECRET_KEY')`
  - Configurar: `DEBUG = config('DEBUG', default=False, cast=bool)`
  - Configurar: `ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')`

- [ ] **1.2.4** Configurar `config/settings.py` - Internacionalização
  - Definir: `LANGUAGE_CODE = 'pt-br'`
  - Definir: `TIME_ZONE = 'America/Sao_Paulo'`
  - Definir: `USE_I18N = True`
  - Definir: `USE_TZ = True`

- [ ] **1.2.5** Criar arquivo `.env.example`
  ```
  SECRET_KEY=your-secret-key-here
  DEBUG=True
  ALLOWED_HOSTS=localhost,127.0.0.1

  DATABASE_URL=postgresql://user:password@localhost:5432/agentbase_nfe

  REDIS_URL=redis://localhost:6379/0

  OPENAI_API_KEY=sk-...

  WAHA_API_URL=http://localhost:3000
  WAHA_API_KEY=your-api-key
  WAHA_VERIFY_TOKEN=your-verify-token

  USE_FAKE_TECNOSPEED=True
  ```

- [ ] **1.2.6** Criar arquivo `.env` (copiar de `.env.example`)
  - Gerar SECRET_KEY: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
  - Preencher valores reais

- [ ] **1.2.7** Criar `.gitignore`
  ```
  venv/
  __pycache__/
  *.pyc
  .env
  db.sqlite3
  media/
  staticfiles/
  .DS_Store
  .vscode/
  .idea/
  ```

### 1.3 Configuração do PostgreSQL

- [ ] **1.3.1** Instalar PostgreSQL 16
  - Verificar instalação: `psql --version`

- [ ] **1.3.2** Criar database
  - Conectar: `psql -U postgres`
  - Executar: `CREATE DATABASE agentbase_nfe;`
  - Executar: `\c agentbase_nfe`

- [ ] **1.3.3** Instalar extensões PostgreSQL
  - Executar: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`
  - Executar: `CREATE EXTENSION IF NOT EXISTS "pgvector";`
  - Verificar: `\dx` (listar extensões)

- [ ] **1.3.4** Configurar database no `settings.py`
  ```python
  import dj_database_url

  DATABASES = {
      'default': dj_database_url.config(
          default=config('DATABASE_URL'),
          conn_max_age=600,
          conn_health_checks=True,
      )
  }
  ```

- [ ] **1.3.5** Instalar `dj-database-url`
  - Adicionar ao `requirements/base.txt`: `dj-database-url==2.1.0`
  - Instalar: `pip install dj-database-url`

### 1.4 Configuração do Redis

- [ ] **1.4.1** Instalar Redis 7
  - Verificar instalação: `redis-cli --version`

- [ ] **1.4.2** Iniciar Redis server
  - Executar: `redis-server`
  - Testar: `redis-cli ping` (deve retornar PONG)

- [ ] **1.4.3** Configurar Redis no `settings.py`
  ```python
  CACHES = {
      'default': {
          'BACKEND': 'django_redis.cache.RedisCache',
          'LOCATION': config('REDIS_URL', default='redis://localhost:6379/0'),
          'OPTIONS': {
              'CLIENT_CLASS': 'django_redis.client.DefaultClient',
              'SOCKET_CONNECT_TIMEOUT': 5,
              'SOCKET_TIMEOUT': 5,
              'CONNECTION_POOL_KWARGS': {
                  'max_connections': 50,
              }
          },
          'KEY_PREFIX': 'agentbase',
          'TIMEOUT': 300,
      }
  }
  ```

- [ ] **1.4.4** Configurar session backend
  - Adicionar: `SESSION_ENGINE = 'django.contrib.sessions.backends.cache'`
  - Adicionar: `SESSION_CACHE_ALIAS = 'default'`

### 1.5 Configuração do Celery

- [ ] **1.5.1** Criar arquivo `config/celery.py`
  ```python
  import os
  from celery import Celery

  os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

  app = Celery('agentbase_nfe')
  app.config_from_object('django.conf:settings', namespace='CELERY')
  app.autodiscover_tasks()
  ```

- [ ] **1.5.2** Atualizar `config/__init__.py`
  ```python
  from .celery import app as celery_app

  __all__ = ('celery_app',)
  ```

- [ ] **1.5.3** Configurar Celery no `settings.py`
  ```python
  CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
  CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
  CELERY_ACCEPT_CONTENT = ['json']
  CELERY_TASK_SERIALIZER = 'json'
  CELERY_RESULT_SERIALIZER = 'json'
  CELERY_TIMEZONE = TIME_ZONE
  ```

### 1.6 Estrutura de Diretórios

- [ ] **1.6.1** Criar estrutura de templates
  - Criar: `templates/`
  - Criar: `templates/base.html`
  - Criar: `templates/components/`
  - Criar: `templates/home.html`

- [ ] **1.6.2** Criar estrutura de static files
  - Criar: `static/`
  - Criar: `static/css/custom.css`
  - Criar: `static/js/main.js`
  - Criar: `static/images/`

- [ ] **1.6.3** Criar diretório media
  - Criar: `media/`
  - Criar: `media/certificados/`
  - Criar: `media/pdfs/`

- [ ] **1.6.4** Configurar templates e static no `settings.py`
  ```python
  TEMPLATES = [
      {
          'BACKEND': 'django.template.backends.django.DjangoTemplates',
          'DIRS': [BASE_DIR / 'templates'],
          'APP_DIRS': True,
          'OPTIONS': {
              'context_processors': [
                  'django.template.context_processors.debug',
                  'django.template.context_processors.request',
                  'django.contrib.auth.context_processors.auth',
                  'django.contrib.messages.context_processors.messages',
              ],
          },
      },
  ]

  STATIC_URL = '/static/'
  STATICFILES_DIRS = [BASE_DIR / 'static']
  STATIC_ROOT = BASE_DIR / 'staticfiles'

  MEDIA_URL = '/media/'
  MEDIA_ROOT = BASE_DIR / 'media'
  ```

### 1.7 Configurações de Logging

- [ ] **1.7.1** Criar diretório `logs/`
  - Executar: `mkdir logs`
  - Criar: `logs/.gitkeep`
  - Adicionar ao `.gitignore`: `logs/*.log`

- [ ] **1.7.2** Configurar logging no `settings.py`
  ```python
  LOGGING = {
      'version': 1,
      'disable_existing_loggers': False,
      'formatters': {
          'verbose': {
              'format': '{levelname} {asctime} {module} {message}',
              'style': '{',
          },
      },
      'handlers': {
          'console': {
              'class': 'logging.StreamHandler',
              'formatter': 'verbose',
          },
          'file': {
              'class': 'logging.FileHandler',
              'filename': 'logs/debug.log',
              'formatter': 'verbose',
          },
      },
      'root': {
          'handlers': ['console', 'file'],
          'level': 'INFO',
      },
      'loggers': {
          'django': {
              'handlers': ['console', 'file'],
              'level': 'INFO',
              'propagate': False,
          },
          'apps': {
              'handlers': ['console', 'file'],
              'level': 'DEBUG',
              'propagate': False,
          },
      },
  }
  ```

### 1.8 Testes Iniciais

- [ ] **1.8.1** Testar migrations iniciais
  - Executar: `python manage.py makemigrations`
  - Executar: `python manage.py migrate`

- [ ] **1.8.2** Criar superuser
  - Executar: `python manage.py createsuperuser`
  - Email: admin@test.com
  - Password: (definir senha forte)

- [ ] **1.8.3** Testar servidor Django
  - Executar: `python manage.py runserver`
  - Acessar: http://localhost:8000
  - Acessar: http://localhost:8000/admin

- [ ] **1.8.4** Testar Celery worker
  - Terminal 1: `celery -A config worker -l info`
  - Verificar: "celery@hostname ready"

- [ ] **1.8.5** Criar arquivo `README.md` do projeto
  - Documentar setup básico
  - Documentar comandos principais
  - Documentar estrutura do projeto

---

## SPRINT 2: App Account (Autenticação e Usuários)

**Objetivo:** Implementar sistema de autenticação customizado com email
**Duração estimada:** 2-3 dias

### 2.1 Criação do App Account

- [ ] **2.1.1** Criar app account
  - Executar: `python manage.py startapp account apps/account`

- [ ] **2.1.2** Registrar app no `settings.py`
  ```python
  INSTALLED_APPS = [
      'django.contrib.admin',
      'django.contrib.auth',
      'django.contrib.contenttypes',
      'django.contrib.sessions',
      'django.contrib.messages',
      'django.contrib.staticfiles',
      'apps.account',
  ]
  ```

- [ ] **2.1.3** Criar estrutura de diretórios do app
  - Criar: `apps/account/templates/account/`
  - Criar: `apps/account/forms.py`
  - Criar: `apps/account/urls.py`

### 2.2 Custom User Model

- [ ] **2.2.1** Criar model `User` customizado em `apps/account/models.py`
  ```python
  from django.contrib.auth.models import AbstractUser
  from django.db import models
  import uuid

  class User(AbstractUser):
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
      email = models.EmailField('Email', unique=True)
      contabilidade = models.ForeignKey(
          'contabilidade.Contabilidade',
          on_delete=models.PROTECT,
          null=True,
          blank=True,
          related_name='usuarios'
      )

      USERNAME_FIELD = 'email'
      REQUIRED_FIELDS = ['username']

      class Meta:
          db_table = 'user'
          verbose_name = 'Usuário'
          verbose_name_plural = 'Usuários'

      def __str__(self):
          return self.email
  ```

- [ ] **2.2.2** Configurar `AUTH_USER_MODEL` no `settings.py`
  - Adicionar: `AUTH_USER_MODEL = 'account.User'`

- [ ] **2.2.3** Criar migrations
  - Executar: `python manage.py makemigrations account`
  - Verificar arquivo de migration criado

### 2.3 Forms de Autenticação

- [ ] **2.3.1** Criar `LoginForm` em `apps/account/forms.py`
  ```python
  from django import forms
  from django.contrib.auth import authenticate

  class LoginForm(forms.Form):
      email = forms.EmailField(
          label='Email',
          widget=forms.EmailInput(attrs={
              'class': 'form-control',
              'placeholder': 'seu@email.com'
          })
      )
      password = forms.CharField(
          label='Senha',
          widget=forms.PasswordInput(attrs={
              'class': 'form-control',
              'placeholder': 'Sua senha'
          })
      )

      def clean(self):
          email = self.cleaned_data.get('email')
          password = self.cleaned_data.get('password')

          if email and password:
              self.user = authenticate(username=email, password=password)
              if not self.user:
                  raise forms.ValidationError('Email ou senha incorretos')

          return self.cleaned_data
  ```

- [ ] **2.3.2** Criar `ProfileForm` em `apps/account/forms.py`
  ```python
  from django import forms
  from .models import User

  class ProfileForm(forms.ModelForm):
      class Meta:
          model = User
          fields = ['first_name', 'last_name', 'email']
          widgets = {
              'first_name': forms.TextInput(attrs={'class': 'form-control'}),
              'last_name': forms.TextInput(attrs={'class': 'form-control'}),
              'email': forms.EmailInput(attrs={'class': 'form-control'}),
          }
  ```

### 2.4 Views de Autenticação

- [ ] **2.4.1** Criar `LoginView` em `apps/account/views.py`
  ```python
  from django.views.generic import FormView
  from django.contrib.auth import login
  from django.urls import reverse_lazy
  from .forms import LoginForm

  class LoginView(FormView):
      template_name = 'account/login.html'
      form_class = LoginForm
      success_url = reverse_lazy('contabilidade:dashboard')

      def form_valid(self, form):
          login(self.request, form.user)
          return super().form_valid(form)
  ```

- [ ] **2.4.2** Criar `LogoutView` em `apps/account/views.py`
  ```python
  from django.contrib.auth.views import LogoutView as DjangoLogoutView

  class LogoutView(DjangoLogoutView):
      next_page = 'account:login'
  ```

- [ ] **2.4.3** Criar `ProfileView` em `apps/account/views.py`
  ```python
  from django.views.generic import UpdateView
  from django.contrib.auth.mixins import LoginRequiredMixin
  from .models import User
  from .forms import ProfileForm

  class ProfileView(LoginRequiredMixin, UpdateView):
      model = User
      form_class = ProfileForm
      template_name = 'account/profile.html'
      success_url = reverse_lazy('account:profile')

      def get_object(self):
          return self.request.user
  ```

### 2.5 URLs do Account

- [ ] **2.5.1** Criar `apps/account/urls.py`
  ```python
  from django.urls import path
  from . import views

  app_name = 'account'

  urlpatterns = [
      path('login/', views.LoginView.as_view(), name='login'),
      path('logout/', views.LogoutView.as_view(), name='logout'),
      path('profile/', views.ProfileView.as_view(), name='profile'),
  ]
  ```

- [ ] **2.5.2** Incluir URLs no `config/urls.py`
  ```python
  from django.contrib import admin
  from django.urls import path, include
  from django.conf import settings
  from django.conf.urls.static import static

  urlpatterns = [
      path('admin/', admin.site.urls),
      path('account/', include('apps.account.urls')),
  ]

  if settings.DEBUG:
      urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
  ```

### 2.6 Templates de Autenticação

- [ ] **2.6.1** Criar `templates/account/login.html`
  ```html
  {% extends 'base.html' %}

  {% block title %}Login{% endblock %}

  {% block content %}
  <div class="container">
      <div class="row justify-content-center mt-5">
          <div class="col-md-4">
              <div class="card shadow-sm">
                  <div class="card-body">
                      <h3 class="text-center mb-4">Login</h3>
                      <form method="post">
                          {% csrf_token %}
                          {{ form.as_p }}
                          <button type="submit" class="btn btn-gradient-primary w-100">
                              Entrar
                          </button>
                      </form>
                  </div>
              </div>
          </div>
      </div>
  </div>
  {% endblock %}
  ```

- [ ] **2.6.2** Criar `templates/account/profile.html`
  ```html
  {% extends 'base.html' %}

  {% block title %}Meu Perfil{% endblock %}

  {% block content %}
  <div class="container mt-4">
      <h2>Meu Perfil</h2>
      <div class="card shadow-sm mt-3">
          <div class="card-body">
              <form method="post">
                  {% csrf_token %}
                  {{ form.as_p }}
                  <button type="submit" class="btn btn-gradient-primary">
                      Salvar Alterações
                  </button>
              </form>
          </div>
      </div>
  </div>
  {% endblock %}
  ```

### 2.7 Admin do Account

- [ ] **2.7.1** Customizar admin em `apps/account/admin.py`
  ```python
  from django.contrib import admin
  from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
  from .models import User

  @admin.register(User)
  class UserAdmin(DjangoUserAdmin):
      list_display = ['email', 'first_name', 'last_name', 'contabilidade', 'is_staff']
      list_filter = ['is_staff', 'is_superuser', 'is_active']
      search_fields = ['email', 'first_name', 'last_name']
      ordering = ['email']

      fieldsets = (
          (None, {'fields': ('email', 'password')}),
          ('Informações Pessoais', {'fields': ('first_name', 'last_name')}),
          ('Tenant', {'fields': ('contabilidade',)}),
          ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
          ('Datas', {'fields': ('last_login', 'date_joined')}),
      )

      add_fieldsets = (
          (None, {
              'classes': ('wide',),
              'fields': ('email', 'password1', 'password2'),
          }),
      )
  ```

### 2.8 Testes do Sprint 2

- [ ] **2.8.1** Aplicar migrations
  - Executar: `python manage.py migrate`

- [ ] **2.8.2** Criar usuário de teste
  - Executar: `python manage.py shell`
  - Criar user com email

- [ ] **2.8.3** Testar login
  - Acessar: http://localhost:8000/account/login/
  - Fazer login com usuário criado

- [ ] **2.8.4** Testar profile
  - Acessar: http://localhost:8000/account/profile/
  - Editar dados

- [ ] **2.8.5** Testar logout
  - Clicar em logout
  - Verificar redirecionamento

---

## SPRINT 3: App Contabilidade (Multi-tenant)

**Objetivo:** Implementar models e funcionalidades de multi-tenant
**Duração estimada:** 4-5 dias

### 3.1 Criação do App Contabilidade

- [ ] **3.1.1** Criar app contabilidade
  - Executar: `python manage.py startapp contabilidade apps/contabilidade`

- [ ] **3.1.2** Registrar app no `settings.py`
  ```python
  INSTALLED_APPS = [
      # ...
      'apps.account',
      'apps.contabilidade',
  ]
  ```

- [ ] **3.1.3** Criar estrutura de diretórios
  - Criar: `apps/contabilidade/templates/contabilidade/`
  - Criar: `apps/contabilidade/middleware.py`
  - Criar: `apps/contabilidade/urls.py`

### 3.2 Models do Contabilidade

- [ ] **3.2.1** Criar model `Contabilidade` em `apps/contabilidade/models.py`
  ```python
  import uuid
  from django.db import models

  class PlanoChoices(models.TextChoices):
      BASICO = 'basico', 'Básico'
      PROFISSIONAL = 'profissional', 'Profissional'
      ENTERPRISE = 'enterprise', 'Enterprise'

  class StatusChoices(models.TextChoices):
      ATIVO = 'ativo', 'Ativo'
      SUSPENSO = 'suspenso', 'Suspenso'
      CANCELADO = 'cancelado', 'Cancelado'

  class Contabilidade(models.Model):
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
      cnpj = models.CharField('CNPJ', max_length=14, unique=True)
      razao_social = models.CharField('Razão Social', max_length=255)
      nome_fantasia = models.CharField('Nome Fantasia', max_length=255)
      email = models.EmailField('Email')
      telefone = models.CharField('Telefone', max_length=20, blank=True)

      plano = models.CharField(
          'Plano',
          max_length=20,
          choices=PlanoChoices.choices,
          default=PlanoChoices.BASICO
      )
      limite_clientes = models.IntegerField('Limite de Clientes', null=True, blank=True)
      limite_notas_mes = models.IntegerField('Limite de Notas/Mês', null=True, blank=True)

      status = models.CharField(
          'Status',
          max_length=20,
          choices=StatusChoices.choices,
          default=StatusChoices.ATIVO
      )
      is_active = models.BooleanField('Ativo', default=True)

      created_at = models.DateTimeField('Criado em', auto_now_add=True)
      updated_at = models.DateTimeField('Atualizado em', auto_now=True)

      class Meta:
          db_table = 'contabilidade'
          verbose_name = 'Contabilidade'
          verbose_name_plural = 'Contabilidades'
          ordering = ['-created_at']

      def __str__(self):
          return self.nome_fantasia

      def pode_emitir_nota(self):
          """Verifica se pode emitir notas."""
          return self.is_active and self.status == StatusChoices.ATIVO
  ```

- [ ] **3.2.2** Criar model `EmpresaClienteContabilidade` em `apps/contabilidade/models.py`
  ```python
  class EmpresaClienteContabilidade(models.Model):
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

      razao_social = models.CharField('Razão Social', max_length=255)
      nome_fantasia = models.CharField('Nome Fantasia', max_length=255, blank=True)
      cnpj = models.CharField('CNPJ', max_length=14)
      inscricao_estadual = models.CharField('Inscrição Estadual', max_length=20, blank=True)
      inscricao_municipal = models.CharField('Inscrição Municipal', max_length=20, blank=True)

      endereco_logradouro = models.CharField('Logradouro', max_length=255, blank=True)
      endereco_numero = models.CharField('Número', max_length=20, blank=True)
      endereco_complemento = models.CharField('Complemento', max_length=100, blank=True)
      endereco_bairro = models.CharField('Bairro', max_length=100, blank=True)
      endereco_cidade = models.CharField('Cidade', max_length=100, blank=True)
      endereco_uf = models.CharField('UF', max_length=2, blank=True)
      endereco_cep = models.CharField('CEP', max_length=8, blank=True)

      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)

      class Meta:
          db_table = 'empresa_cliente_contabilidade'
          verbose_name = 'Empresa do Cliente'
          verbose_name_plural = 'Empresas dos Clientes'

      def __str__(self):
          return self.razao_social
  ```

- [ ] **3.2.3** Criar model `ClienteContabilidade` em `apps/contabilidade/models.py`
  ```python
  from django.core.validators import RegexValidator

  class ClienteContabilidade(models.Model):
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

      contabilidade = models.ForeignKey(
          Contabilidade,
          on_delete=models.PROTECT,
          related_name='clientes',
          verbose_name='Contabilidade'
      )

      empresa = models.OneToOneField(
          EmpresaClienteContabilidade,
          on_delete=models.CASCADE,
          related_name='cliente',
          verbose_name='Empresa'
      )

      nome = models.CharField('Nome', max_length=255)
      telefone = models.CharField(
          'Telefone',
          max_length=20,
          unique=True,
          validators=[
              RegexValidator(
                  regex=r'^\+\d{12,15}$',
                  message='Formato E.164: +5511999999999'
              )
          ]
      )
      email = models.EmailField('Email', blank=True)

      codigo_servico_municipal_padrao = models.CharField(
          'Código Serviço Municipal Padrão',
          max_length=10,
          blank=True
      )
      aliquota_iss = models.DecimalField(
          'Alíquota ISS',
          max_digits=5,
          decimal_places=4,
          default=0.02,
          help_text='Alíquota do ISS (ex: 0.02 para 2%)'
      )

      auto_aprovar_notas = models.BooleanField(
          'Auto-aprovar Notas',
          default=False,
          help_text='Se ativado, notas são emitidas automaticamente'
      )

      total_notas_emitidas = models.IntegerField('Total de Notas Emitidas', default=0)
      total_valor_notas = models.DecimalField(
          'Total Valor de Notas',
          max_digits=15,
          decimal_places=2,
          default=0
      )

      is_active = models.BooleanField('Ativo', default=True)
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)

      class Meta:
          db_table = 'cliente_contabilidade'
          verbose_name = 'Cliente'
          verbose_name_plural = 'Clientes'
          ordering = ['-created_at']
          indexes = [
              models.Index(fields=['contabilidade', 'is_active']),
              models.Index(fields=['telefone']),
          ]

      def __str__(self):
          return self.nome

      def incrementar_metricas(self, valor):
          """Incrementa métricas após emissão de nota."""
          self.total_notas_emitidas += 1
          self.total_valor_notas += valor
          self.save(update_fields=['total_notas_emitidas', 'total_valor_notas'])
  ```

### 3.3 Middleware Multi-tenant

- [ ] **3.3.1** Criar `TenantMiddleware` em `apps/contabilidade/middleware.py`
  ```python
  class TenantMiddleware:
      """
      Middleware que anexa o tenant (contabilidade) ao request.
      """
      def __init__(self, get_response):
          self.get_response = get_response

      def __call__(self, request):
          if request.user.is_authenticated and hasattr(request.user, 'contabilidade'):
              request.tenant = request.user.contabilidade
          else:
              request.tenant = None

          response = self.get_response(request)
          return response
  ```

- [ ] **3.3.2** Registrar middleware no `settings.py`
  ```python
  MIDDLEWARE = [
      'django.middleware.security.SecurityMiddleware',
      'django.contrib.sessions.middleware.SessionMiddleware',
      'django.middleware.common.CommonMiddleware',
      'django.middleware.csrf.CsrfViewMiddleware',
      'django.contrib.auth.middleware.AuthenticationMiddleware',
      'django.contrib.messages.middleware.MessageMiddleware',
      'django.middleware.clickjacking.XFrameOptionsMiddleware',
      'apps.contabilidade.middleware.TenantMiddleware',
  ]
  ```

### 3.4 Views do Contabilidade

- [ ] **3.4.1** Criar `DashboardView` em `apps/contabilidade/views.py`
  ```python
  from django.views.generic import TemplateView
  from django.contrib.auth.mixins import LoginRequiredMixin
  from .models import ClienteContabilidade
  from apps.nfe.models import NotaFiscal

  class DashboardView(LoginRequiredMixin, TemplateView):
      template_name = 'contabilidade/dashboard.html'

      def get_context_data(self, **kwargs):
          context = super().get_context_data(**kwargs)

          if self.request.tenant:
              context['total_clientes'] = ClienteContabilidade.objects.filter(
                  contabilidade=self.request.tenant,
                  is_active=True
              ).count()

              context['total_notas'] = NotaFiscal.objects.filter(
                  contabilidade=self.request.tenant
              ).count()

              context['notas_mes'] = NotaFiscal.objects.filter(
                  contabilidade=self.request.tenant,
                  created_at__month=timezone.now().month
              ).count()

          return context
  ```

- [ ] **3.4.2** Criar `ClienteListView` em `apps/contabilidade/views.py`
  ```python
  from django.views.generic import ListView
  from .models import ClienteContabilidade

  class ClienteListView(LoginRequiredMixin, ListView):
      model = ClienteContabilidade
      template_name = 'contabilidade/cliente_list.html'
      context_object_name = 'clientes'
      paginate_by = 50

      def get_queryset(self):
          queryset = ClienteContabilidade.objects.filter(
              contabilidade=self.request.tenant
          ).select_related('empresa', 'contabilidade')

          search = self.request.GET.get('search')
          if search:
              queryset = queryset.filter(
                  models.Q(nome__icontains=search) |
                  models.Q(telefone__icontains=search) |
                  models.Q(email__icontains=search)
              )

          return queryset.order_by('-created_at')
  ```

- [ ] **3.4.3** Criar `ClienteCreateView` em `apps/contabilidade/views.py`
  ```python
  from django.views.generic import CreateView
  from django.urls import reverse_lazy
  from .models import ClienteContabilidade, EmpresaClienteContabilidade
  from .forms import ClienteForm, EmpresaForm

  class ClienteCreateView(LoginRequiredMixin, CreateView):
      model = ClienteContabilidade
      form_class = ClienteForm
      template_name = 'contabilidade/cliente_form.html'
      success_url = reverse_lazy('contabilidade:cliente-list')

      def get_context_data(self, **kwargs):
          context = super().get_context_data(**kwargs)
          if self.request.POST:
              context['empresa_form'] = EmpresaForm(self.request.POST)
          else:
              context['empresa_form'] = EmpresaForm()
          return context

      def form_valid(self, form):
          context = self.get_context_data()
          empresa_form = context['empresa_form']

          if empresa_form.is_valid():
              self.object = form.save(commit=False)
              self.object.contabilidade = self.request.tenant
              self.object.empresa = empresa_form.save()
              self.object.save()
              return super().form_valid(form)
          else:
              return self.form_invalid(form)
  ```

- [ ] **3.4.4** Criar `ClienteUpdateView` e `ClienteDeleteView`

### 3.5 Forms do Contabilidade

- [ ] **3.5.1** Criar `ClienteForm` em `apps/contabilidade/forms.py`
  ```python
  from django import forms
  from .models import ClienteContabilidade, EmpresaClienteContabilidade

  class ClienteForm(forms.ModelForm):
      class Meta:
          model = ClienteContabilidade
          fields = [
              'nome', 'telefone', 'email',
              'codigo_servico_municipal_padrao',
              'aliquota_iss', 'auto_aprovar_notas'
          ]
          widgets = {
              'nome': forms.TextInput(attrs={'class': 'form-control'}),
              'telefone': forms.TextInput(attrs={
                  'class': 'form-control',
                  'placeholder': '+5511999999999'
              }),
              'email': forms.EmailInput(attrs={'class': 'form-control'}),
              'codigo_servico_municipal_padrao': forms.TextInput(attrs={'class': 'form-control'}),
              'aliquota_iss': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
              'auto_aprovar_notas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
          }
  ```

- [ ] **3.5.2** Criar `EmpresaForm` em `apps/contabilidade/forms.py`
  ```python
  class EmpresaForm(forms.ModelForm):
      class Meta:
          model = EmpresaClienteContabilidade
          fields = [
              'razao_social', 'nome_fantasia', 'cnpj',
              'inscricao_estadual', 'inscricao_municipal',
              'endereco_logradouro', 'endereco_numero',
              'endereco_complemento', 'endereco_bairro',
              'endereco_cidade', 'endereco_uf', 'endereco_cep'
          ]
          # widgets com form-control...
  ```

### 3.6 URLs do Contabilidade

- [ ] **3.6.1** Criar `apps/contabilidade/urls.py`
  ```python
  from django.urls import path
  from . import views

  app_name = 'contabilidade'

  urlpatterns = [
      path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
      path('clientes/', views.ClienteListView.as_view(), name='cliente-list'),
      path('clientes/novo/', views.ClienteCreateView.as_view(), name='cliente-create'),
      path('clientes/<uuid:pk>/', views.ClienteDetailView.as_view(), name='cliente-detail'),
      path('clientes/<uuid:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente-update'),
      path('clientes/<uuid:pk>/deletar/', views.ClienteDeleteView.as_view(), name='cliente-delete'),
  ]
  ```

- [ ] **3.6.2** Incluir no `config/urls.py`
  ```python
  urlpatterns = [
      # ...
      path('contabilidade/', include('apps.contabilidade.urls')),
  ]
  ```

### 3.7 Templates do Contabilidade

- [ ] **3.7.1** Criar `templates/contabilidade/dashboard.html`
- [ ] **3.7.2** Criar `templates/contabilidade/cliente_list.html`
- [ ] **3.7.3** Criar `templates/contabilidade/cliente_form.html`
- [ ] **3.7.4** Criar `templates/contabilidade/cliente_detail.html`

### 3.8 Admin do Contabilidade

- [ ] **3.8.1** Registrar models no `apps/contabilidade/admin.py`
  ```python
  from django.contrib import admin
  from .models import Contabilidade, ClienteContabilidade, EmpresaClienteContabilidade

  @admin.register(Contabilidade)
  class ContabilidadeAdmin(admin.ModelAdmin):
      list_display = ['nome_fantasia', 'cnpj', 'plano', 'status', 'is_active']
      list_filter = ['plano', 'status', 'is_active']
      search_fields = ['nome_fantasia', 'razao_social', 'cnpj']

  # Registrar outros models...
  ```

### 3.9 Migrations e Testes

- [ ] **3.9.1** Criar migrations
  - Executar: `python manage.py makemigrations contabilidade`

- [ ] **3.9.2** Aplicar migrations
  - Executar: `python manage.py migrate`

- [ ] **3.9.3** Criar contabilidade de teste no admin

- [ ] **3.9.4** Associar user ao tenant

- [ ] **3.9.5** Testar CRUD de clientes

---

## SPRINT 4: App Core - Parte 1 (Models e Webhook)

**Objetivo:** Criar estrutura básica do Core e webhook WhatsApp
**Duração estimada:** 3-4 dias

### 4.1 Criação do App Core

- [ ] **4.1.1** Criar app core
  - Executar: `python manage.py startapp core apps/core`

- [ ] **4.1.2** Registrar no `settings.py`
  ```python
  INSTALLED_APPS = [
      # ...
      'apps.core',
  ]
  ```

- [ ] **4.1.3** Criar estrutura de diretórios
  - Criar: `apps/core/services/`
  - Criar: `apps/core/services/__init__.py`
  - Criar: `apps/core/integrations/`
  - Criar: `apps/core/integrations/__init__.py`
  - Criar: `apps/core/views/`
  - Criar: `apps/core/views/__init__.py`
  - Criar: `apps/core/tasks.py`

### 4.2 Models do Core

- [ ] **4.2.1** Criar choices `EstadoMensagemChoices` em `apps/core/models.py`
  ```python
  class EstadoMensagemChoices(models.TextChoices):
      COLETA = 'coleta', 'Coleta'
      DADOS_INCOMPLETOS = 'dados_incompletos', 'Dados Incompletos'
      DADOS_COMPLETOS = 'dados_completos', 'Dados Completos'
      VALIDADO = 'validado', 'Validado'
      AGUARDANDO_CONFIRMACAO = 'aguardando_confirmacao', 'Aguardando Confirmação'
      CONFIRMADO = 'confirmado', 'Confirmado'
      CANCELADO_USUARIO = 'cancelado_usuario', 'Cancelado pelo Usuário'
      PROCESSANDO = 'processando', 'Processando'
      ENVIADO_GATEWAY = 'enviado_gateway', 'Enviado ao Gateway'
      APROVADO = 'aprovado', 'Aprovado'
      REJEITADO = 'rejeitado', 'Rejeitado'
      ERRO = 'erro', 'Erro'
      EXPIRADO = 'expirado', 'Expirado'
  ```

- [ ] **4.2.2** Criar model `Protocolo` em `apps/core/models.py`
  ```python
  import uuid
  from django.db import models
  from django.utils import timezone

  class Protocolo(models.Model):
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

      numero_protocolo = models.CharField(
          'Número do Protocolo',
          max_length=20,
          unique=True,
          editable=False
      )

      contabilidade = models.ForeignKey(
          'contabilidade.Contabilidade',
          on_delete=models.PROTECT,
          related_name='protocolos',
          verbose_name='Contabilidade'
      )

      cliente_contabilidade = models.ForeignKey(
          'contabilidade.ClienteContabilidade',
          on_delete=models.PROTECT,
          related_name='protocolos',
          verbose_name='Cliente'
      )

      telefone_from = models.CharField('Telefone', max_length=20)
      mensagem = models.TextField('Mensagem')

      estado_mensagem = models.CharField(
          'Estado',
          max_length=30,
          choices=EstadoMensagemChoices.choices,
          default=EstadoMensagemChoices.COLETA
      )

      dados_extraidos = models.JSONField('Dados Extraídos', default=dict, blank=True)
      confidence_score = models.FloatField('Score de Confiança', default=0.0)

      tentativas = models.IntegerField('Tentativas', default=0)
      expirado_em = models.DateTimeField('Expirado em', null=True, blank=True)

      created_at = models.DateTimeField('Criado em', auto_now_add=True)
      updated_at = models.DateTimeField('Atualizado em', auto_now=True)

      class Meta:
          db_table = 'protocolo'
          verbose_name = 'Protocolo'
          verbose_name_plural = 'Protocolos'
          ordering = ['-created_at']
          indexes = [
              models.Index(fields=['contabilidade', 'created_at']),
              models.Index(fields=['cliente_contabilidade', 'created_at']),
              models.Index(fields=['telefone_from']),
              models.Index(fields=['estado_mensagem']),
          ]

      def __str__(self):
          return f'Protocolo {self.numero_protocolo}'

      def save(self, *args, **kwargs):
          if not self.numero_protocolo:
              self.numero_protocolo = self.gerar_numero_protocolo()
          super().save(*args, **kwargs)

      @staticmethod
      def gerar_numero_protocolo():
          """Gera número de protocolo único."""
          import random
          import string
          timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
          random_suffix = ''.join(random.choices(string.digits, k=4))
          return f'PROT{timestamp}{random_suffix}'
  ```

- [ ] **4.2.3** Criar model `DadosHistoricosCliente` em `apps/core/models.py`
  ```python
  class DadosHistoricosCliente(models.Model):
      """
      Armazena histórico de dados do cliente com embeddings para busca semântica.
      """
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

      cliente_contabilidade = models.ForeignKey(
          'contabilidade.ClienteContabilidade',
          on_delete=models.CASCADE,
          related_name='historico_dados'
      )

      tipo_dado = models.CharField(
          'Tipo de Dado',
          max_length=50,
          help_text='Ex: cnpj_tomador, descricao, emissao_completa'
      )

      valor = models.TextField('Valor')
      contexto_original = models.TextField('Contexto Original', help_text='Mensagem original')

      # Embedding vetorial para busca semântica (pgvector)
      # Será um campo especial que armazena vetores
      # Por enquanto, usar TextField, depois migrar para VectorField
      embedding = models.TextField('Embedding', blank=True)

      frequencia_uso = models.IntegerField('Frequência de Uso', default=1)
      ultima_utilizacao = models.DateTimeField('Última Utilização', auto_now=True)
      validado = models.BooleanField('Validado', default=False)

      created_at = models.DateTimeField(auto_now_add=True)

      class Meta:
          db_table = 'dados_historicos_cliente'
          verbose_name = 'Histórico de Dados'
          verbose_name_plural = 'Histórico de Dados'
          ordering = ['-ultima_utilizacao']
          indexes = [
              models.Index(fields=['cliente_contabilidade', 'tipo_dado']),
              models.Index(fields=['cliente_contabilidade', '-frequencia_uso']),
          ]
  ```

### 4.3 WhatsApp Webhook

- [ ] **4.3.1** Criar `WhatsAppWebhookView` em `apps/core/views/webhook.py`
  ```python
  import json
  import logging
  import hmac
  import hashlib
  from django.http import JsonResponse, HttpResponse
  from django.views import View
  from django.views.decorators.csrf import csrf_exempt
  from django.utils.decorators import method_decorator
  from django.conf import settings

  logger = logging.getLogger(__name__)

  @method_decorator(csrf_exempt, name='dispatch')
  class WhatsAppWebhookView(View):
      """
      Recebe webhooks do WhatsApp (WAHA).
      """

      def post(self, request):
          """Processa mensagem recebida."""
          try:
              # Validar autenticação
              if not self._validate_webhook(request):
                  logger.warning('Webhook não autorizado')
                  return HttpResponse(status=401)

              # Parse payload
              payload = json.loads(request.body)

              telefone = payload.get('from')
              mensagem = payload.get('body')
              message_id = payload.get('messageId')

              if not all([telefone, mensagem, message_id]):
                  logger.warning('Payload incompleto', extra={'payload': payload})
                  return JsonResponse({'error': 'Invalid payload'}, status=400)

              logger.info(
                  'Webhook recebido',
                  extra={
                      'telefone': telefone,
                      'message_id': message_id
                  }
              )

              # Processar assincronamente (implementar na próxima sprint)
              # from apps.core.tasks import process_message
              # process_message.delay(telefone, mensagem, message_id)

              return JsonResponse({'status': 'received'}, status=200)

          except Exception as e:
              logger.exception('Erro ao processar webhook')
              return JsonResponse({'error': str(e)}, status=500)

      def get(self, request):
          """Verificação do webhook (Facebook/WhatsApp pattern)."""
          mode = request.GET.get('hub.mode')
          token = request.GET.get('hub.verify_token')
          challenge = request.GET.get('hub.challenge')

          if mode == 'subscribe' and token == settings.WAHA_VERIFY_TOKEN:
              logger.info('Webhook verificado')
              return HttpResponse(challenge)

          return HttpResponse(status=403)

      def _validate_webhook(self, request):
          """Valida autenticidade do webhook usando HMAC."""
          # Implementação básica - pode ser melhorada
          api_key = request.headers.get('X-API-Key')
          return api_key == settings.WAHA_API_KEY
  ```

### 4.4 Configurações do WhatsApp

- [ ] **4.4.1** Adicionar configurações no `settings.py`
  ```python
  # WhatsApp (WAHA)
  WAHA_API_URL = config('WAHA_API_URL', default='http://localhost:3000')
  WAHA_API_KEY = config('WAHA_API_KEY', default='')
  WAHA_VERIFY_TOKEN = config('WAHA_VERIFY_TOKEN', default='')
  WAHA_SESSION_NAME = config('WAHA_SESSION_NAME', default='default')
  ```

### 4.5 URLs do Core

- [ ] **4.5.1** Criar `apps/core/urls.py`
  ```python
  from django.urls import path
  from .views.webhook import WhatsAppWebhookView

  app_name = 'core'

  urlpatterns = [
      path('webhook/whatsapp/', WhatsAppWebhookView.as_view(), name='whatsapp-webhook'),
  ]
  ```

- [ ] **4.5.2** Incluir no `config/urls.py`
  ```python
  urlpatterns = [
      # ...
      path('api/v1/', include('apps.core.urls')),
  ]
  ```

### 4.6 Admin do Core

- [ ] **4.6.1** Registrar models em `apps/core/admin.py`
  ```python
  from django.contrib import admin
  from .models import Protocolo, DadosHistoricosCliente

  @admin.register(Protocolo)
  class ProtocoloAdmin(admin.ModelAdmin):
      list_display = [
          'numero_protocolo', 'cliente_contabilidade',
          'estado_mensagem', 'confidence_score', 'created_at'
      ]
      list_filter = ['estado_mensagem', 'created_at']
      search_fields = ['numero_protocolo', 'telefone_from', 'mensagem']
      readonly_fields = ['numero_protocolo', 'created_at', 'updated_at']

      fieldsets = (
          ('Identificação', {
              'fields': ('numero_protocolo', 'contabilidade', 'cliente_contabilidade')
          }),
          ('Mensagem', {
              'fields': ('telefone_from', 'mensagem', 'estado_mensagem')
          }),
          ('Dados Extraídos', {
              'fields': ('dados_extraidos', 'confidence_score')
          }),
          ('Controle', {
              'fields': ('tentativas', 'expirado_em', 'created_at', 'updated_at')
          }),
      )

  @admin.register(DadosHistoricosCliente)
  class DadosHistoricosClienteAdmin(admin.ModelAdmin):
      list_display = [
          'cliente_contabilidade', 'tipo_dado',
          'frequencia_uso', 'validado', 'created_at'
      ]
      list_filter = ['tipo_dado', 'validado']
      search_fields = ['valor', 'contexto_original']
  ```

### 4.7 Migrations e Testes

- [ ] **4.7.1** Criar migrations
  - Executar: `python manage.py makemigrations core`

- [ ] **4.7.2** Aplicar migrations
  - Executar: `python manage.py migrate`

- [ ] **4.7.3** Testar webhook com curl
  ```bash
  curl -X POST http://localhost:8000/api/v1/webhook/whatsapp/ \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your-api-key" \
    -d '{
      "from": "+5511999999999",
      "body": "teste",
      "messageId": "wamid.123"
    }'
  ```

- [ ] **4.7.4** Criar protocolo de teste no admin

---

## SPRINT 5: App Core - Parte 2 (State Machine e Redis)

**Objetivo:** Implementar gerenciamento de estados no Redis
**Duração estimada:** 3-4 dias

### 5.1 State Manager Service

- [ ] **5.1.1** Criar `StateManager` em `apps/core/services/state_manager.py`
  ```python
  import json
  import logging
  from typing import Optional, Dict
  from django.core.cache import cache
  from django.utils import timezone

  logger = logging.getLogger(__name__)

  class StateManager:
      """
      Gerencia estados de conversas no Redis.
      """

      def __init__(self):
          self.prefix = 'state'

      def _get_key(self, telefone: str) -> str:
          """Gera chave Redis para o telefone."""
          return f'{self.prefix}:{telefone}'

      def get_state(self, telefone: str) -> Optional[Dict]:
          """
          Recupera estado do Redis.

          Returns:
              Dict com dados do estado ou None se não existir
          """
          key = self._get_key(telefone)
          data = cache.get(key)

          if data:
              logger.debug(f'Estado recuperado para {telefone}')
              return json.loads(data) if isinstance(data, str) else data

          return None

      def update_state(
          self,
          telefone: str,
          novo_estado: str,
          dados: Dict,
          protocolo_id: str,
          ttl: int = 3600
      ) -> None:
          """
          Atualiza ou cria estado no Redis.

          Args:
              telefone: Telefone do cliente
              novo_estado: Novo estado da conversa
              dados: Dados extraídos/parciais
              protocolo_id: UUID do protocolo
              ttl: Time to live em segundos (default: 1h)
          """
          key = self._get_key(telefone)

          state_data = {
              'estado': novo_estado,
              'dados': dados,
              'protocolo_id': protocolo_id,
              'timestamp': timezone.now().isoformat(),
              'tentativas': 0
          }

          # Salvar no Redis com TTL
          cache.set(key, json.dumps(state_data), timeout=ttl)

          logger.info(
              f'Estado atualizado: {novo_estado}',
              extra={
                  'telefone': telefone,
                  'ttl': ttl
              }
          )

      def clear_state(self, telefone: str) -> None:
          """Remove estado do Redis."""
          key = self._get_key(telefone)
          cache.delete(key)
          logger.info(f'Estado removido para {telefone}')

      def increment_tentativa(self, telefone: str) -> int:
          """Incrementa contador de tentativas."""
          state = self.get_state(telefone)
          if state:
              state['tentativas'] += 1
              key = self._get_key(telefone)
              cache.set(key, json.dumps(state))
              return state['tentativas']
          return 0
  ```

### 5.2 Response Builder Service

- [ ] **5.2.1** Criar `ResponseBuilder` em `apps/core/services/response_builder.py`
  ```python
  import logging
  from typing import Dict
  from decimal import Decimal

  logger = logging.getLogger(__name__)

  class ResponseBuilder:
      """
      Constrói respostas para enviar ao cliente via WhatsApp.
      """

      def build_dados_incompletos(self, campos_faltantes: list) -> str:
          """Mensagem solicitando dados faltantes."""
          campos_str = ', '.join(campos_faltantes)
          return f"""
  ⚠️ *Informações Incompletas*

  Por favor, informe os seguintes dados:
  {campos_str}

  Ou digite *cancelar* para cancelar a operação.
          """.strip()

      def build_validacao_erro(self, erros: list) -> str:
          """Mensagem de erro de validação."""
          erros_str = '\n'.join(f'• {erro}' for erro in erros)
          return f"""
  ❌ *Dados Inválidos*

  {erros_str}

  Por favor, corrija e envie novamente.
  Ou digite *cancelar* para cancelar.
          """.strip()

      def build_espelho(
          self,
          dados: Dict,
          aliquota_iss: Decimal = Decimal('0.02')
      ) -> str:
          """Monta espelho da nota para confirmação."""
          valor = Decimal(str(dados.get('valor', 0)))
          valor_iss = valor * aliquota_iss

          return f"""
  📋 *ESPELHO DA NOTA FISCAL*

  *Tomador:* {dados.get('razao_social_tomador', 'Não informado')}
  *CNPJ:* {dados.get('cnpj_tomador', 'Não informado')}

  *Descrição:* {dados.get('descricao', 'Não informado')}
  *Código Serviço:* {dados.get('codigo_servico', 'Padrão do cadastro')}

  *Valor dos Serviços:* R$ {valor:.2f}
  *ISS ({aliquota_iss * 100:.2f}%):* R$ {valor_iss:.2f}

  ━━━━━━━━━━━━━━━━━━━━
  *VALOR TOTAL:* R$ {valor:.2f}

  ✅ Confirma a emissão desta nota?

  Digite *SIM* para confirmar
  Digite *NÃO* para cancelar
          """.strip()

      def build_confirmacao_processando(self, numero_protocolo: str) -> str:
          """Mensagem de confirmação - nota em processamento."""
          return f"""
  ✅ *Nota Fiscal em Processamento!*

  Você receberá o PDF em alguns instantes.

  📝 Protocolo: {numero_protocolo}
          """.strip()

      def build_nota_aprovada(self, numero_nfe: str) -> str:
          """Mensagem de nota aprovada."""
          return f"""
  🎉 *Nota Fiscal Emitida com Sucesso!*

  Número da NFSe: *{numero_nfe}*

  O PDF está sendo enviado...
          """.strip()

      def build_nota_erro(self, erro: str) -> str:
          """Mensagem de erro na emissão."""
          return f"""
  ❌ *Erro ao Emitir Nota Fiscal*

  {erro}

  Por favor, entre em contato com sua contabilidade.
          """.strip()

      def build_cancelado(self) -> str:
          """Mensagem de operação cancelada."""
          return """
  ❌ *Operação Cancelada*

  Envie uma nova mensagem quando precisar emitir uma nota.
          """.strip()

      def build_expirado(self) -> str:
          """Mensagem de sessão expirada."""
          return """
  ⏱️ *Tempo Esgotado*

  A solicitação de nota fiscal expirou.
  Envie uma nova mensagem para recomeçar.
          """.strip()
  ```

### 5.3 Celery Task Básica

- [ ] **5.3.1** Criar task placeholder em `apps/core/tasks.py`
  ```python
  from celery import shared_task
  import logging

  logger = logging.getLogger(__name__)

  @shared_task(bind=True)
  def process_message(self, telefone: str, mensagem: str, message_id: str):
      """
      Task para processar mensagem recebida.
      Será implementada completamente nas próximas sprints.
      """
      logger.info(
          'Processando mensagem',
          extra={
              'telefone': telefone,
              'message_id': message_id,
              'task_id': self.request.id
          }
      )

      # TODO: Implementar lógica completa nas próximas sprints
      return {'status': 'pending_implementation'}
  ```

### 5.4 Testes do State Manager

- [ ] **5.4.1** Testar StateManager no Django shell
  ```python
  from apps.core.services.state_manager import StateManager

  sm = StateManager()

  # Criar estado
  sm.update_state(
      telefone='+5511999999999',
      novo_estado='dados_incompletos',
      dados={'valor': 150.00},
      protocolo_id='uuid-123',
      ttl=3600
  )

  # Recuperar estado
  estado = sm.get_state('+5511999999999')
  print(estado)

  # Limpar estado
  sm.clear_state('+5511999999999')
  ```

- [ ] **5.4.2** Verificar no Redis CLI
  ```bash
  redis-cli
  KEYS state:*
  GET state:+5511999999999
  TTL state:+5511999999999
  ```

---

## SPRINT 6: App Core - Parte 3 (IA Services)

**Objetivo:** Implementar serviços de IA (OpenAI)
**Duração estimada:** 4-5 dias

### 6.1 Configurações OpenAI

- [ ] **6.1.1** Adicionar dependências no `requirements/base.txt`
  ```
  openai==1.3.0
  tiktoken==0.5.2
  tenacity==8.2.3
  ```

- [ ] **6.1.2** Instalar dependências
  - Executar: `pip install -r requirements/base.txt`

- [ ] **6.1.3** Adicionar configurações no `settings.py`
  ```python
  # OpenAI
  OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
  OPENAI_MODEL = config('OPENAI_MODEL', default='gpt-4o-mini')
  OPENAI_EMBEDDING_MODEL = config('OPENAI_EMBEDDING_MODEL', default='text-embedding-3-small')
  ```

### 6.2 AI Extractor Service

- [ ] **6.2.1** Criar `AIExtractor` em `apps/core/services/ai_extractor.py`
  ```python
  import json
  import logging
  from typing import Dict, Optional, List
  from openai import OpenAI
  from django.conf import settings
  from django.core.cache import cache
  import tiktoken

  logger = logging.getLogger(__name__)

  class AIExtractor:
      """
      Extrai dados estruturados de mensagens usando OpenAI.
      """

      def __init__(self):
          self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
          self.model = settings.OPENAI_MODEL
          self.max_tokens = 500
          self.temperature = 0.1

      def extract_nfe_data(
          self,
          mensagem: str,
          historico_cliente: Optional[List[Dict]] = None
      ) -> Dict:
          """
          Extrai dados de NFe da mensagem.

          Returns:
              Dict com 'dados', 'confidence_score', 'tokens_used'
          """
          # Cache
          cache_key = f'extraction:{hash(mensagem)}'
          cached = cache.get(cache_key)
          if cached:
              logger.info('Usando extração em cache')
              return cached

          try:
              # Construir prompts
              system_prompt = self._build_system_prompt()
              user_prompt = self._build_user_prompt(mensagem, historico_cliente)

              # Log tokens
              token_count = self._count_tokens(system_prompt + user_prompt)
              logger.info(f'Tokens enviados: {token_count}')

              # Chamar OpenAI
              response = self.client.chat.completions.create(
                  model=self.model,
                  messages=[
                      {'role': 'system', 'content': system_prompt},
                      {'role': 'user', 'content': user_prompt}
                  ],
                  temperature=self.temperature,
                  max_tokens=self.max_tokens,
                  response_format={'type': 'json_object'}
              )

              # Parse resposta
              content = response.choices[0].message.content
              dados_extraidos = json.loads(content)

              # Resultado
              result = {
                  'dados': dados_extraidos,
                  'confidence_score': self._calculate_confidence(dados_extraidos),
                  'tokens_used': response.usage.total_tokens,
                  'model': self.model
              }

              # Cache 24h
              cache.set(cache_key, result, timeout=86400)

              logger.info(
                  'Extração concluída',
                  extra={
                      'confidence': result['confidence_score'],
                      'tokens': result['tokens_used']
                  }
              )

              return result

          except Exception as e:
              logger.exception('Erro na extração IA')
              raise

      def _build_system_prompt(self) -> str:
          """System prompt para extração."""
          return """Você é um assistente especializado em extrair dados de notas fiscais de serviço.

  TAREFA:
  Extrair dados estruturados de mensagens sobre emissão de NFSe.

  DADOS A EXTRAIR:
  - valor: Valor total da nota (número decimal)
  - tomador: Nome ou identificação do tomador
  - cnpj_tomador: CNPJ do tomador (apenas números)
  - razao_social_tomador: Razão social do tomador
  - descricao: Descrição do serviço prestado
  - codigo_servico: Código do serviço municipal (se mencionado)

  REGRAS:
  1. Retorne APENAS JSON válido
  2. Use null para campos não mencionados
  3. Valores monetários sempre como número decimal
  4. CNPJ apenas números, sem formatação
  5. Seja conservador - se não tiver certeza, use null

  FORMATO:
  {
      "valor": 150.00,
      "tomador": "Empresa XYZ",
      "cnpj_tomador": "12345678000190",
      "razao_social_tomador": "Empresa XYZ Ltda",
      "descricao": "Consultoria empresarial",
      "codigo_servico": null
  }"""

      def _build_user_prompt(self, mensagem: str, historico: Optional[List[Dict]]) -> str:
          """User prompt com contexto."""
          prompt = f"MENSAGEM:\n{mensagem}\n\n"

          if historico:
              prompt += "HISTÓRICO (para contexto):\n"
              for item in historico[:3]:
                  prompt += f"- Tomador: {item.get('tomador')}, Valor: R$ {item.get('valor')}\n"
              prompt += "\n"

          prompt += "Extraia os dados no formato JSON:"
          return prompt

      def _calculate_confidence(self, dados: Dict) -> float:
          """Calcula confidence score."""
          score = 0.0
          weights = {
              'valor': 0.4,
              'tomador': 0.3,
              'descricao': 0.2,
              'cnpj_tomador': 0.1
          }

          for field, weight in weights.items():
              if dados.get(field) is not None:
                  score += weight

          return round(score, 2)

      def _count_tokens(self, text: str) -> int:
          """Conta tokens."""
          try:
              encoding = tiktoken.encoding_for_model(self.model)
              return len(encoding.encode(text))
          except:
              # Fallback: aproximação
              return len(text) // 4
  ```

### 6.3 AI Validator Service

- [ ] **6.3.1** Criar `AIValidator` em `apps/core/services/ai_validator.py`
  ```python
  import logging
  import re
  from typing import Dict, List, Tuple

  logger = logging.getLogger(__name__)

  class AIValidator:
      """
      Valida dados extraídos pela IA.
      """

      def validate_extracted_data(self, dados: Dict) -> Tuple[bool, List[str]]:
          """
          Valida dados extraídos.

          Returns:
              (is_valid, errors)
          """
          errors = []

          # Validar valor
          if not dados.get('valor'):
              errors.append('Valor não informado')
          elif dados['valor'] <= 0:
              errors.append('Valor deve ser positivo')

          # Validar tomador
          if not dados.get('tomador'):
              errors.append('Tomador não informado')

          # Validar CNPJ (se informado)
          if dados.get('cnpj_tomador'):
              if not self._validar_cnpj(dados['cnpj_tomador']):
                  errors.append('CNPJ inválido')

          # Validar descrição
          if not dados.get('descricao'):
              errors.append('Descrição não informada')

          is_valid = len(errors) == 0

          if not is_valid:
              logger.warning('Validação falhou', extra={'errors': errors})

          return is_valid, errors

      def _validar_cnpj(self, cnpj: str) -> bool:
          """Valida CNPJ básico."""
          # Remove formatação
          cnpj = re.sub(r'[^0-9]', '', cnpj)

          if len(cnpj) != 14:
              return False

          # Validação simples - melhorar depois
          if cnpj == cnpj[0] * 14:
              return False

          return True
  ```

### 6.4 Semantic Search Service (Básico)

- [ ] **6.4.1** Criar `SemanticSearch` em `apps/core/services/semantic_search.py`
  ```python
  import logging
  from typing import List, Dict
  from apps.core.models import DadosHistoricosCliente

  logger = logging.getLogger(__name__)

  class SemanticSearch:
      """
      Busca semântica em histórico (versão básica sem embeddings).
      """

      def search_similar_emissions(
          self,
          cliente_id: str,
          query: str,
          limit: int = 5
      ) -> List[Dict]:
          """
          Busca emissões similares (versão simplificada).
          """
          try:
              # Por enquanto, busca simples por palavra-chave
              # Implementar embeddings depois
              results = DadosHistoricosCliente.objects.filter(
                  cliente_contabilidade_id=cliente_id,
                  validado=True
              ).order_by('-frequencia_uso', '-ultima_utilizacao')[:limit]

              return [
                  {
                      'tipo_dado': r.tipo_dado,
                      'valor': r.valor,
                      'frequencia_uso': r.frequencia_uso
                  }
                  for r in results
              ]

          except Exception as e:
              logger.exception('Erro na busca semântica')
              return []
  ```

### 6.5 Testes dos Serviços de IA

- [ ] **6.5.1** Testar AIExtractor no shell
  ```python
  from apps.core.services.ai_extractor import AIExtractor

  extractor = AIExtractor()
  result = extractor.extract_nfe_data('emitir nota de 150 reais para empresa XYZ')
  print(result)
  ```

- [ ] **6.5.2** Testar AIValidator
  ```python
  from apps.core.services.ai_validator import AIValidator

  validator = AIValidator()
  dados = {
      'valor': 150.00,
      'tomador': 'Empresa XYZ',
      'descricao': 'Consultoria'
  }
  is_valid, errors = validator.validate_extracted_data(dados)
  print(is_valid, errors)
  ```

### 6.6 Message Processor Service

- [ ] **6.6.1** Criar `MessageProcessor` em `apps/core/services/message_processor.py`
  ```python
  import logging
  from typing import Dict
  from apps.contabilidade.models import ClienteContabilidade
  from apps.core.models import Protocolo, EstadoMensagemChoices
  from .state_manager import StateManager
  from .ai_extractor import AIExtractor
  from .ai_validator import AIValidator
  from .response_builder import ResponseBuilder
  from .semantic_search import SemanticSearch

  logger = logging.getLogger(__name__)

  class MessageProcessor:
      """
      Orquestra o processamento de mensagens WhatsApp.
      """

      def __init__(self):
          self.state_manager = StateManager()
          self.ai_extractor = AIExtractor()
          self.ai_validator = AIValidator()
          self.response_builder = ResponseBuilder()
          self.semantic_search = SemanticSearch()

      def process(self, telefone: str, mensagem: str) -> str:
          """
          Processa mensagem e retorna resposta para o cliente.

          Args:
              telefone: Telefone do cliente (formato E.164)
              mensagem: Texto da mensagem

          Returns:
              Texto da resposta a ser enviada
          """
          logger.info('Iniciando processamento', extra={'telefone': telefone})

          try:
              # 1. Buscar cliente
              cliente = self._get_cliente(telefone)
              if not cliente:
                  return 'Telefone não cadastrado. Entre em contato com sua contabilidade.'

              # 2. Verificar intenção (cancelar?)
              if self._is_cancel_intent(mensagem):
                  return self._handle_cancel(telefone)

              # 3. Buscar estado
              estado = self.state_manager.get_state(telefone)

              # 4. Processar baseado no estado
              if not estado:
                  return self._handle_nova_mensagem(telefone, mensagem, cliente)
              elif estado['estado'] == 'dados_incompletos':
                  return self._handle_completar_dados(telefone, mensagem, cliente, estado)
              elif estado['estado'] == 'aguardando_confirmacao':
                  return self._handle_confirmacao(telefone, mensagem, cliente, estado)
              else:
                  return 'Processamento em andamento. Aguarde...'

          except Exception as e:
              logger.exception('Erro no processamento')
              return 'Erro ao processar mensagem. Tente novamente.'

      def _get_cliente(self, telefone: str):
          """Busca cliente pelo telefone."""
          try:
              return ClienteContabilidade.objects.select_related(
                  'contabilidade', 'empresa'
              ).get(telefone=telefone, is_active=True)
          except ClienteContabilidade.DoesNotExist:
              return None

      def _is_cancel_intent(self, mensagem: str) -> bool:
          """Verifica se é intenção de cancelar."""
          palavras_cancelar = ['cancelar', 'cancela', 'desistir', 'parar']
          return any(palavra in mensagem.lower() for palavra in palavras_cancelar)

      def _handle_cancel(self, telefone: str) -> str:
          """Cancela operação em andamento."""
          self.state_manager.clear_state(telefone)
          return self.response_builder.build_cancelado()

      def _handle_nova_mensagem(self, telefone: str, mensagem: str, cliente) -> str:
          """Processa nova mensagem (sem estado prévio)."""
          # Criar protocolo
          protocolo = Protocolo.objects.create(
              contabilidade=cliente.contabilidade,
              cliente_contabilidade=cliente,
              telefone_from=telefone,
              mensagem=mensagem,
              estado_mensagem=EstadoMensagemChoices.COLETA
          )

          # Buscar histórico
          historico = self.semantic_search.search_similar_emissions(
              cliente_id=str(cliente.id),
              query=mensagem,
              limit=5
          )

          # Extrair dados
          extraction_result = self.ai_extractor.extract_nfe_data(mensagem, historico)
          dados = extraction_result['dados']

          # Salvar no protocolo
          protocolo.dados_extraidos = dados
          protocolo.confidence_score = extraction_result['confidence_score']
          protocolo.save()

          # Validar
          is_valid, errors = self.ai_validator.validate_extracted_data(dados)

          if not is_valid:
              # Dados incompletos
              protocolo.estado_mensagem = EstadoMensagemChoices.DADOS_INCOMPLETOS
              protocolo.save()

              self.state_manager.update_state(
                  telefone=telefone,
                  novo_estado='dados_incompletos',
                  dados=dados,
                  protocolo_id=str(protocolo.id),
                  ttl=3600
              )

              return self.response_builder.build_dados_incompletos(errors)
          else:
              # Dados completos - pedir confirmação
              protocolo.estado_mensagem = EstadoMensagemChoices.AGUARDANDO_CONFIRMACAO
              protocolo.save()

              self.state_manager.update_state(
                  telefone=telefone,
                  novo_estado='aguardando_confirmacao',
                  dados=dados,
                  protocolo_id=str(protocolo.id),
                  ttl=600
              )

              return self.response_builder.build_espelho(dados, cliente.aliquota_iss)

      def _handle_completar_dados(self, telefone: str, mensagem: str, cliente, estado) -> str:
          """Complementa dados incompletos."""
          # TODO: Implementar merge de dados
          return 'Funcionalidade em implementação...'

      def _handle_confirmacao(self, telefone: str, mensagem: str, cliente, estado) -> str:
          """Processa confirmação do cliente."""
          mensagem_lower = mensagem.lower().strip()

          if mensagem_lower in ['sim', 's', 'ok', 'confirmo', 'confirmar']:
              # Criar nota fiscal e disparar task
              # TODO: Implementar na próxima sprint
              return 'Nota fiscal em processamento...'
          elif mensagem_lower in ['não', 'nao', 'n', 'cancelar']:
              return self._handle_cancel(telefone)
          else:
              return 'Por favor, responda SIM para confirmar ou NÃO para cancelar.'
  ```

### 6.7 Atualizar Task de Processamento

- [ ] **6.7.1** Atualizar `process_message` em `apps/core/tasks.py`
  ```python
  from celery import shared_task
  import logging
  from .services.message_processor import MessageProcessor
  from .integrations.whatsapp.client import WhatsAppClient

  logger = logging.getLogger(__name__)

  @shared_task(bind=True, max_retries=3)
  def process_message(self, telefone: str, mensagem: str, message_id: str):
      """
      Task para processar mensagem recebida.
      """
      logger.info(
          'Processando mensagem',
          extra={
              'telefone': telefone,
              'message_id': message_id
          }
      )

      try:
          # Processar mensagem
          processor = MessageProcessor()
          resposta = processor.process(telefone, mensagem)

          # Enviar resposta via WhatsApp
          whatsapp_client = WhatsAppClient()
          whatsapp_client.send_message(telefone, resposta)

          logger.info('Mensagem processada com sucesso')

          return {'status': 'success', 'resposta': resposta}

      except Exception as exc:
          logger.exception('Erro ao processar mensagem')
          raise self.retry(exc=exc, countdown=30)
  ```

### 6.8 WhatsApp Client

- [ ] **6.8.1** Criar diretório `apps/core/integrations/whatsapp/`
  - Criar: `apps/core/integrations/whatsapp/__init__.py`

- [ ] **6.8.2** Criar `WhatsAppClient` em `apps/core/integrations/whatsapp/client.py`
  ```python
  import logging
  import requests
  from typing import Optional
  from django.conf import settings
  from tenacity import retry, stop_after_attempt, wait_exponential

  logger = logging.getLogger(__name__)

  class WhatsAppClient:
      """
      Cliente para enviar mensagens via WAHA API.
      """

      def __init__(self):
          self.api_url = settings.WAHA_API_URL
          self.api_key = settings.WAHA_API_KEY
          self.session_name = settings.WAHA_SESSION_NAME

      @retry(
          stop=stop_after_attempt(3),
          wait=wait_exponential(multiplier=1, min=2, max=10)
      )
      def send_message(self, telefone: str, mensagem: str) -> dict:
          """
          Envia mensagem de texto.
          """
          url = f'{self.api_url}/api/sendText'

          payload = {
              'session': self.session_name,
              'chatId': f'{telefone}@c.us',
              'text': mensagem
          }

          headers = {
              'X-API-Key': self.api_key,
              'Content-Type': 'application/json'
          }

          logger.info(f'Enviando mensagem para {telefone}')

          try:
              response = requests.post(url, json=payload, headers=headers, timeout=10)
              response.raise_for_status()

              logger.info('Mensagem enviada com sucesso')
              return response.json()

          except requests.RequestException as e:
              logger.exception('Erro ao enviar mensagem')
              raise
  ```

### 6.9 Atualizar Webhook para Usar Task

- [ ] **6.9.1** Atualizar `WhatsAppWebhookView` para disparar task
  ```python
  # No método post()
  from apps.core.tasks import process_message

  # Processar assincronamente
  process_message.delay(telefone, mensagem, message_id)
  ```

### 6.10 Testes Integrados

- [ ] **6.10.1** Testar fluxo completo via webhook
  ```bash
  curl -X POST http://localhost:8000/api/v1/webhook/whatsapp/ \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your-key" \
    -d '{
      "from": "+5511999999999",
      "body": "emitir nota de 150 reais para empresa XYZ consultoria",
      "messageId": "wamid.123"
    }'
  ```

- [ ] **6.10.2** Verificar logs do Celery

- [ ] **6.10.3** Verificar estado no Redis

---

**[CONTINUA NO PRÓXIMO DOCUMENTO - SPRINTS 7-12]**

Este plano será continuado com:
- Sprint 7: App NFe - Parte 1 (Models, Admin)
- Sprint 8: App NFe - Parte 2 (Services, Integração Tecnospeed)
- Sprint 9: Frontend Dashboard e Templates
- Sprint 10: Fluxos Completos e Refinamentos
- Sprint 11: Testes Automatizados
- Sprint 12: Docker e Deploy

---

**LEGENDA DO CHECKLIST:**
- [ ] Tarefa não iniciada
- [X] Tarefa concluída

**OBSERVAÇÕES:**
- Cada tarefa está numerada hierarquicamente (ex: 1.1.1, 1.1.2)
- Descrições detalhadas incluem comandos, código e contexto
- Tarefas granulares para facilitar tracking
- Ordem sequencial respeitando dependências
