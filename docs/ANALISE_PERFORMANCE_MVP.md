# Analise de Performance e Arquitetura MVP - AgentNFe

**Data:** 2026-02-08
**Cenario:** VM 8GB RAM / 4 vCPU - Monolitico
**Carga estimada:** 100 contabilidades, 2.000 empresas, ~1.000 sessoes, 10 msgs/sessao/dia = **~10.000 msgs WhatsApp/dia**

---

## 1. RESUMO EXECUTIVO

A analise identificou **14 gargalos criticos** que impediriam o MVP de operar na carga projetada. Os problemas estao organizados por severidade (P0 = bloqueante, P1 = alto impacto, P2 = medio impacto).

### Quadro de impacto

| # | Gargalo | Severidade | Tipo | Impacto estimado |
|---|---------|-----------|------|-----------------|
| 1 | SQLite como banco principal | P0 | I/O | Global write lock: 1 escrita por vez |
| 2 | Chamada OpenAI sincrona bloqueante | P0 | I/O | Worker bloqueado 1-5s por mensagem |
| 3 | Sem task queue (Celery) | P0 | Arquitetura | Emissao NFSe sincrona no request |
| 4 | Cache Redis desativado | P1 | I/O | Toda consulta bate no banco |
| 5 | Delete+recreate de mensagens a cada save | P1 | I/O | N deletes + N inserts por interacao |
| 6 | MessageProcessor instanciado por request | P1 | CPU/Memoria | Novo OpenAI client a cada msg |
| 7 | NFSeEmissao salva 4x no mesmo fluxo | P1 | I/O | 4 UPDATE queries sequenciais |
| 8 | BrasilAPI sincrona na emissao | P1 | I/O | HTTP externo no request cycle |
| 9 | Dashboard com 7+ queries isoladas | P2 | I/O | N+1 potencial |
| 10 | EmpresaListView forca list() perdendo paginacao | P2 | Memoria | Carrega tudo em memoria |
| 11 | SessaoListView subquery por telefones | P2 | I/O | Query ineficiente |
| 12 | Sem rate limiting no /send/ | P2 | Seguranca | Flood de requests |
| 13 | httpx e requests misturados sem pooling | P2 | I/O | Conexao TCP nova a cada call |
| 14 | Logging sincrono em arquivo | P2 | I/O | Disk I/O em cada log line |

---

## 2. ANALISE DETALHADA DOS GARGALOS

### 2.1 [P0] SQLite como Banco Principal

**Arquivo:** `config/settings.py:108-113`

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

**Problema:** SQLite usa um global write lock. Apenas uma operacao de escrita pode ocorrer por vez em toda a base. Com ~10.000 mensagens/dia, cada uma gerando 3-5 writes (session update, messages delete, messages bulk_create, nfse records), o banco trava sob concorrencia.

**Numeros:**
- 10.000 msgs/dia = ~0.7 msgs/segundo (media)
- Pico: ate 5-10 msgs/segundo (horario comercial)
- Cada mensagem: ~5 operacoes de escrita
- SQLite suporta ~50-100 writes/segundo
- Limite pratico com WAL mode: ~200 writes/segundo
- **Margem:** Funcionaria no caso medio mas falharia em picos

**Solucao:** Migrar para PostgreSQL (ja tem psycopg2-binary no requirements.txt e DATABASE_URL no .env).

---

### 2.2 [P0] Chamada OpenAI Sincrona Bloqueante

**Arquivo:** `apps/core/agent_extractor.py:72-81`

```python
response = self.client.beta.chat.completions.parse(
    model=self.model,
    messages=[...],
    response_format=DadosNFSe,
    max_tokens=1024,
    temperature=0.4,
)
```

**Problema:** Cada mensagem em estado COLETA ou DADOS_INCOMPLETOS faz uma chamada HTTP sincrona para a OpenAI que demora 1-5 segundos. O worker do gunicorn fica bloqueado durante esse tempo. Com 4 workers sync, apenas 4 mensagens podem ser processadas simultaneamente.

**Numeros:**
- Latencia media OpenAI gpt-4o-mini: ~1.5-3s
- 4 workers sync = 4 requests simultaneos
- Throughput maximo: ~2.6 msgs/segundo (4 / 1.5s)
- Pico necessario: 5-10 msgs/segundo
- **Deficit: workers insuficientes em pico**

