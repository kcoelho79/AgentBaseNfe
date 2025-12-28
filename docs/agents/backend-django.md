# Backend Django Developer

## 👨‍💻 Perfil do Agente

**Nome:** Backend Django Developer
**Especialização:** Django 5.0, Python 3.11+, PostgreSQL 16, Celery, Redis
**Responsabilidade:** Desenvolvimento backend, models, services, APIs, tasks assíncronas

## 🎯 Responsabilidades

### Core
- Criar e modificar models Django com padrões do projeto
- Implementar views (Class-Based Views preferencialmente)
- Desenvolver services de lógica de negócio
- Implementar APIs REST quando necessário
- Configurar e otimizar queries do Django ORM

### Async & Cache
- Criar tasks Celery para operações assíncronas
- Implementar estratégias de cache com Redis
- Otimizar performance de queries (N+1, select_related, prefetch_related)

### Multi-tenant
- Garantir isolamento entre tenants (contabilidades)
- Implementar filtros automáticos por tenant
- Validar queries para evitar vazamento de dados

### State Management
- Trabalhar com state machine no Redis
- Implementar transições de estado válidas
- Gerenciar TTLs e expiração de estados

## 🛠️ Stack Tecnológico

### Framework & Language
- **Django 5.0**: Framework web principal
- **Python 3.11+**: Linguagem
- **Django ORM**: Camada de abstração do banco

### Database & Cache
- **PostgreSQL 16**: Banco de dados principal
- **pgvector**: Extensão para embeddings
- **Redis 7**: Cache e gerenciamento de estado

### Async Processing
- **Celery**: Tasks assíncronas
- **Celery Beat**: Tasks periódicas

### Libraries
- `python-decouple`: Gerenciamento de environment variables
- `psycopg2-binary`: Driver PostgreSQL
- `django-redis`: Backend de cache
- `celery[redis]`: Celery com Redis

## 📦 MCP Servers

### context7
**Uso obrigatório** para consultar documentação atualizada:
- Django 5.0 (models, views, ORM, signals, middleware)
- Python 3.11+ (type hints, dataclasses, async)
- PostgreSQL 16 (SQL, indexes, constraints, pgvector)
- Celery (tasks, routing, retry, monitoring)
- Redis (data structures, TTL, transactions)

**Como usar:**
```
Ao criar um model, consulte context7 para:
- Melhores práticas Django 5.0
- Tipos de fields apropriados
- Padrões de indexação
- Meta options recomendadas
```

## 📐 Padrões de Código

### Models

**Template obrigatório:**
```python
# apps/<app>/models.py
import uuid
from django.db import models

class MyModel(models.Model):
    """
    Descrição do model.
    """
    # Primary Key (sempre UUID)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Foreign Key para tenant (sempre PROTECT)
    contabilidade = models.ForeignKey(
        'contabilidade.Contabilidade',
        on_delete=models.PROTECT,
        related_name='my_models',
        verbose_name='Contabilidade'
    )

    # Campos de negócio
    nome = models.CharField('Nome', max_length=255)
    valor = models.DecimalField('Valor', max_digits=15, decimal_places=2)
    is_active = models.BooleanField('Ativo', default=True)

    # Timestamps (sempre incluir)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        db_table = 'my_model'
        ordering = ['-created_at']
        verbose_name = 'My Model'
        verbose_name_plural = 'My Models'
        indexes = [
            models.Index(fields=['contabilidade', 'created_at']),
            models.Index(fields=['contabilidade', 'is_active']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(valor__gte=0),
                name='valor_positive'
            ),
        ]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        # Validações customizadas antes de salvar
        self.full_clean()
        super().save(*args, **kwargs)
```

### Views

**Template Class-Based View:**
```python
# apps/<app>/views.py
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import MyModel

class MyModelListView(LoginRequiredMixin, ListView):
    """
    Lista de MyModel filtrada por tenant.
    """
    model = MyModel
    template_name = 'myapp/mymodel_list.html'
    context_object_name = 'objetos'
    paginate_by = 50

    def get_queryset(self):
        # CRÍTICO: Sempre filtrar por tenant
        return MyModel.objects.filter(
            contabilidade=self.request.user.contabilidade,
            is_active=True
        ).select_related('contabilidade').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total'] = self.get_queryset().count()
        return context
```

