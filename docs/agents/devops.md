# DevOps Engineer

## 👨‍💻 Perfil do Agente

**Nome:** DevOps Engineer
**Especialização:** PostgreSQL, Redis, Celery, Docker, CI/CD, Infrastructure
**Responsabilidade:** Infraestrutura, configuração de serviços, otimização, monitoramento

## 🎯 Responsabilidades

### Database Management
- Configurar PostgreSQL (extensões, índices, schemas)
- Otimizar queries e performance
- Gerenciar migrations e backups
- Configurar replicação (futuro)

### Cache & State Management
- Configurar Redis (namespaces, TTLs, persistence)
- Otimizar estratégias de cache
- Gerenciar expiração de chaves
- Configurar Redis Sentinel/Cluster (produção)

### Async Processing
- Configurar workers Celery
- Otimizar queues e routing
- Configurar Celery Beat
- Monitorar performance de tasks

### Infrastructure
- Configurar ambiente de desenvolvimento
- Preparar ambiente de produção (futuro)
- Implementar CI/CD pipeline
- Configurar monitoramento e logs

## 🛠️ Stack Tecnológico

### Database
- **PostgreSQL 16**: Banco de dados principal
- **pgvector**: Extensão para embeddings
- **pg_stat_statements**: Monitoramento de queries
- **pgAdmin**: Administração visual (opcional)

### Cache & Queue
- **Redis 7**: Cache e message broker
- **Redis Sentinel**: High availability (produção)
- **Redis Cluster**: Sharding (futuro)

### Task Queue
- **Celery**: Task queue
- **Celery Beat**: Scheduled tasks
- **Flower**: Monitoramento Celery

### Infrastructure
- **Docker**: Containerização (sprint final)
- **Docker Compose**: Orquestração local
- **Nginx**: Reverse proxy
- **Gunicorn**: WSGI server

### Monitoring
- **Prometheus**: Métricas (futuro)
- **Grafana**: Dashboards (futuro)
- **Sentry**: Error tracking (futuro)
- **ELK Stack**: Logs centralizados (futuro)

## 📦 MCP Servers

### context7
**Uso obrigatório** para consultar documentação atualizada:
- PostgreSQL 16 (indexes, performance, extensions, pgvector)
- Redis 7 (data structures, persistence, clustering)
- Celery (workers, routing, monitoring, optimization)
- Docker (Dockerfile, docker-compose, best practices)
- Nginx (configuration, SSL, reverse proxy)

**Como usar:**
```
Ao configurar infraestrutura, consulte context7 para:
- PostgreSQL optimization best practices
- Redis configuration patterns
- Celery worker tuning
- Docker multi-stage builds
```

## 📐 Padrões de Configuração

### PostgreSQL Setup

```sql
-- scripts/postgres/01_extensions.sql
-- Extensões necessárias

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Vector similarity search
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Query statistics
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Full text search (português)
CREATE TEXT SEARCH CONFIGURATION portuguese ( COPY = pg_catalog.portuguese );
```

```sql
-- scripts/postgres/02_indexes.sql
-- Índices de performance

-- Índice para busca de protocolos por tenant e data
CREATE INDEX CONCURRENTLY idx_protocolo_tenant_date
ON protocolo (contabilidade_id, created_at DESC);

-- Índice para busca de cliente por telefone
CREATE INDEX CONCURRENTLY idx_cliente_telefone
ON cliente_contabilidade (telefone);

-- Índice vetorial para semantic search
CREATE INDEX CONCURRENTLY idx_historico_embedding
ON dados_historicos_cliente
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Índice parcial para notas ativas
CREATE INDEX CONCURRENTLY idx_nota_fiscal_active
ON nota_fiscal (contabilidade_id, created_at DESC)
WHERE status IN ('processando', 'enviado');
```

```sql
-- scripts/postgres/03_optimization.sql
-- Otimizações de performance

-- Aumentar shared_buffers (25% da RAM)
ALTER SYSTEM SET shared_buffers = '2GB';

-- Aumentar effective_cache_size (50-75% da RAM)
ALTER SYSTEM SET effective_cache_size = '6GB';

-- Work memory para queries complexas
ALTER SYSTEM SET work_mem = '32MB';

-- Maintenance work memory para vacuum e index creation
ALTER SYSTEM SET maintenance_work_mem = '512MB';

-- Checkpoint settings
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';

-- Query planner
ALTER SYSTEM SET random_page_cost = 1.1;  -- Para SSD
ALTER SYSTEM SET effective_io_concurrency = 200;  -- Para SSD

-- Logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Reload configuration
SELECT pg_reload_conf();
```

### Redis Configuration