**Solucao:** Gunicorn com workers async (gevent/uvicorn) ou mover processamento para Celery.

---

### 2.3 [P0] Sem Task Queue (Celery)

**Arquivo:** `apps/core/message_processor.py:158-163`

```python
# _handle_confirmacao - NFSe emitida dentro do request
nfse = NFSeEmissaoService.emitir_de_sessao(session.sessao_id)
```

**Problema:** A emissao de NFSe (que inclui consulta BrasilAPI, criacao de 4+ registros no banco, chamada ao gateway) e feita sincronamente dentro do request HTTP. Se o gateway real (Teknospeed) demorar, o WhatsApp webhook pode dar timeout.

**Numeros do fluxo de emissao (sincrono):**
1. SessionSnapshot.objects.get() - ~1ms
2. UsuarioEmpresa query - ~1ms
3. BrasilAPI HTTP call - ~500ms-2s
4. EmpresaClienteTomador.get_or_create - ~2ms
5. NFSeEmissao.create + 3x .save() - ~10ms
6. Gateway HTTP call (mock agora, real sera ~1-5s) - ~1ms mock
7. NFSeProcessada.create - ~2ms
8. Session.save - ~2ms
- **Total atual (mock):** ~520ms-2s
- **Total real (Teknospeed):** ~2-8s

---

### 2.4 [P1] Cache Redis Desativado

**Arquivo:** `config/settings.py:138-148`

```python
# Cache COMENTADO
#CACHES = {
#    'default': {
#        'BACKEND': 'django_redis.cache.RedisCache',
#        'LOCATION': config('REDIS_URL'),
#        ...
#    }
#}
```

**Problema:** Sem cache, todas as consultas repetem queries no banco. Dados como UsuarioEmpresa (verificacao por telefone a cada msg), ClienteTomador (na construcao do espelho), e sessoes ativas sao consultados repetidamente.

**Dados que se beneficiariam de cache:**
- `UsuarioEmpresa` lookup por telefone (a cada mensagem) - TTL: 5min
- `ClienteTomador` por CNPJ (no espelho e emissao) - TTL: 24h
- Dashboard metrics (contagens) - TTL: 1min
- Session data (sessao ativa por telefone) - TTL: TTL da sessao

---

### 2.5 [P1] Delete + Recreate de Mensagens a Cada Save

**Arquivo:** `apps/core/session_manager.py:134-136`

```python
# Atualizar mensagens (delete and recreate)
existing.messages.all().delete()
self._save_messages(existing, session)
```

**Problema:** A cada interacao, TODAS as mensagens da sessao sao deletadas e recriadas. Em uma sessao com 10 interacoes, sao 20+ mensagens (user + bot + system) deletadas e reinseridas. Em SQLite com write lock, isso amplifica o problema.

**Numeros por interacao (sessao com N mensagens):**
- DELETE: 1 operacao (DELETE FROM session_message WHERE session_id=X)
- INSERT: N operacoes (bulk_create)
- Na 10a interacao: ~30 mensagens deletadas e recriadas
- **10.000 msgs/dia * 30 mensagens media = 300.000 operacoes/dia desnecessarias**

**Solucao:** Append-only - inserir apenas mensagens novas, nao deletar existentes.

---

### 2.6 [P1] MessageProcessor Instanciado por Request

**Arquivo:** `apps/core/views.py:41`

```python
processor = MessageProcessor()  # Novo a cada request
```

**Arquivo:** `apps/core/message_processor.py:20-23`

```python
def __init__(self):
    self.session_manager = SessionManager()
    self.extractor = AIExtractor()  # Cria novo OpenAI client
    self.response_builder = ResponseBuilder()
```

**Arquivo:** `apps/core/agent_extractor.py:49`

```python
self.client = OpenAI(api_key=self.api_key)  # HTTP client novo
```

**Problema:** A cada request, um novo OpenAI client e criado (novo connection pool HTTP, novo carregamento de prompt de arquivo). O prompt file e lido do disco a cada instanciacao tambem (linha 38: `prompt_path.read_text()`).

**Solucao:** Singleton ou module-level instance para MessageProcessor/AIExtractor.

---

