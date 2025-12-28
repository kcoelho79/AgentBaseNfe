# Estrutura do Projeto

## Organização de Apps Django

O projeto AgentBase NFe segue o princípio de separação de responsabilidades através de Django Apps.

## Apps Principais

### 1. App Account

**Responsabilidade**: Autenticação e gerenciamento de perfis de usuários

```
apps/account/
├── models.py           # User, Profile
├── views.py            # Login, Logout, Profile
├── forms.py            # LoginForm, ProfileForm
└── templates/
    └── account/
        ├── login.html
        └── profile.html
```

**Características**:
- Sistema de autenticação nativo do Django
- Login via email (ao invés de username)
- Usuários são funcionários da contabilidade (tenant)

### 2. App Core

**Responsabilidade**: Núcleo do sistema - gerencia fluxo de mensagens, estados e agentes IA

```
apps/core/
├── models.py                    # Protocolo, EstadoMensagem
├── views/
│   └── webhook.py               # WhatsAppWebhookView
├── services/
│   ├── message_processor.py    # Orquestrador principal
│   ├── state_manager.py         # Gerencia estados no Redis
│   ├── ai_extractor.py          # Extração de dados via IA
│   ├── ai_validator.py          # Validação de dados
│   ├── semantic_search.py       # Busca semântica (pgvector)
│   └── response_builder.py      # Constrói respostas WhatsApp
├── tasks.py                     # Celery tasks
└── templates/
    └── core/
```

**Models Principais**:

#### Protocolo
```python
class Protocolo(models.Model):
    id = models.UUIDField(primary_key=True)
    numero_protocolo = models.CharField(max_length=20, unique=True)
    cliente_contabilidade = models.ForeignKey('contabilidade.ClienteContabilidade')
    contabilidade = models.ForeignKey('contabilidade.Contabilidade')
    telefone_from = models.CharField(max_length=20)
    mensagem = models.TextField()
    estado_mensagem = models.CharField(choices=EstadoMensagemChoices)
    dados_extraidos = models.JSONField()
    confidence_score = models.FloatField()
    tentativas = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Estados de Mensagem**:
```
- COLETA
- DADOS_INCOMPLETOS
- DADOS_COMPLETOS
- VALIDADO
- AGUARDANDO_CONFIRMACAO
- CONFIRMADO
- CANCELADO_USUARIO
- PROCESSANDO
- ENVIADO_GATEWAY
- APROVADO
- REJEITADO
- ERRO
- EXPIRADO
```

**Services**:

- **MessageProcessor**: Orquestra todo o fluxo de processamento
- **StateManager**: Gerencia estados das conversas no Redis (TTL)
- **AIExtractor**: Extrai dados estruturados usando OpenAI
- **AIValidator**: Valida dados extraídos
- **SemanticSearch**: Busca histórico similar usando embeddings
- **ResponseBuilder**: Constrói e envia respostas via WhatsApp

### 3. App Contabilidade

**Responsabilidade**: Gerenciamento de tenants e clientes

```
apps/contabilidade/
├── models.py           # Contabilidade, ClienteContabilidade, EmpresaCliente
├── views.py            # CRUD clientes, Dashboard, Relatórios
├── middleware.py       # TenantMiddleware (isolamento multi-tenant)
├── admin.py            # Admin customizado
└── templates/
    └── contabilidade/
        ├── dashboard.html
        ├── cliente_list.html
        └── cliente_form.html
```

**Models Principais**:

#### Contabilidade (Tenant)
```python
class Contabilidade(models.Model):
    id = models.UUIDField(primary_key=True)
    cnpj = models.CharField(max_length=14, unique=True)
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255)
    email = models.EmailField()
    plano = models.CharField(choices=PlanoChoices)
    limite_clientes = models.IntegerField(null=True)
    limite_notas_mes = models.IntegerField(null=True)
    status = models.CharField(choices=StatusChoices)
    is_active = models.BooleanField(default=True)
```

#### ClienteContabilidade
```python
class ClienteContabilidade(models.Model):
    id = models.UUIDField(primary_key=True)
    contabilidade = models.ForeignKey(Contabilidade)
    nome = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, unique=True)  # Formato E.164
    email = models.EmailField(blank=True)
    codigo_servico_municipal_padrao = models.CharField(max_length=10)
    auto_aprovar_notas = models.BooleanField(default=False)
    total_notas_emitidas = models.IntegerField(default=0)
    total_valor_notas = models.DecimalField(max_digits=15, decimal_places=2)
```

#### EmpresaClienteContabilidade
```python
class EmpresaClienteContabilidade(models.Model):
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=14)
    inscricao_estadual = models.CharField(max_length=20)
    inscricao_municipal = models.CharField(max_length=20)
    endereco_completo = models.TextField()
```

**Funcionalidades**:
- Cadastro/edição/exclusão de clientes
- Configuração de códigos de serviço padrão
- Gerenciamento de certificados digitais
- Dashboard com métricas
- Relatórios de notas emitidas

### 4. App NFe

**Responsabilidade**: Emissão de notas fiscais e integrações com gateways

```
apps/nfe/
├── models.py                # NotaFiscal, CertificadoDigital, HistoricoNota
├── views.py                 # Lista, detalhes, emissão manual
├── services/
│   ├── nfe_emitter.py       # Serviço de emissão
│   └── rps_builder.py       # Constrói XML RPS
├── integrations/
│   └── tecnospeed/
│       ├── client.py        # Cliente SOAP Tecnospeed
│       └── fake_client.py   # Mock para desenvolvimento
├── tasks.py                 # Celery tasks de emissão
└── templates/
    └── nfe/
        ├── nota_list.html
        └── nota_detail.html
