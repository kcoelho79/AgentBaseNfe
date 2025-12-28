# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AgentBase NFe** is a multi-tenant SaaS system for automated NFSe (Brazilian electronic service invoices) issuance via WhatsApp using AI. Accounting firms manage their clients who can issue invoices by simply sending a WhatsApp message.

**Stack:**
- Backend: Django 5.0 (Python 3.11+)
- Frontend: Django Templates + Bootstrap 5
- Database: PostgreSQL 16 + pgvector
- Cache/State: Redis 7
- Tasks: Celery
- AI: OpenAI GPT-4o-mini
- Integrations: WhatsApp (WAHA), Tecnospeed Gateway

## Development Setup

### Initial Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements/development.txt

# Setup PostgreSQL extensions
psql -U postgres -d agentbase_nfe
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Running the Project
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
celery -A config worker -l info

# Terminal 3: Celery Beat (periodic tasks)
celery -A config beat -l info

# Terminal 4: Django Dev Server
python manage.py runserver
```

### Essential Commands
```bash
# Database
python manage.py makemigrations
python manage.py migrate
python manage.py shell

# Testing
python manage.py test
python manage.py test apps.core.tests.test_message_processor

# Celery monitoring
celery -A config inspect active
celery -A config purge

# Redis CLI
redis-cli
KEYS state:*
GET state:+5511999999999
TTL state:+5511999999999
```

## Architecture

### Django Apps Structure

```
apps/
├── account/          # Authentication, user profiles
├── core/             # Message processing, state machine, AI services
├── contabilidade/    # Multi-tenant management, clients
└── nfe/              # NFe issuance, Tecnospeed integration
```

### Key Components

**State Machine (apps/core/services/state_manager.py)**
- Manages conversation states in Redis with TTL
- States: COLETA → DADOS_INCOMPLETOS → DADOS_COMPLETOS → VALIDADO → AGUARDANDO_CONFIRMACAO → CONFIRMADO → PROCESSANDO → ENVIADO → APROVADO
- TTLs: COLETA/DADOS_INCOMPLETOS (1h), AGUARDANDO_CONFIRMACAO (10min)

**Message Processor (apps/core/services/message_processor.py)**
- Orchestrates the complete message processing pipeline
- Coordinates AI extraction, validation, state transitions
- Handles retry logic and error scenarios

**AI Services (apps/core/services/)**
- `ai_extractor.py`: Extracts structured data from natural language messages
- `ai_validator.py`: Validates extracted data
- `semantic_search.py`: Uses pgvector embeddings for historical data search

**NFe Emitter (apps/nfe/services/nfe_emitter.py)**
- Builds RPS XML
- Signs with digital certificate (A1)
- Integrates with Tecnospeed gateway
- Handles retry logic for failed emissions

### Multi-Tenant Architecture

**Middleware (apps/contabilidade/middleware.py)**
- `TenantMiddleware`: Automatically filters queries by tenant
- Attaches `request.tenant` to authenticated requests

**Models:**
- All models have FK to `Contabilidade` (tenant)
- Use `related_name` consistently
- Always filter by tenant in querysets

### Redis Structure

```
state:{telefone}                # Conversation state (TTL based)
cache:cliente:{id}              # Client data cache (5min TTL)
cache:extraction:{hash}         # AI extraction cache (24h TTL)
session:{token}                 # Web sessions (7d TTL)
celery:*                        # Celery queues
ratelimit:{ip}                  # Rate limiting (1min TTL)
```

## Code Standards

### Language Convention
- **Code**: English (variables, functions, classes, comments)
- **UI/Interface**: Portuguese (Brazilian)
- **Documentation**: Portuguese (Brazilian)

### Python Standards
- Always use single quotes: `'text'`
- Follow PEP8
- Line length: 120 chars (when necessary)
- Use UUID for primary keys
- Always include `created_at`, `updated_at` timestamps

### Models Pattern
```python
class MyModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contabilidade = models.ForeignKey('contabilidade.Contabilidade', on_delete=models.PROTECT, related_name='my_models')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'my_model'
        ordering = ['-created_at']
        verbose_name = 'My Model'
        verbose_name_plural = 'My Models'
        indexes = [
            models.Index(fields=['contabilidade', 'created_at']),
        ]
```

### Views Pattern
- Prefer Class-Based Views (ListView, CreateView, etc.)
- Always use `LoginRequiredMixin`
- Always filter by `request.user.contabilidade` (tenant)
- Use `select_related()` and `prefetch_related()` to avoid N+1 queries

### Services Pattern
```python
# apps/myapp/services/my_service.py
import logging

logger = logging.getLogger(__name__)

class MyService:
    """
    Service description
    """
    def __init__(self):
        self.dependency = OtherService()

    def process(self, data: dict) -> Result:
        logger.info('Processing started', extra={'data': data})
        try:
            result = self.dependency.do_something(data)
            logger.info('Processing completed')
            return result
        except Exception as e:
            logger.exception('Processing failed')
            raise
