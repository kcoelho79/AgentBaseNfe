# Guia de Desenvolvimento

## Configuração do Ambiente

### Pré-requisitos

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Node.js (para compilação de assets, opcional)

### Instalação

#### 1. Clone o Repositório
```bash
git clone <url-do-repositorio>
cd agentbase-nfe
```

#### 2. Crie Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

#### 3. Instale Dependências
```bash
pip install -r requirements/development.txt
```

#### 4. Configure Variáveis de Ambiente

Crie arquivo `.env` na raiz:
```bash
# Django
SECRET_KEY=sua-secret-key-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/agentbase_nfe

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=sk-...

# WhatsApp (WAHA)
WAHA_API_URL=http://localhost:3000
WAHA_API_KEY=sua-api-key

# Tecnospeed (usar fake em dev)
USE_FAKE_TECNOSPEED=True
TECNOSPEED_WSDL_URL=https://api.tecnospeed.com.br/...
```

#### 5. Configure PostgreSQL

```bash
# Conecte ao PostgreSQL
psql -U postgres

# Crie database
CREATE DATABASE agentbase_nfe;

# Conecte ao database
\c agentbase_nfe

# Instale extensões
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
```

#### 6. Execute Migrações

```bash
python manage.py makemigrations
python manage.py migrate
```

#### 7. Crie Superusuário

```bash
python manage.py createsuperuser
```

#### 8. Inicie Redis

```bash
redis-server
```

#### 9. Inicie Celery (em terminal separado)

```bash
# Worker
celery -A config worker -l info

# Beat (para tarefas periódicas)
celery -A config beat -l info
```

#### 10. Inicie Servidor Django

```bash
python manage.py runserver
```

Acesse: `http://localhost:8000`

## Estrutura de Desenvolvimento

### Criando um Novo App

```bash
python manage.py startapp nome_do_app apps/nome_do_app
```

Adicione ao `INSTALLED_APPS` em `config/settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'apps.nome_do_app',
]
```

### Criando Models

```python
# apps/nome_do_app/models.py
from django.db import models
import uuid

class MinhaModel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    nome = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'minha_model'
        verbose_name = 'Minha Model'
        verbose_name_plural = 'Minhas Models'

    def __str__(self):
        return self.nome
```

### Criando Views

```python
# apps/nome_do_app/views.py
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import MinhaModel

class MinhaModelListView(LoginRequiredMixin, ListView):
    model = MinhaModel
    template_name = 'nome_do_app/minha_model_list.html'
    context_object_name = 'objetos'
    paginate_by = 50

    def get_queryset(self):
        # Filtra por tenant
        return MinhaModel.objects.filter(
            contabilidade=self.request.user.contabilidade
        )
```

### Criando Services

```python
# apps/nome_do_app/services/meu_service.py
import logging

logger = logging.getLogger(__name__)

class MeuService:
    """
    Descrição do serviço
    """

    def __init__(self):
        self.dependencia = OutroService()

    def processar(self, dados):
        """
        Processa dados
        """
        logger.info('Iniciando processamento', extra={'dados': dados})

        try:
            resultado = self.dependencia.fazer_algo(dados)
            logger.info('Processamento concluído')
            return resultado

        except Exception as e:
            logger.exception('Erro no processamento')
            raise
```

### Criando Tasks Celery

```python
# apps/nome_do_app/tasks.py
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def minha_task(self, parametro):
    """
    Descrição da task
    """
    try:
        logger.info(f'Executando task com {parametro}')

        # Lógica da task
        resultado = processar(parametro)

        return resultado

    except Exception as exc:
        logger.exception('Erro na task')
        raise self.retry(exc=exc, countdown=30)
```

### Criando Templates

```html
<!-- templates/nome_do_app/minha_model_list.html -->
{% extends 'base.html' %}

{% block title %}Minhas Models{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>Minhas Models</h2>
        <a href="{% url 'nome_do_app:create' %}" class="btn btn-primary">
            Novo
        </a>
    </div>

    <div class="card shadow-sm">
        <div class="card-body">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Nome</th>
                        <th>Criado em</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
                    {% for objeto in objetos %}
                    <tr>
                        <td>{{ objeto.nome }}</td>
                        <td>{{ objeto.created_at|date:'d/m/Y H:i' }}</td>
                        <td>
                            <a href="{% url 'nome_do_app:detail' objeto.id %}" class="btn btn-sm btn-info">
                                Ver
                            </a>
                        </td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="3" class="text-center text-muted">
                            Nenhum registro encontrado
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    {% if is_paginated %}
    <nav class="mt-4">
        <ul class="pagination justify-content-center">
            {% if page_obj.has_previous %}
            <li class="page-item">
                <a class="page-link" href="?page=1">Primeira</a>
            </li>
            <li class="page-item">
                <a class="page-link" href="?page={{ page_obj.previous_page_number }}">Anterior</a>
            </li>
            {% endif %}

            <li class="page-item active">
                <span class="page-link">
                    Página {{ page_obj.number }} de {{ page_obj.paginator.num_pages }}
                </span>
            </li>

            {% if page_obj.has_next %}
            <li class="page-item">
                <a class="page-link" href="?page={{ page_obj.next_page_number }}">Próxima</a>
            </li>
            <li class="page-item">
                <a class="page-link" href="?page={{ page_obj.paginator.num_pages }}">Última</a>
            </li>
            {% endif %}
        </ul>
    </nav>
    {% endif %}
</div>
{% endblock %}
```