### 2.7 [P1] NFSeEmissao Salva 4x no Mesmo Fluxo

**Arquivo:** `apps/nfse/services/emissao.py:88-127`

```python
emissao = NFSeEmissao.objects.create(...)   # INSERT
emissao.payload_enviado = payload
emissao.save()                              # UPDATE 1
emissao.status = 'enviado'
emissao.save()                              # UPDATE 2
emissao.resposta_gateway = resposta
emissao.status = 'processando'
emissao.save()                              # UPDATE 3
emissao.status = 'concluido'
emissao.save()                              # UPDATE 4
```

**Problema:** 1 INSERT + 4 UPDATEs para a mesma linha, quando poderia ser 1 INSERT + 1 UPDATE final. Cada .save() em SQLite adquire o write lock.

**Solucao:** Acumular mudancas e fazer um unico save() no final, ou usar `update_fields` para minimizar I/O.

---

### 2.8 [P1] BrasilAPI Sincrona na Emissao

**Arquivo:** `apps/nfse/services/receita_federal.py:36`

```python
response = httpx.get(url, timeout=10)  # Sincrono, bloqueia worker
```

**Problema:** A consulta CNPJ na BrasilAPI e feita de forma sincrona no fluxo de emissao. Se a BrasilAPI estiver lenta (timeout de 10s), o request inteiro fica bloqueado. Sem retry em caso de falha temporaria.

**Solucao:** Cache no banco (ja faz com ClienteTomador), mas a primeira consulta de um CNPJ novo ainda bloqueia. Mover para task async.

---

### 2.9 [P2] Dashboard com 7+ Queries Isoladas

**Arquivo:** `apps/contabilidade/views.py:56-99`

```python
context['total_empresas'] = Empresa.objects.filter(...).count()          # Query 1
context['certificados_vencendo'] = Certificado.objects.filter(...).count()  # Query 2
context['total_usuarios_empresas'] = UsuarioEmpresa.objects.filter(...).count()  # Query 3
context['total_notas'] = NFSeEmissao.objects.filter(...).count()          # Query 4
context['sessoes_ativas'] = SessionSnapshot.objects.filter(...).count()   # Query 5
context['sessoes_recentes'] = SessionSnapshot.objects.filter(...)[:10]    # Query 6
context['certificados_lista'] = Certificado.objects.filter(...)[:5]       # Query 7
```

**Problema:** 7 queries separadas ao banco na dashboard. O filtro `empresa_id__in=Empresa.objects.filter(contabilidade=contabilidade).values_list('id', flat=True)` gera subquery.

**Solucao:** Cache Redis para metricas (TTL 1min), ou agregar queries com raw SQL/subquery.

---

### 2.10 [P2] EmpresaListView Forca list()

**Arquivo:** `apps/contabilidade/views.py:146`

```python
empresas = list(qs)  # Forca avaliacao de TODO o queryset
```

**Problema:** Mesmo com `paginate_by = 20`, a contagem de sessoes forca a avaliacao de todas as empresas em memoria. Com 2.000 empresas, isso carrega tudo.

**Solucao:** Usar subquery annotation ao inves de pos-processamento em Python.

---

### 2.11 [P2] SessaoListView Subquery por Telefones

**Arquivo:** `apps/contabilidade/views.py:360-365`

```python
telefones = UsuarioEmpresa.objects.filter(
    empresa__contabilidade=contabilidade, is_active=True
).values_list('telefone', flat=True)
qs = SessionSnapshot.objects.filter(telefone__in=telefones)
```

**Problema:** Com 2.000 empresas e multiplos usuarios por empresa, `telefone__in` pode gerar uma clausula IN com milhares de valores, tornando a query lenta.

**Solucao:** Usar JOIN via subquery ou campo empresa_id (que ja existe no SessionSnapshot).

---

### 2.12 [P2] Sem Rate Limiting no /send/

**Arquivo:** `apps/core/views.py:25-57`

```python
@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    ...
```

**Problema:** Endpoint sem autenticacao, sem CSRF, sem rate limiting. Um unico telefone pode enviar ilimitadas mensagens, cada uma consumindo uma chamada OpenAI ($) e bloqueando um worker.

**Solucao:** Rate limiting por IP/telefone (django-ratelimit ou middleware customizado).

