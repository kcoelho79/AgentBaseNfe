# Padrões de Código e Guidelines

## Princípios Gerais

### Simplicidade
- **Não fazer over engineering**
- Código deve ser simples e direto
- Evitar abstrações prematuras
- Implementar apenas o que foi solicitado

### Convenções de Código

#### Idioma
- **Código**: Inglês (variáveis, funções, classes, comentários)
- **Interface do usuário**: Português brasileiro
- **Documentação**: Português brasileiro

#### Formatação
- **Aspas**: Sempre usar aspas simples (`'texto'`)
- **Padrão**: Seguir PEP8
- **Linha**: Máximo 120 caracteres (quando necessário)

## Estrutura do Projeto Django

### Organização em Apps

O projeto é dividido em apps Django para isolar responsabilidades:

```
agentbase-nfe/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── account/          # Autenticação e perfis
│   ├── core/             # Núcleo: mensagens, protocolos, state machine
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── services/
│   │   │   ├── message_processor.py
│   │   │   ├── state_manager.py
│   │   │   ├── ai_extractor.py
│   │   │   └── response_builder.py
│   │   └── tasks.py
│   ├── contabilidade/    # Tenants e clientes
│   │   ├── models.py
│   │   ├── views.py
│   │   └── middleware.py
│   └── nfe/              # Notas fiscais e integrações
│       ├── models.py
│       ├── views.py
│       ├── services/
│       │   └── nfe_emitter.py
│       └── integrations/
│           └── tecnospeed/
```

### Nomenclatura

#### Models
```python
# Singular, CamelCase
class Protocolo(models.Model):
    pass

class ClienteContabilidade(models.Model):
    pass
```

#### Views
```python
# Class Based Views sempre que possível
class NotaFiscalListView(ListView):
    model = NotaFiscal

class ClienteCreateView(CreateView):
    model = ClienteContabilidade
```

#### Services
```python
# Classes de serviço com responsabilidade única
class MessageProcessor:
    def process(self, telefone, mensagem):
        pass

class NFeEmitter:
    def emitir(self, nota_fiscal_id):
        pass
```

#### Variáveis e Funções
```python
# Snake_case para variáveis e funções
def extrair_dados_mensagem(mensagem):
    telefone_from = mensagem.get('from')
    dados_extraidos = ai_service.extract(mensagem)
    return dados_extraidos
```

## Padrões de Django

### Models

#### Campos Obrigatórios
```python
class Protocolo(models.Model):
    # ID sempre UUID
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Timestamps sempre presentes
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Foreign keys com related_name descritivo
    cliente_contabilidade = models.ForeignKey(
        'contabilidade.ClienteContabilidade',
        on_delete=models.PROTECT,
        related_name='protocolos'
    )
```

#### Meta Options
```python
class Meta:
    db_table = 'protocolo'
    ordering = ['-created_at']
    verbose_name = 'Protocolo'
    verbose_name_plural = 'Protocolos'
    indexes = [
        models.Index(fields=['cliente_contabilidade', 'created_at']),
    ]
```

### Views

#### Usar Class Based Views
```python
# Preferir CBVs nativos do Django
class NotaFiscalListView(LoginRequiredMixin, ListView):
    model = NotaFiscal
    template_name = 'nfe/nota_list.html'
    context_object_name = 'notas'
    paginate_by = 50

    def get_queryset(self):
        # Filtrar por tenant
        return NotaFiscal.objects.filter(
            contabilidade=self.request.user.contabilidade
        ).select_related('cliente_contabilidade')
```

### Services

#### Lógica de Negócio em Services
```python
# apps/core/services/message_processor.py
class MessageProcessor:
    """
    Orquestra o processamento de mensagens WhatsApp
    """

    def __init__(self):
        self.state_manager = StateManager()
        self.ai_extractor = AIExtractor()

    def process(self, telefone: str, mensagem: str) -> ProcessingResult:
        """
        Pipeline principal de processamento
        """
        # Lógica aqui
        pass
```

### Signals

#### Localização
Signals devem ficar em `apps/<app>/signals.py`

```python
# apps/nfe/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=NotaFiscal)
def incrementar_metricas_cliente(sender, instance, created, **kwargs):
    if created and instance.status == 'aprovado':
        instance.cliente_contabilidade.incrementar_metricas(
            valor_nota=instance.valor
        )
```