## Comandos Úteis

### Django

```bash
# Criar migrações
python manage.py makemigrations

# Aplicar migrações
python manage.py migrate

# Shell interativo
python manage.py shell

# Criar superusuário
python manage.py createsuperuser

# Coletar arquivos estáticos
python manage.py collectstatic

# Rodar servidor
python manage.py runserver

# Criar dump do banco
python manage.py dumpdata > backup.json

# Restaurar dump
python manage.py loaddata backup.json
```

### Celery

```bash
# Iniciar worker
celery -A config worker -l info

# Iniciar beat (tarefas periódicas)
celery -A config beat -l info

# Monitorar filas
celery -A config inspect active

# Limpar filas
celery -A config purge
```

### PostgreSQL

```bash
# Conectar ao banco
psql -U postgres -d agentbase_nfe

# Listar tabelas
\dt

# Descrever tabela
\d nome_da_tabela

# Executar query
SELECT * FROM protocolo LIMIT 10;

# Backup
pg_dump -U postgres agentbase_nfe > backup.sql

# Restore
psql -U postgres agentbase_nfe < backup.sql
```

### Redis

```bash
# Conectar ao Redis CLI
redis-cli

# Listar todas as chaves
KEYS *

# Ver conteúdo de uma chave
GET state:+5511999999999

# Ver TTL de uma chave
TTL state:+5511999999999

# Deletar chave
DEL state:+5511999999999

# Limpar todo o database
FLUSHDB
```

## Debugging

### Django Debug Toolbar

Adicione em `requirements/development.txt`:
```
django-debug-toolbar==4.2.0
```

Configure em `config/settings.py`:
```python
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']
```

### Logs

Configure em `config/settings.py`:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'json': {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
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
            'formatter': 'json',
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

### Breakpoints

```python
# Em qualquer lugar do código
import pdb; pdb.set_trace()

# Ou use o built-in do Python 3.7+
breakpoint()
```

## Testando Localmente

### Simular Webhook do WhatsApp

```bash
curl -X POST http://localhost:8000/api/v1/webhook/whatsapp/ \
  -H "Content-Type: application/json" \
  -d '{
    "from": "+5511999999999",
    "body": "emitir nota de 150 reais para empresa XYZ",
    "timestamp": 1703600000,
    "messageId": "wamid.xxx"
  }'
```

### Usar Fake Tecnospeed

Em `.env`:
```
USE_FAKE_TECNOSPEED=True
```

Isso usa `FakeTecnospeedClient` que simula respostas do gateway.

### Testar Cache Redis

```python
from django.core.cache import cache

# Salvar
cache.set('teste', 'valor', timeout=300)

# Recuperar
valor = cache.get('teste')
print(valor)  # 'valor'

# Deletar
cache.delete('teste')
```

## Padrões de Commit

### Mensagens de Commit

Seguir padrão Conventional Commits:

```
feat: adiciona extração de dados via IA
fix: corrige validação de CNPJ
docs: atualiza documentação de API
refactor: refatora message processor
test: adiciona testes para state manager
chore: atualiza dependências
```

### Branches

```
main        - produção
develop     - desenvolvimento
feature/*   - novas funcionalidades
bugfix/*    - correções de bugs
hotfix/*    - correções urgentes em produção
```

## Deploy (Futuro)

### Checklist

- [ ] Configurar variáveis de ambiente de produção
- [ ] Configurar banco de dados PostgreSQL (RDS ou similar)
- [ ] Configurar Redis (ElastiCache ou similar)
- [ ] Configurar Celery workers
- [ ] Configurar Nginx/Gunicorn
- [ ] Configurar SSL/HTTPS
- [ ] Configurar backup automático
- [ ] Configurar monitoramento (Prometheus/Grafana)
- [ ] Configurar logs centralizados
- [ ] Configurar alertas

### Ambiente de Produção

```bash
# Coletar estáticos
python manage.py collectstatic --noinput

# Rodar migrações
python manage.py migrate --noinput

# Iniciar Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Iniciar Celery (supervisor ou systemd)
celery -A config worker -l info -c 4
celery -A config beat -l info
```

## Recursos Úteis

### Documentação

- [Django Documentation](https://docs.djangoproject.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [OpenAI API Reference](https://platform.openai.com/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)

### Ferramentas

- **Postman**: Testar APIs
- **DBeaver**: Cliente PostgreSQL
- **RedisInsight**: Cliente Redis visual
- **Flower**: Monitorar Celery
- **Django Extensions**: Comandos úteis extras