---

### 2.13 [P2] httpx e requests Misturados

**Arquivos:**
- `apps/nfse/services/receita_federal.py` - usa `httpx`
- `apps/whatsapp_api/services/evolution.py` - usa `requests`
- `apps/core/models.py:101` - usa `httpx` (consultar_receita)

**Problema:** Duas bibliotecas HTTP diferentes sem connection pooling compartilhado. Cada chamada abre nova conexao TCP.

**Solucao:** Padronizar em `httpx` com `httpx.Client()` reutilizavel (connection pooling).

---

### 2.14 [P2] Logging Sincrono em Arquivo

**Arquivo:** `config/settings.py:228-241`

```python
'file': {
    'class': 'logging.handlers.RotatingFileHandler',
    ...
}
```

**Problema:** RotatingFileHandler e sincrono - cada log.info() faz I/O no disco. Com logging extensivo no fluxo de mensagens (20+ log lines por request), isso adiciona latencia.

**Solucao:** QueueHandler para logging assincrono, ou reduzir verbosidade em producao.

---

## 3. CAPACIDADE ESTIMADA DA VM (8GB / 4 vCPU)

### 3.1 Distribuicao de Memoria Recomendada

| Servico | Memoria | Observacao |
|---------|---------|-----------|
| Linux + OS | 512 MB | Kernel, buffers |
| PostgreSQL | 2 GB | shared_buffers=512MB, work_mem, caches |
| Redis | 512 MB | Cache + sessions |
| Django/Gunicorn | 2 GB | 4 workers * ~200MB + overhead |
| Evolution API | 1.5 GB | Node.js + Chrome/Baileys |
| Caddy | 128 MB | Reverse proxy |
| Margem | 1.3 GB | Buffer para picos |
| **Total** | **8 GB** | |

### 3.2 Distribuicao de CPU

| Servico | vCPU | Observacao |
|---------|------|-----------|
| Django/Gunicorn | 1.5 | Workers sync com I/O wait alto |
| PostgreSQL | 1.0 | Queries, WAL, vacuum |
| Evolution API | 0.5 | Event-driven, baixo uso constante |
| Redis | 0.3 | Single-threaded, muito rapido |
| Caddy + OS | 0.2 | Minimal |
| **Total** | **3.5** | Margem de 0.5 vCPU |

### 3.3 Throughput Estimado (apos otimizacoes)

| Metrica | Valor | Calculo |
|---------|-------|---------|
| Mensagens/dia | 10.000 | 1.000 sessoes * 10 msgs |
| Msgs/hora (pico 8h) | 1.250 | 10.000 / 8h horario comercial |
| Msgs/segundo (media) | 0.35 | 1.250 / 3600 |
| Msgs/segundo (pico) | 3-5 | Burst de ate 5x a media |
| Chamadas OpenAI/dia | ~7.000 | ~70% msgs passam pelo AI (COLETA/DADOS_INCOMPLETOS) |
| Workers gunicorn necessarios | 4-8 | Depende de sync vs async |

**Conclusao:** A VM de 8GB/4vCPU **e suficiente** para o MVP com as otimizacoes propostas.

---

## 4. ARQUITETURA PROPOSTA MVP

### 4.1 Diagrama de Deploy (VM Unica)

```
                    INTERNET
                       |
                  [Caddy:443]
                   /    |    \
                  /     |     \
    [Django:8000] [Evolution:8080] [Static files]
         |              |
    [PostgreSQL:5432]   |
         |              |
    [Redis:6379]--------+
         |
    [Celery Worker]
```

### 4.2 Stack Completa

```
VM 8GB / 4 vCPU
|
+-- Caddy (reverse proxy + SSL + static files)
|   - :443 -> Django :8000 (app)
|   - :443/whatsapp -> Evolution :8080 (webhook passthrough)
|   - Static/Media files servidos diretamente
|
+-- Gunicorn + Django (WSGI sync, 4 workers)
|   - Workers: 4 (sync) ou 2 (gevent com greenlets)
|   - max-requests: 1000 (recicla workers)
|   - timeout: 120s (para requests com OpenAI)
|
+-- Celery (1 worker, 4 threads)
|   - Queue: default (emissao NFSe, webhooks)
|   - Queue: ai (chamadas OpenAI - futuro)
|   - Broker: Redis
|   - Result Backend: Redis
|
+-- PostgreSQL 16
|   - shared_buffers: 512MB
|   - work_mem: 4MB
|   - effective_cache_size: 3GB
|   - max_connections: 50
|
+-- Redis 7
|   - maxmemory: 256mb
|   - maxmemory-policy: allkeys-lru
|   - Uso: Cache Django + Celery broker + Session cache
|
+-- Evolution API
|   - Node.js runtime
|   - Database: mesmo PostgreSQL (schema separado)
```