Registrar no `apps.py`:
```python
# apps/nfe/apps.py
class NfeConfig(AppConfig):
    name = 'apps.nfe'

    def ready(self):
        import apps.nfe.signals
```

## Frontend (Django Templates)

### Templates
```
templates/
├── base.html
├── components/
│   ├── navbar.html
│   ├── sidebar.html
│   └── card.html
├── nfe/
│   ├── nota_list.html
│   ├── nota_detail.html
│   └── nota_form.html
└── contabilidade/
    ├── cliente_list.html
    └── dashboard.html
```

### Design System

#### Bootstrap
```html
<!-- Usar Bootstrap 5 -->
<!-- Componentes consistentes -->
<div class="card shadow-sm">
    <div class="card-header bg-gradient-primary text-white">
        <h5>Título</h5>
    </div>
    <div class="card-body">
        Conteúdo
    </div>
</div>
```

#### Cores (Paleta com fundo escuro)
```css
/* Gradientes e cores harmônicas */
--primary: #667eea;
--secondary: #764ba2;
--success: #48bb78;
--danger: #f56565;
--warning: #ed8936;
--info: #4299e1;
--dark: #1a202c;
--background: #2d3748;
```

## Boas Práticas

### Database

#### N+1 Queries
```python
# ❌ Ruim - N+1 queries
for protocolo in Protocolo.objects.all():
    print(protocolo.cliente.nome)  # Query em cada iteração

# ✅ Bom - Usa select_related
protocolos = Protocolo.objects.select_related(
    'cliente_contabilidade',
    'contabilidade'
).all()
```

#### Índices
```python
class Meta:
    indexes = [
        # Índice para queries frequentes
        models.Index(
            fields=['contabilidade', 'created_at'],
            name='idx_proto_tenant_date'
        ),
        # Índice para telefone (busca exata)
        models.Index(
            fields=['telefone_from'],
            name='idx_proto_telefone'
        ),
    ]
```

### Segurança

#### Multi-tenant
```python
# Middleware que filtra por tenant automaticamente
class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.tenant = request.user.contabilidade
        response = self.get_response(request)
        return response
```

#### Validação de Dados
```python
# Sempre validar dados de entrada
from django.core.validators import RegexValidator

class ClienteContabilidade(models.Model):
    telefone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                r'^\+\d{12,15}$',
                'Formato E.164: +5511999999999'
            )
        ]
    )
```

### Performance

#### Cache
```python
from django.core.cache import cache

# Cache de consultas frequentes
def get_cliente(telefone):
    cache_key = f'cliente:{telefone}'
    cliente = cache.get(cache_key)

    if not cliente:
        cliente = ClienteContabilidade.objects.get(telefone=telefone)
        cache.set(cache_key, cliente, timeout=300)  # 5 minutos

    return cliente
```

#### Processamento Assíncrono
```python
# Operações demoradas sempre assíncronas
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def emitir_nfe_task(self, nota_fiscal_id):
    try:
        nfe_emitter = NFeEmitter()
        nfe_emitter.emitir(nota_fiscal_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
```

## Logs

### Logs Estruturados
```python
import logging
import json

logger = logging.getLogger(__name__)

# Log estruturado em JSON
logger.info(
    'Processamento concluído',
    extra={
        'protocolo_id': str(protocolo.id),
        'cliente_id': str(cliente.id),
        'novo_estado': resultado.novo_estado,
        'latencia_ms': latencia
    }
)
```

## Testes

### Estrutura (para sprints finais)
```
tests/
├── core/
│   ├── test_models.py
│   ├── test_views.py
│   └── services/
│       └── test_message_processor.py
├── contabilidade/
│   └── test_models.py
└── nfe/
    └── test_emitter.py
```

### Factories (pytest-factory-boy)
```python
import factory
from apps.contabilidade.models import ClienteContabilidade

class ClienteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ClienteContabilidade

    nome = factory.Faker('name', locale='pt_BR')
    telefone = factory.Sequence(lambda n: f'+5511{n:09d}')
```

## O Que NÃO Fazer

- ❌ Não usar Docker inicialmente (sprint final)
- ❌ Não implementar testes inicialmente (sprint final)
- ❌ Não adicionar funcionalidades além do solicitado
- ❌ Não usar aspas duplas
- ❌ Não misturar inglês e português no código
- ❌ Não colocar lógica de negócio nas views
- ❌ Não fazer queries dentro de loops
- ❌ Não commitar secrets no código