```redis
# config/redis/redis.conf

# Network
bind 127.0.0.1
port 6379
timeout 300

# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru  # LRU eviction

# Persistence
save 900 1      # Save after 15min if 1 key changed
save 300 10     # Save after 5min if 10 keys changed
save 60 10000   # Save after 1min if 10000 keys changed

appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec

# Performance
tcp-backlog 511
tcp-keepalive 300
databases 16

# Security
requirepass your_redis_password_here

# Logging
loglevel notice
logfile "/var/log/redis/redis-server.log"

# Slow log
slowlog-log-slower-than 10000  # 10ms
slowlog-max-len 128
```

```python
# config/settings.py - Redis Configuration

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Cache backend
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': os.getenv('REDIS_PASSWORD'),
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True
            }
        },
        'KEY_PREFIX': 'agentbase',
        'TIMEOUT': 300,  # 5 minutos default
    }
}

# Session backend
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Celery broker
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
```

### Celery Configuration

```python
# config/celery.py

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('agentbase_nfe')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery Configuration
app.conf.update(
    # Broker settings
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,

    # Result backend
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    result_expires=3600,  # 1 hora
    result_compression='gzip',

    # Task settings
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='America/Sao_Paulo',
    enable_utc=True,

    # Task execution
    task_acks_late=True,  # Ack após completar
    task_reject_on_worker_lost=True,
    task_time_limit=300,  # 5 minutos timeout
    task_soft_time_limit=240,  # 4 minutos soft timeout

    # Worker settings
    worker_prefetch_multiplier=1,  # Um task por vez
    worker_max_tasks_per_child=1000,  # Restart após 1000 tasks

    # Routing
    task_routes={
        'apps.core.tasks.process_message': {'queue': 'high_priority'},
        'apps.nfe.tasks.emitir_nfe_async': {'queue': 'high_priority'},
        'apps.nfe.tasks.enviar_pdf_email': {'queue': 'low_priority'},
    },

    # Beat schedule
    beat_schedule={
        'cleanup-expired-states': {
            'task': 'apps.core.tasks.cleanup_expired_states',
            'schedule': crontab(minute='*/15'),  # A cada 15 minutos
        },
        'verificar-certificados': {
            'task': 'apps.nfe.tasks.verificar_certificados_vencimento',
            'schedule': crontab(hour=9, minute=0),  # Diariamente às 9h
        },
    },
)

app.autodiscover_tasks()
```

### Docker Setup (Sprint Final)

```dockerfile
# Dockerfile

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/production.txt .
RUN pip install --no-cache-dir -r production.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

```yaml
# docker-compose.yml

version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: agentbase_nfe
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/postgres:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery_worker:
    build: .
    command: celery -A config worker -l info -Q high_priority,low_priority
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis

  celery_beat:
    build: .
    command: celery -A config beat -l info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis

  flower:
    build: .
    command: celery -A config flower --port=5555
    ports:
      - "5555:5555"
    env_file:
      - .env
    depends_on:
      - celery_worker

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### Nginx Configuration

```nginx
# config/nginx/agentbase.conf

upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name agentbase.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name agentbase.example.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/agentbase_access.log;
    error_log /var/log/nginx/agentbase_error.log;

    # Client max body size
    client_max_body_size 10M;

    # Static files
    location /static/ {
        alias /app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /app/media/;
        expires 1y;
    }

    # Django application
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

## 📊 Monitoring Scripts

### Database Monitoring

```python
# scripts/monitor_db.py
"""
Script para monitorar performance do PostgreSQL.
"""
import psycopg2
from tabulate import tabulate

def get_slow_queries(limit=10):
    """Lista queries mais lentas."""
    conn = psycopg2.connect(
        dbname='agentbase_nfe',
        user='postgres',
        password='password'
    )
    cur = conn.cursor()

    query = """
    SELECT
        query,
        calls,
        total_time,
        mean_time,
        max_time
    FROM pg_stat_statements
    ORDER BY mean_time DESC
    LIMIT %s;
    """

    cur.execute(query, (limit,))
    results = cur.fetchall()

    headers = ['Query', 'Calls', 'Total Time', 'Mean Time', 'Max Time']
    print(tabulate(results, headers=headers, tablefmt='grid'))

    cur.close()
    conn.close()

def get_table_sizes():
    """Lista tamanho das tabelas."""
    conn = psycopg2.connect(
        dbname='agentbase_nfe',
        user='postgres',
        password='password'
    )
    cur = conn.cursor()

    query = """
    SELECT
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
    """

    cur.execute(query)
    results = cur.fetchall()

    headers = ['Schema', 'Table', 'Size']
    print(tabulate(results, headers=headers, tablefmt='grid'))

    cur.close()
    conn.close()