---

## 5. PLANO DE OTIMIZACOES (Ordenado por Prioridade)

### Fase 1 - Criticos (Pre-lancamento)

#### 5.1 Migrar SQLite para PostgreSQL

```python
# config/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='agentbase_nfe'),
        'USER': config('DB_USER', default='agentbase_user'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'connect_timeout': 5,
        },
    }
}
```

**Passos:**
1. Instalar PostgreSQL 16 na VM
2. Criar database e usuario
3. Alterar settings.py
4. `python manage.py migrate` (cria schema novo)
5. Exportar dados do SQLite: `python manage.py dumpdata > backup.json`
6. Importar no PostgreSQL: `python manage.py loaddata backup.json`

#### 5.2 Ativar Redis Cache

```python
# config/settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 300,  # 5 min default
    }
}

# Session backend via Redis (mais rapido que DB)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

**Adicionar ao requirements.txt:**
```
django-redis==5.4.0
```

#### 5.3 Implementar Celery para Tasks Assincronas

```python
# config/celery.py (novo arquivo)
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('agentbase')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

```python
# config/settings.py (adicionar)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SOFT_TIME_LIMIT = 120
CELERY_TASK_TIME_LIMIT = 180
CELERY_WORKER_MAX_TASKS_PER_CHILD = 500
```

**Adicionar ao requirements.txt:**
```
celery==5.4.0
```

**Tasks a migrar para Celery:**
1. `NFSeEmissaoService.emitir_de_sessao()` - maior ganho
2. Webhook NFSe processing
3. Futuro: Envio de mensagens WhatsApp via Evolution

#### 5.4 Singleton para MessageProcessor/AIExtractor

```python
# apps/core/views.py - usar singleton
_processor = None

def get_processor():
    global _processor
    if _processor is None:
        _processor = MessageProcessor()
    return _processor

@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    ...
    processor = get_processor()
    resposta = processor.process(telefone, mensagem)
    ...
```

---

### Fase 2 - Alto Impacto (Semana 1 pos-lancamento)

#### 5.5 Otimizar Session Save (Append-Only Messages)

```python
# apps/core/session_manager.py - save_session otimizado
@transaction.atomic
def save_session(self, session: Session, reason: str = 'manual') -> None:
    existing = SessionSnapshot.objects.filter(sessao_id=session.sessao_id).first()

    if existing:
        existing.update_from_session(session)
        existing.snapshot_reason = reason
        existing.save()

        # APPEND-ONLY: so inserir mensagens novas
        existing_count = existing.messages.count()
        new_messages = session.context[existing_count:]  # Mensagens que ainda nao estao no banco

        messages_to_create = []
        for order, msg in enumerate(new_messages, start=existing_count):
            messages_to_create.append(
                SessionMessage(
                    session=existing,
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    order=order
                )
            )
        if messages_to_create:
            SessionMessage.objects.bulk_create(messages_to_create)
    else:
        # ...criar novo (mantém logica atual)
```

#### 5.6 Otimizar NFSeEmissao - Single Save

```python
# apps/nfse/services/emissao.py - reduzir saves
emissao = NFSeEmissao(
    session=session,
    prestador=prestador,
    tomador=tomador,
    id_integracao=id_integracao,
    descricao_servico=session.descricao or "Serviços prestados",
    valor_servico=session.valor,
    status='pendente'
)

# Montar payload sem salvar
payload = NFSeBuilder.build_payload(emissao)
emissao.payload_enviado = payload

# Enviar para gateway
resposta = MockNFSeGateway.emitir_nfse(payload)
emissao.resposta_gateway = resposta

# Salvar UMA vez com todos os dados
emissao.status = 'concluido'
emissao.enviado_em = timezone.now()
emissao.processado_em = timezone.now()
emissao.save()  # 1 INSERT unico
```