```

### Celery Tasks Pattern
```python
@shared_task(bind=True, max_retries=3)
def my_task(self, parameter):
    try:
        result = process(parameter)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
```

### Template Pattern
- Use Bootstrap 5 components
- Extend from `base.html`
- Use template components in `templates/components/`
- Dark theme with gradient colors (see 03-padroes-codigo.md for color palette)

## Critical Development Rules

### DO
- ✅ Keep it simple - no over-engineering
- ✅ Use Django's built-in features whenever possible
- ✅ Put business logic in Services, not Views
- ✅ Use async tasks (Celery) for slow operations
- ✅ Always filter by tenant in queries
- ✅ Use structured logging (JSON format)
- ✅ Cache frequent queries (Redis, 5min TTL)
- ✅ Use `select_related()` for FK, `prefetch_related()` for M2M
- ✅ Validate data at model level
- ✅ Use indexes for frequently queried fields

### DON'T
- ❌ Don't use Docker initially (final sprint only)
- ❌ Don't implement tests initially (final sprint only)
- ❌ Don't add features beyond what's requested
- ❌ Don't use double quotes for strings
- ❌ Don't mix English and Portuguese in code
- ❌ Don't put business logic in views
- ❌ Don't make queries inside loops
- ❌ Don't commit secrets to code
- ❌ Don't create premature abstractions

## Security

### Multi-Tenant Isolation
- Always filter by `contabilidade` field
- Use `TenantMiddleware` for automatic filtering
- Never expose data across tenants

### Sensitive Data
- Digital certificates: AES-256 encryption
- Passwords: bcrypt hash
- API tokens: environment variables only
- Never commit `.env` file

### Rate Limiting
```python
@ratelimit(key='ip', rate='100/m')
@ratelimit(key='user', rate='1000/h')
```

## Testing Locally

### Simulate WhatsApp Webhook
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

### Use Fake Tecnospeed
Set in `.env`:
```
USE_FAKE_TECNOSPEED=True
```

This uses `FakeTecnospeedClient` that simulates gateway responses (90% success, 10% error).

## Common Workflows

### Adding a New Model
1. Create model in `apps/<app>/models.py` with UUID, timestamps, tenant FK
2. Add indexes in Meta class
3. Run `python manage.py makemigrations`
4. Run `python manage.py migrate`
5. Register in `apps/<app>/admin.py` if needed

### Adding a New Service
1. Create file in `apps/<app>/services/my_service.py`
2. Add logging with structured extra data
3. Handle exceptions properly
4. Add retry logic if needed
5. Import and use in views or tasks

### Adding a Celery Task
1. Define in `apps/<app>/tasks.py` with `@shared_task`
2. Use `bind=True` and `max_retries` for retry support
3. Add structured logging
4. Call with `.delay()` or `.apply_async()`

## Database Queries

### Avoid N+1 Queries
```python
# ❌ Bad - N+1 queries
for protocolo in Protocolo.objects.all():
    print(protocolo.cliente.nome)  # Query on each iteration

# ✅ Good - Use select_related
protocolos = Protocolo.objects.select_related('cliente_contabilidade', 'contabilidade').all()
```

### Use Caching
```python
from django.core.cache import cache

def get_cliente(telefone):
    cache_key = f'cliente:{telefone}'
    cliente = cache.get(cache_key)
    if not cliente:
        cliente = ClienteContabilidade.objects.get(telefone=telefone)
        cache.set(cache_key, cliente, timeout=300)  # 5 minutes
    return cliente
```

## Logging

Always use structured logging:
```python
import logging
logger = logging.getLogger(__name__)

logger.info(
    'Processing completed',
    extra={
        'protocolo_id': str(protocolo.id),
        'cliente_id': str(cliente.id),
        'novo_estado': resultado.novo_estado,
        'latencia_ms': latencia
    }
)
```

## Git Commit Messages

Follow Conventional Commits:
```
feat: add AI data extraction
fix: correct CNPJ validation
docs: update API documentation
refactor: refactor message processor
test: add tests for state manager
chore: update dependencies
```

## Documentation References

Detailed documentation in `/docs`:
- `01-introducao.md`: System overview, actors, basic flow
- `02-arquitetura.md`: C4 architecture, components, scalability
- `03-padroes-codigo.md`: Code standards, patterns, best practices
- `04-estrutura-projeto.md`: Apps structure, models, services
- `05-fluxos-principais.md`: Business flows, state transitions
- `06-desenvolvimento.md`: Development guide, setup, commands

## Integration Points

### WhatsApp (WAHA)
- Webhook endpoint: `POST /api/v1/webhook/whatsapp/`
- Send messages via WAHA API
- Handle message states in Redis

### OpenAI API
- Use GPT-4o-mini for extraction
- Cache results (24h TTL)
- Include historical context for better accuracy

### Tecnospeed Gateway
- SOAP/XML integration
- Digital certificate signing
- Retry logic: 3 attempts with 30s backoff
- Use `FakeTecnospeedClient` in development