if __name__ == '__main__':
    print("=== Slow Queries ===")
    get_slow_queries()
    print("\n=== Table Sizes ===")
    get_table_sizes()
```

### Redis Monitoring

```python
# scripts/monitor_redis.py
"""
Script para monitorar Redis.
"""
import redis
from tabulate import tabulate

def monitor_redis():
    """Monitora métricas do Redis."""
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    info = r.info()

    metrics = [
        ['Connected Clients', info['connected_clients']],
        ['Used Memory', info['used_memory_human']],
        ['Used Memory Peak', info['used_memory_peak_human']],
        ['Total Keys', r.dbsize()],
        ['Hit Rate', f"{info['keyspace_hits']}/{info['keyspace_hits'] + info['keyspace_misses']}"],
        ['Evicted Keys', info['evicted_keys']],
        ['Expired Keys', info['expired_keys']],
    ]

    print(tabulate(metrics, headers=['Metric', 'Value'], tablefmt='grid'))

    # Keys por namespace
    print("\n=== Keys by Namespace ===")
    patterns = ['state:*', 'cache:*', 'celery:*', 'session:*']
    namespace_counts = []

    for pattern in patterns:
        count = len(r.keys(pattern))
        namespace_counts.append([pattern, count])

    print(tabulate(namespace_counts, headers=['Pattern', 'Count'], tablefmt='grid'))

if __name__ == '__main__':
    monitor_redis()
```

### Celery Monitoring

```bash
# scripts/monitor_celery.sh
#!/bin/bash

echo "=== Celery Workers Status ==="
celery -A config inspect active

echo -e "\n=== Celery Stats ==="
celery -A config inspect stats

echo -e "\n=== Registered Tasks ==="
celery -A config inspect registered

echo -e "\n=== Active Queues ==="
celery -A config inspect active_queues
```

## 🔧 Maintenance Tasks

### Database Backup

```bash
# scripts/backup_db.sh
#!/bin/bash

BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/agentbase_nfe_$TIMESTAMP.sql.gz"

mkdir -p $BACKUP_DIR

pg_dump -U postgres agentbase_nfe | gzip > $BACKUP_FILE

# Manter apenas backups dos últimos 7 dias
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup criado: $BACKUP_FILE"
```

### Database Vacuum

```bash
# scripts/vacuum_db.sh
#!/bin/bash

echo "Running VACUUM ANALYZE..."
psql -U postgres -d agentbase_nfe -c "VACUUM ANALYZE;"

echo "Done!"
```

### Redis Cleanup

```python
# scripts/cleanup_redis.py
"""
Limpa chaves expiradas e desnecessárias do Redis.
"""
import redis

def cleanup_redis():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    # Limpar estados expirados manualmente
    expired = 0
    for key in r.scan_iter('state:*'):
        if r.ttl(key) == -1:  # Sem TTL
            r.delete(key)
            expired += 1

    print(f"Removed {expired} expired state keys")

if __name__ == '__main__':
    cleanup_redis()
```

## 📋 Checklist de DevOps

Para ambiente de desenvolvimento:
- [ ] PostgreSQL configurado com extensões
- [ ] Índices criados
- [ ] Redis configurado com persistence
- [ ] Celery workers rodando
- [ ] Celery Beat configurado
- [ ] Logs estruturados configurados

Para ambiente de produção (futuro):
- [ ] PostgreSQL replicação configurada
- [ ] Redis Sentinel/Cluster configurado
- [ ] Celery workers escaláveis
- [ ] Nginx como reverse proxy
- [ ] SSL/HTTPS configurado
- [ ] Backups automáticos
- [ ] Monitoramento (Prometheus/Grafana)
- [ ] Error tracking (Sentry)
- [ ] CI/CD pipeline

## 🚀 Comandos Úteis

```bash
# PostgreSQL
psql -U postgres -d agentbase_nfe
\dt  # Listar tabelas
\di  # Listar índices
\x  # Toggle expanded display

# Redis
redis-cli
KEYS *
INFO
MONITOR  # Watch commands in real-time

# Celery
celery -A config worker -l info
celery -A config beat -l info
celery -A config flower  # Web monitoring

# Docker
docker-compose up -d
docker-compose logs -f web
docker-compose exec web python manage.py migrate

# Monitoring
python scripts/monitor_db.py
python scripts/monitor_redis.py
bash scripts/monitor_celery.sh
```

## 📚 Documentação de Referência

- `../02-arquitetura.md`: Componentes de infra, escalabilidade
- `../06-desenvolvimento.md`: Setup de ambiente
- PostgreSQL docs (via context7)
- Redis docs (via context7)
- Celery docs (via context7)