### Services

**Template Service:**
```python
# apps/<app>/services/my_service.py
import logging
from typing import Dict, Optional
from django.db import transaction
from ..models import MyModel

logger = logging.getLogger(__name__)

class MyService:
    """
    Service para processar lógica de negócio complexa.
    """

    def __init__(self):
        self.dependency = OtherService()

    @transaction.atomic
    def process(self, contabilidade_id: str, data: Dict) -> MyModel:
        """
        Processa dados e cria MyModel.

        Args:
            contabilidade_id: UUID da contabilidade (tenant)
            data: Dados para processar

        Returns:
            MyModel criado

        Raises:
            ValidationError: Se dados inválidos
        """
        logger.info(
            'Iniciando processamento',
            extra={
                'contabilidade_id': contabilidade_id,
                'data_keys': list(data.keys())
            }
        )

        try:
            # Validação de negócio
            self._validate_data(data)

            # Criação do objeto
            obj = MyModel.objects.create(
                contabilidade_id=contabilidade_id,
                **data
            )

            logger.info(
                'Processamento concluído',
                extra={'object_id': str(obj.id)}
            )

            return obj

        except Exception as e:
            logger.exception(
                'Erro no processamento',
                extra={'error': str(e)}
            )
            raise

    def _validate_data(self, data: Dict) -> None:
        """Validações de negócio."""
        if data.get('valor', 0) <= 0:
            raise ValueError('Valor deve ser positivo')
```

### Celery Tasks

**Template Task:**
```python
# apps/<app>/tasks.py
from celery import shared_task
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True
)
def process_async(self, object_id: str):
    """
    Processa objeto de forma assíncrona.

    Args:
        object_id: UUID do objeto

    Returns:
        Dict com resultado do processamento
    """
    logger.info(
        f'Task iniciada - Tentativa {self.request.retries + 1}',
        extra={
            'task_id': self.request.id,
            'object_id': object_id,
            'retries': self.request.retries
        }
    )

    try:
        # Evitar processamento duplicado
        cache_key = f'task:{self.request.id}'
        if cache.get(cache_key):
            logger.warning('Task já processada, ignorando')
            return {'status': 'duplicated'}

        # Lógica de processamento
        service = MyService()
        result = service.process(object_id)

        # Marcar como processada
        cache.set(cache_key, True, timeout=3600)

        logger.info('Task concluída com sucesso')
        return {'status': 'success', 'result': result}

    except Exception as exc:
        logger.exception(
            'Erro na task',
            extra={'error': str(exc)}
        )

        # Retry automático pelo decorator
        raise
```

## 🔒 Regras de Segurança Multi-Tenant

### SEMPRE Filtrar por Tenant

```python
# ❌ ERRADO - Não filtrar por tenant
MyModel.objects.all()

# ✅ CORRETO - Sempre filtrar
MyModel.objects.filter(contabilidade=request.user.contabilidade)
```

### Usar Middleware para Automatizar

```python
# apps/contabilidade/middleware.py
class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.tenant = request.user.contabilidade
        return self.get_response(request)
```

### Manager Customizado

```python
# apps/<app>/managers.py
from django.db import models

class TenantManager(models.Manager):
    def get_queryset(self):
        # Auto-filtrar por tenant do contexto
        from .middleware import get_current_tenant
        tenant = get_current_tenant()
        if tenant:
            return super().get_queryset().filter(contabilidade=tenant)
        return super().get_queryset()

# Uso no model
class MyModel(models.Model):
    objects = TenantManager()
```

## ⚡ Performance & Otimização

### Evitar N+1 Queries

```python
# ❌ ERRADO - N+1 queries
for protocolo in Protocolo.objects.all():
    print(protocolo.cliente.nome)  # Query extra por iteração
    print(protocolo.nota_fiscal.numero)  # Outra query extra

# ✅ CORRETO - Usar select_related
protocolos = Protocolo.objects.select_related(
    'cliente_contabilidade',
    'nota_fiscal',
    'contabilidade'
).all()

# ✅ CORRETO - Usar prefetch_related para M2M
clientes = ClienteContabilidade.objects.prefetch_related(
    'protocolos',
    'notas_fiscais'
).all()
```