```

**Models Principais**:

#### NotaFiscal
```python
class NotaFiscal(models.Model):
    id = models.UUIDField(primary_key=True)
    cliente_contabilidade = models.ForeignKey('contabilidade.ClienteContabilidade')
    contabilidade = models.ForeignKey('contabilidade.Contabilidade')
    protocolo = models.ForeignKey('core.Protocolo', null=True)

    # Dados do tomador
    cnpj_tomador = models.CharField(max_length=14)
    razao_social_tomador = models.CharField(max_length=255)

    # Dados da nota
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    descricao = models.TextField()
    codigo_servico_municipal = models.CharField(max_length=10)
    aliquota_iss = models.DecimalField(max_digits=5, decimal_places=2)
    valor_iss = models.DecimalField(max_digits=15, decimal_places=2)

    # Dados de retorno
    numero_nfe = models.CharField(max_length=20, blank=True)
    codigo_verificacao = models.CharField(max_length=100, blank=True)
    xml_nfse = models.TextField(blank=True)
    pdf_nfse = models.BinaryField(blank=True)

    # Status
    status = models.CharField(choices=StatusChoices)
    error_message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    emitida_em = models.DateTimeField(null=True)
```

#### CertificadoDigital
```python
class CertificadoDigital(models.Model):
    contabilidade = models.ForeignKey('contabilidade.Contabilidade')
    certificado_arquivo = models.BinaryField()  # .pfx
    senha = models.CharField(max_length=255)  # Criptografada
    validade = models.DateField()
    tipo = models.CharField(max_length=10)  # A1, A3
    status = models.CharField(choices=StatusChoices)
    is_active = models.BooleanField(default=True)
```

**Services**:

- **NFeEmitter**: Orquestra emissão completa
- **RPSBuilder**: Constrói XML do RPS
- **TecnospeedClient**: Integração com gateway Tecnospeed
- **FakeTecnospeedClient**: Mock para desenvolvimento/testes

## Estrutura de Diretórios Completa

```
agentbase-nfe/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── account/
│   ├── core/
│   ├── contabilidade/
│   └── nfe/
├── static/
│   ├── css/
│   │   └── custom.css
│   ├── js/
│   │   └── main.js
│   └── images/
├── media/
│   ├── certificados/
│   └── pdfs/
├── templates/
│   ├── base.html
│   ├── home.html
│   └── components/
│       ├── navbar.html
│       └── sidebar.html
├── tests/
│   ├── core/
│   ├── contabilidade/
│   └── nfe/
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── docs/                    # Esta documentação
├── manage.py
├── .env.example
├── .gitignore
└── README.md
```

## Redis: Gerenciamento de Estados

### Estrutura de Chaves

```
state:{telefone}
```

**Exemplo**:
```json
{
  "estado": "aguardando_confirmacao",
  "protocolo_id": "uuid-123",
  "dados": {
    "cnpj_tomador": "12345678000190",
    "valor": 150.00,
    "descricao": "Consultoria empresarial"
  },
  "tentativas": 1,
  "timestamp": "2025-12-26T10:30:00"
}
```

**TTL por Estado**:
- COLETA: 1 hora
- DADOS_INCOMPLETOS: 1 hora
- AGUARDANDO_CONFIRMACAO: 10 minutos
- Outros: Sem TTL (gerenciados por tasks)

## PostgreSQL: Schemas e Extensões

### Extensões Necessárias

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
```

### Tabelas Principais

```
contabilidade
cliente_contabilidade
empresa_cliente_contabilidade
certificado_digital
protocolo
nota_fiscal
historico_nota
dados_historicos_cliente  -- Com coluna embedding (vector)
audit_log
```

## Integração com Tecnospeed

### Cliente SOAP

```python
from zeep import Client

class TecnospeedClient:
    def __init__(self):
        self.wsdl_url = settings.TECNOSPEED_WSDL_URL
        self.client = Client(self.wsdl_url)

    def enviar_rps(self, rps_xml: str, certificado: bytes):
        response = self.client.service.EnviarRPS(
            xml=rps_xml,
            certificado=certificado
        )
        return response
```

### Mock para Desenvolvimento

```python
class FakeTecnospeedClient:
    """Simula respostas do gateway para desenvolvimento"""

    def enviar_rps(self, rps_xml, certificado):
        import random

        # 90% sucesso, 10% erro
        if random.random() < 0.9:
            return {
                'sucesso': True,
                'numero_nfe': f'NFE{random.randint(1000, 9999)}',
                'xml': '<xml>...</xml>',
                'pdf': b'PDF_CONTENT'
            }
        else:
            return {
                'sucesso': False,
                'erro': 'Certificado inválido'
            }
```

## Multi-tenant: Isolamento

### Middleware

```python
class TenantMiddleware:
    """
    Garante isolamento entre tenants
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Anexa tenant ao request
            request.tenant = request.user.contabilidade

        response = self.get_response(request)
        return response
```

### Manager Customizado

```python
class TenantManager(models.Manager):
    """
    Manager que filtra automaticamente por tenant
    """
    def get_queryset(self):
        # Filtra por tenant do usuário logado
        tenant = get_current_tenant()
        return super().get_queryset().filter(contabilidade=tenant)
```