#### 5.7 Cache de Consultas Frequentes

```python
# apps/core/message_processor.py - cache UsuarioEmpresa lookup
from django.core.cache import cache

def _get_usuario_empresa(self, telefone):
    cache_key = f'usuario_empresa:{telefone}'
    usuario = cache.get(cache_key)
    if not usuario:
        usuario = UsuarioEmpresa.objects.filter(
            telefone=telefone, is_active=True
        ).select_related('empresa').first()
        if usuario:
            cache.set(cache_key, usuario, timeout=300)  # 5 min
    return usuario
```

```python
# apps/nfse/services/receita_federal.py - cache ClienteTomador
from django.core.cache import cache

@classmethod
def buscar_ou_criar_tomador(cls, cnpj: str) -> ClienteTomador:
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    cache_key = f'tomador:{cnpj_limpo}'

    tomador = cache.get(cache_key)
    if tomador:
        return tomador

    tomador = ClienteTomador.objects.filter(cnpj=cnpj_limpo).first()
    if tomador:
        cache.set(cache_key, tomador, timeout=86400)  # 24h
        return tomador

    # ...consulta BrasilAPI e cria
    cache.set(cache_key, tomador, timeout=86400)
    return tomador
```

---

### Fase 3 - Medio Impacto (Semana 2-3)

#### 5.8 Otimizar Dashboard com Cache

```python
# apps/contabilidade/views.py
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    contabilidade = self.request.user.contabilidade
    cache_key = f'dashboard:{contabilidade.id}'

    cached = cache.get(cache_key)
    if cached:
        context.update(cached)
        return context

    # ... calcular metricas (codigo atual) ...

    # Cache por 60 segundos
    metrics = {
        'total_empresas': context['total_empresas'],
        'certificados_vencendo': context['certificados_vencendo'],
        # ...
    }
    cache.set(cache_key, metrics, timeout=60)
    return context
```

#### 5.9 Otimizar EmpresaListView com Subquery

```python
# apps/contabilidade/views.py - EmpresaListView.get_queryset
from django.db.models import Subquery, OuterRef, Count

qs = qs.annotate(
    total_usuarios=Count('usuarios_autorizados', distinct=True),
    total_clientes=Count('clientes_tomadores_vinculados', distinct=True),
    total_notas=Count('nfse_emitidas', distinct=True),
    total_sessoes=Subquery(
        SessionSnapshot.objects.filter(
            empresa_id=OuterRef('pk')
        ).values('empresa_id').annotate(c=Count('id')).values('c')
    )
)
# NAO converter para list() - deixar o paginator fazer a query
return qs
```

#### 5.10 Otimizar SessaoListView

```python
# Usar empresa_id ao inves de telefone__in
qs = SessionSnapshot.objects.filter(
    empresa_id__in=Empresa.objects.filter(
        contabilidade=contabilidade
    ).values_list('id', flat=True)
)
```

#### 5.11 Rate Limiting no /send/

```python
# requirements.txt
# django-ratelimit==4.1.0

# apps/core/views.py
from django_ratelimit.decorators import ratelimit

@csrf_exempt
@require_http_methods(["POST"])
@ratelimit(key='post:telefone', rate='30/m', method='POST')
def send_message(request):
    if getattr(request, 'limited', False):
        return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
    ...
```

#### 5.12 Padronizar HTTP Client

```python
# apps/core/http_client.py (novo)
import httpx

# Client reutilizavel com connection pooling
_client = None

def get_http_client():
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _client
```

---

## 6. CONFIGURACAO GUNICORN (PRODUCAO)

```python
# gunicorn.conf.py
import multiprocessing

bind = "127.0.0.1:8000"
workers = 4  # 2 * CPU + 1, mas limitado pela RAM
worker_class = "sync"  # ou "gevent" se instalar gevent
threads = 1
timeout = 120  # OpenAI pode demorar
max_requests = 1000  # Recicla workers para evitar memory leak
max_requests_jitter = 50
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Limitar memoria por worker
worker_tmp_dir = "/dev/shm"  # tmpfs para heartbeat (mais rapido)
```