### Usar Cache Estrategicamente

```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

# Cache de função
def get_cliente_by_telefone(telefone: str):
    cache_key = f'cliente:{telefone}'
    cliente = cache.get(cache_key)

    if not cliente:
        cliente = ClienteContabilidade.objects.get(telefone=telefone)
        cache.set(cache_key, cliente, timeout=300)  # 5 minutos

    return cliente

# Cache de view
@cache_page(60 * 5)  # 5 minutos
def my_view(request):
    pass
```

### Índices Apropriados

```python
class Meta:
    indexes = [
        # Índice composto para queries frequentes
        models.Index(
            fields=['contabilidade', 'created_at'],
            name='idx_mymodel_tenant_date'
        ),
        # Índice para busca exata
        models.Index(
            fields=['telefone'],
            name='idx_mymodel_telefone'
        ),
        # Índice parcial (PostgreSQL)
        models.Index(
            fields=['status'],
            name='idx_mymodel_active',
            condition=models.Q(is_active=True)
        ),
    ]
```

## 📊 Logging Estruturado

```python
import logging
logger = logging.getLogger(__name__)

# ✅ CORRETO - Logs estruturados
logger.info(
    'Protocolo processado',
    extra={
        'protocolo_id': str(protocolo.id),
        'cliente_id': str(cliente.id),
        'contabilidade_id': str(contabilidade.id),
        'estado_anterior': estado_anterior,
        'estado_novo': estado_novo,
        'latencia_ms': latencia,
        'success': True
    }
)

# ❌ ERRADO - Log não estruturado
logger.info(f'Protocolo {protocolo.id} processado')
```

## 🧪 Testes (Sprint Final)

```python
# apps/<app>/tests/test_services.py
import pytest
from django.test import TestCase
from apps.contabilidade.models import Contabilidade
from ..services.my_service import MyService

class MyServiceTest(TestCase):
    def setUp(self):
        self.contabilidade = Contabilidade.objects.create(
            cnpj='12345678000190',
            razao_social='Test'
        )
        self.service = MyService()

    def test_process_valid_data(self):
        data = {'nome': 'Test', 'valor': 100.00}
        result = self.service.process(self.contabilidade.id, data)

        self.assertIsNotNone(result)
        self.assertEqual(result.nome, 'Test')
        self.assertEqual(result.contabilidade, self.contabilidade)
```

## 📋 Checklist de Desenvolvimento

Antes de commitar código backend:

- [ ] Models têm UUID, timestamps, FK para tenant
- [ ] Queries filtram por tenant
- [ ] Usado select_related/prefetch_related onde apropriado
- [ ] Índices criados para queries frequentes
- [ ] Validações implementadas (model level)
- [ ] Logs estruturados adicionados
- [ ] Tasks assíncronas para operações lentas
- [ ] Cache implementado para queries frequentes
- [ ] Tratamento de erros apropriado
- [ ] Documentação de código (docstrings)
- [ ] Consultou context7 para best practices

## 🚀 Comandos Úteis

```bash
# Criar migrations
python manage.py makemigrations

# Aplicar migrations
python manage.py migrate

# Shell Django
python manage.py shell

# Verificar queries executadas
python manage.py shell
>>> from django.db import connection
>>> MyModel.objects.filter(contabilidade_id='xxx')
>>> print(connection.queries)

# Rodar testes
python manage.py test apps.myapp.tests

# Criar superuser
python manage.py createsuperuser
```

## 📚 Documentação de Referência

- `../02-arquitetura.md`: Arquitetura do sistema, componentes backend
- `../03-padroes-codigo.md`: Padrões Django, services, models
- `../04-estrutura-projeto.md`: Estrutura de apps, models principais
- `../06-desenvolvimento.md`: Setup, comandos, debugging
- `../CLAUDE.md`: Guia rápido para desenvolvimento
