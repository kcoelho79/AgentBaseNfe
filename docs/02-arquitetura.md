# Arquitetura do Sistema

## Visão Geral

O AgentBase NFe segue uma arquitetura modular baseada em Django Apps, com separação clara de responsabilidades e integração com sistemas externos.

## Diagrama C4 - Nível 1 (Contexto)

### Atores e Sistemas

**Pessoas:**
- **Cliente da Contabilidade**: Interage via WhatsApp
- **Contador**: Gerencia clientes e configurações via dashboard web

**Sistema Principal:**
- **AgentBase NFe**: Sistema SaaS multi-tenant

**Sistemas Externos:**
- **WhatsApp Business API**: Interface de comunicação
- **OpenAI API**: Processamento de linguagem natural
- **Tecnospeed Gateway**: Emissão de NFSe
- **Sistema Prefeitura**: Validação e aprovação de notas
- **Serviço de Email**: Notificações

## Diagrama C4 - Nível 2 (Containers)

### Containers Técnicos

#### 1. Web Application (Django 5.0)
**Responsabilidades:**
- Dashboard administrativo para contabilidades
- APIs REST
- Autenticação multi-tenant
- Admin Django customizado

**Endpoints Principais:**
```
GET  /api/v1/notas/
POST /api/v1/notas/
GET  /api/v1/clientes/
POST /api/v1/clientes/
GET  /api/v1/relatorios/
POST /webhook/whatsapp/
```

#### 2. Webhook Handler
**Responsabilidades:**
- Recebe webhooks do WhatsApp
- Valida autenticação
- Identifica tenant e cliente
- Dispara processamento assíncrono
- Rate limiting

#### 3. State Machine
**Responsabilidades:**
- Gerencia estados das conversas
- Valida transições de estado
- Armazena contexto temporário no Redis
- Implementa timeouts (TTL)

**Estados:**
```
COLETA → DADOS_INCOMPLETOS → DADOS_COMPLETOS →
VALIDADO → AGUARDANDO_CONFIRMACAO → CONFIRMADO →
PROCESSANDO → ENVIADO → APROVADO
```

#### 4. AI Service
**Responsabilidades:**
- Extração de dados via OpenAI
- Validação de dados extraídos
- Busca semântica usando pgvector
- Cache de extrações

#### 5. NFe Service
**Responsabilidades:**
- Montagem de RPS (Recibo Provisório de Serviço)
- Assinatura digital com certificado A1
- Envio para Tecnospeed
- Processamento de retorno (XML/PDF)
- Retry logic

#### 6. PostgreSQL Database
**Responsabilidades:**
- Dados persistentes (source of truth)
- Relacionamentos complexos
- Busca vetorial (embeddings)
- Full-text search

**Schemas:**
```
public.contabilidade
public.cliente_contabilidade
public.empresa_cliente_contabilidade
public.nota_fiscal
public.protocolo
public.certificado_digital
public.historico_nota
public.audit_log
public.dados_historicos_cliente (com embeddings)
```

#### 7. Redis
**Responsabilidades:**
- Estados de conversa (TTL)
- Cache de consultas frequentes
- Sessões de usuário
- Fila do Celery
- Rate limiting

**Namespaces:**
```
state:{telefone}         # Estados de conversa (TTL 1h)
cache:cliente:{id}       # Cache de dados cliente (TTL 5min)
cache:extraction:{hash}  # Cache extração IA (TTL 24h)
session:{token}          # Sessões web (TTL 7d)
celery:*                 # Filas Celery
ratelimit:{ip}           # Rate limiting (TTL 1min)
```

#### 8. Celery Workers
**Responsabilidades:**
- Processamento assíncrono
- Retry automático
- Scheduled tasks
- Background jobs

**Tasks Principais:**
```python
process_message(protocolo_id)          # Processa mensagem completa
emitir_nfe_async(nota_fiscal_id)       # Emite NFSe assíncronamente
enviar_pdf_email(nota_fiscal_id)       # Envia PDF por email
cleanup_expired_states()               # Remove estados expirados
verificar_certificados_vencimento()    # Alerta certificados vencendo
```

## Comunicação Entre Componentes

### Síncrona
- **Web App ↔ PostgreSQL**: Django ORM
- **AI Service ↔ OpenAI**: HTTP REST API
- **NFe Service ↔ Tecnospeed**: SOAP/XML
- **Webhook Handler ↔ State Machine**: Python imports

### Assíncrona
- **Web App → Celery**: Redis queue
- **Celery → Email**: SMTP
- **Celery → WhatsApp**: API REST

## Escalabilidade

### Horizontal Scaling
- **Web App**: Múltiplos workers Gunicorn (Kubernetes pods)
- **Celery Workers**: Scale por fila (high priority / low priority)
- **Redis**: Redis Sentinel (HA) ou Cluster

### Vertical Scaling
- **PostgreSQL**: Recursos dedicados (CPU/RAM)
- **Redis**: Memória conforme volume

### Load Balancing
```
Internet
   ↓
Nginx (SSL termination)
   ↓
Load Balancer (Round-robin)
   ↓
[Web App 1] [Web App 2] [Web App 3]
      ↓           ↓           ↓
         PostgreSQL (Master)
              ↓
    PostgreSQL (Replica - Read)
```

## Segurança

### Network
- Todos os containers na mesma VPC privada
- Apenas Web App exposto publicamente
- PostgreSQL sem acesso externo
- Redis bind apenas localhost

### Dados Sensíveis
- Certificados digitais: criptografia AES-256
- Senhas: bcrypt hash
- Tokens API: secrets manager
- Environment variables: nunca em código

### Rate Limiting
```python
# Por IP
@ratelimit(key='ip', rate='100/m')

# Por tenant
@ratelimit(key='user', rate='1000/h')

# Por endpoint crítico
@ratelimit(key='ip', rate='10/m', method='POST')
```

## Monitoramento

### Métricas (Prometheus)
- Latência de APIs
- Taxa de erro por endpoint
- Fila Celery (tamanho, latência)
- Conexões DB
- Uso de Redis

### Logs (Estruturados - JSON)
```json
{
  "timestamp": "2025-12-26T10:30:00Z",
  "level": "INFO",
  "service": "message_processor",
  "trace_id": "uuid-123",
  "protocolo_id": "uuid-456",
  "cliente_id": "uuid-789",
  "contabilidade_id": "uuid-000",
  "acao": "extrair_dados",
  "resultado": "sucesso",
  "latencia_ms": 2500
}
```

### Alertas
- Response time > 5s
- Error rate > 5%
- Fila Celery > 1000 items
- Redis memory > 80%
- DB connections > 80%

## Estimativa de Recursos

### Para 100 emissões/dia (pequeno):
- **Web App**: 2 vCPU, 4GB RAM
- **Celery**: 1 vCPU, 2GB RAM
- **PostgreSQL**: 2 vCPU, 4GB RAM, 50GB SSD
- **Redis**: 1 vCPU, 2GB RAM

### Para 1000 emissões/dia (médio):
- **Web App**: 4 vCPU, 8GB RAM (2 instances)
- **Celery**: 2 vCPU, 4GB RAM (3 workers)
- **PostgreSQL**: 4 vCPU, 16GB RAM, 200GB SSD
- **Redis**: 2 vCPU, 4GB RAM