**Iniciar:**
```bash
gunicorn config.wsgi:application -c gunicorn.conf.py
```

---

## 7. CONFIGURACAO POSTGRESQL (PRODUCAO)

```sql
-- postgresql.conf otimizado para 8GB VM

-- Memoria
shared_buffers = '512MB'            -- 25% da RAM dedicada ao PG
effective_cache_size = '3GB'         -- RAM estimada para cache OS
work_mem = '4MB'                     -- Por operacao sort/hash
maintenance_work_mem = '128MB'       -- VACUUM, CREATE INDEX

-- WAL
wal_buffers = '16MB'
checkpoint_completion_target = 0.9
max_wal_size = '1GB'
min_wal_size = '256MB'

-- Conexoes
max_connections = 50                 -- 4 gunicorn + 4 celery + 10 overhead
listen_addresses = 'localhost'       -- Apenas local (monolitico)

-- Query Planner
random_page_cost = 1.1               -- SSD
effective_io_concurrency = 200       -- SSD
default_statistics_target = 100

-- Logging
log_min_duration_statement = 200     -- Log queries > 200ms
log_checkpoints = on
log_connections = on
log_disconnections = on
```

---

## 8. CONFIGURACAO REDIS (PRODUCAO)

```conf
# redis.conf

# Memoria
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistencia (RDB para backup, sem AOF para performance)
save 900 1
save 300 10
save 60 10000

# Rede
bind 127.0.0.1
port 6379
timeout 300

# Performance
tcp-backlog 511
tcp-keepalive 300
databases 4
# 0: Django cache
# 1: Celery broker
# 2: Celery results
# 3: Reservado
```

---

## 9. CONFIGURACAO CADDY (PRODUCAO)

```caddyfile
# Caddyfile

agentbase.seudominio.com.br {
    # Django app
    handle /static/* {
        root * /home/kleber/projetos/AgentBase/mensageria/agentNfe/staticfiles
        file_server
    }

    handle /media/* {
        root * /home/kleber/projetos/AgentBase/mensageria/agentNfe/media
        file_server
    }

    handle {
        reverse_proxy localhost:8000 {
            header_up X-Forwarded-Proto {scheme}
            header_up X-Forwarded-For {remote_host}
            header_up X-Real-IP {remote_host}
        }
    }

    # Rate limiting basico no Caddy
    @api path /send/*
    rate_limit @api {
        zone api_limit {
            key {remote_host}
            events 60
            window 1m
        }
    }

    # Compressao
    encode gzip zstd

    # Logging
    log {
        output file /var/log/caddy/access.log
        format json
    }
}
```

---

## 10. SYSTEMD SERVICES

### 10.1 Django/Gunicorn

```ini
# /etc/systemd/system/agentbase.service
[Unit]
Description=AgentBase Django App
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=kleber
Group=kleber
WorkingDirectory=/home/kleber/projetos/AgentBase/mensageria/agentNfe
ExecStart=/home/kleber/projetos/AgentBase/mensageria/agentNfe/.venv/bin/gunicorn \
    config.wsgi:application \
    -c gunicorn.conf.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
Environment=DJANGO_SETTINGS_MODULE=config.settings

[Install]
WantedBy=multi-user.target
```

### 10.2 Celery Worker

```ini
# /etc/systemd/system/agentbase-celery.service
[Unit]
Description=AgentBase Celery Worker
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=kleber
Group=kleber
WorkingDirectory=/home/kleber/projetos/AgentBase/mensageria/agentNfe
ExecStart=/home/kleber/projetos/AgentBase/mensageria/agentNfe/.venv/bin/celery \
    -A config worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=500 \
    -Q default,ai
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
Environment=DJANGO_SETTINGS_MODULE=config.settings

[Install]
WantedBy=multi-user.target
```

### 10.3 Celery Beat (Agendamento)

```ini
# /etc/systemd/system/agentbase-celerybeat.service
[Unit]
Description=AgentBase Celery Beat Scheduler
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=kleber
Group=kleber
WorkingDirectory=/home/kleber/projetos/AgentBase/mensageria/agentNfe
ExecStart=/home/kleber/projetos/AgentBase/mensageria/agentNfe/.venv/bin/celery \
    -A config beat \
    --loglevel=info \
    --schedule=/tmp/agentbase-celerybeat-schedule
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
Environment=DJANGO_SETTINGS_MODULE=config.settings

[Install]
WantedBy=multi-user.target
```

---

## 11. MONITORAMENTO BASICO

### 11.1 Health Check Endpoint (melhorado)

```python
# apps/core/views.py
@require_http_methods(["GET"])
def health(request):
    from django.db import connection
    from django.core.cache import cache

    checks = {}

    # Database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {e}'

    # Redis
    try:
        cache.set('health_check', 'ok', timeout=5)
        assert cache.get('health_check') == 'ok'
        checks['redis'] = 'ok'
    except Exception as e:
        checks['redis'] = f'error: {e}'

    # OpenAI (apenas verifica configuracao)
    from django.conf import settings
    checks['openai_configured'] = bool(settings.OPENAI_API_KEY)

    status = 'ok' if all(v == 'ok' for v in checks.values() if isinstance(v, str) and v == 'ok') else 'degraded'

    return JsonResponse({
        'status': status,
        'checks': checks,
        'service': 'AgentNFe'
    }, status=200 if status == 'ok' else 503)
```

### 11.2 Metricas no Log (para futuro Prometheus/Grafana)

Metricas essenciais a monitorar:
- **Response time** do `/send/` (P50, P95, P99)
- **OpenAI latency** por chamada
- **Sessoes ativas** em tempo real
- **Celery queue depth** (tarefas pendentes)
- **PostgreSQL connections** em uso
- **Redis memory usage**
- **CPU e RAM** da VM (htop, node_exporter)

---

## 12. CHECKLIST PRE-LANCAMENTO

```
[ ] PostgreSQL instalado e configurado
[ ] Migrar dados do SQLite para PostgreSQL
[ ] Redis cache ativado no settings.py
[ ] Celery configurado e rodando como service
[ ] NFSe emissao migrada para task Celery
[ ] Gunicorn configurado com 4 workers e timeout 120s
[ ] Caddy configurado como reverse proxy com SSL
[ ] systemd services criados para todos os processos
[ ] Rate limiting no endpoint /send/
[ ] Health check endpoint melhorado
[ ] MessageProcessor singleton implementado
[ ] Session save otimizado (append-only messages)
[ ] NFSeEmissao.save() reduzido para 1 operacao
[ ] DEBUG=False no .env
[ ] ALLOWED_HOSTS configurado com dominio real
[ ] CSRF_TRUSTED_ORIGINS configurado
[ ] collectstatic executado
[ ] Logs redirecionados para journald (systemd)
[ ] Backup automatico do PostgreSQL (pg_dump cron)
```

---

## 13. ESTIMATIVA DE CUSTOS OPERACIONAIS

### OpenAI API

| Item | Calculo | Custo/mes |
|------|---------|-----------|
| Chamadas gpt-4o-mini | ~7.000/dia * 30 = 210.000/mes | |
| Input tokens (~500/call) | 210.000 * 500 = 105M tokens | ~$15.75 |
| Output tokens (~200/call) | 210.000 * 200 = 42M tokens | ~$25.20 |
| **Total OpenAI** | | **~$41/mes** |

*Precos gpt-4o-mini: $0.15/1M input, $0.60/1M output (2025)*

### Infraestrutura

| Item | Valor | Obs |
|------|-------|-----|
| VM 8GB/4vCPU | Depende do provedor | Oracle Cloud, DigitalOcean, Hetzner |
| Dominio + SSL | Gratis via Caddy (Let's Encrypt) | |
| BrasilAPI | Gratis | API publica |
| Evolution API | Self-hosted (incluso na VM) | |

---

## 14. PROXIMOS PASSOS APOS MVP

1. **Escala horizontal:** Separar Evolution API em VM dedicada quando atingir 50+ instancias WhatsApp
2. **Database:** Connection pooler (PgBouncer) se exceder 50 conexoes simultaneas
3. **Observabilidade:** Sentry para error tracking, Prometheus + Grafana para metricas
4. **Gateway real:** Substituir MockNFSeGateway por integracao Teknospeed
5. **Backup:** pg_dump diario com retencao de 30 dias
6. **CI/CD:** Pipeline de deploy automatizado (GitHub Actions)
