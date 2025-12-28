# Agentes de IA - AgentBase NFe

Este diretório contém os agentes especializados de IA para desenvolvimento do projeto AgentBase NFe. Cada agente é um especialista em uma área específica do stack tecnológico.

## 📋 Índice de Agentes

### 1. [Backend Django Developer](backend-django.md)
**Especialização:** Django 5.0, Python 3.11+, PostgreSQL, Celery, Redis

**Quando usar:**
- Criar ou modificar models do Django
- Implementar views, serializers e APIs
- Desenvolver services de negócio
- Configurar tasks do Celery
- Implementar lógica de multi-tenant
- Trabalhar com state machine e Redis
- Otimizar queries e performance do banco

**MCP Servers:** `context7` (documentação Django, Python, PostgreSQL, Celery)

---

### 2. [Frontend Developer](frontend.md)
**Especialização:** Django Templates, Bootstrap 5, JavaScript

**Quando usar:**
- Criar ou modificar templates Django
- Implementar componentes de UI com Bootstrap 5
- Desenvolver interfaces responsivas
- Trabalhar com formulários Django
- Implementar JavaScript para interatividade
- Aplicar o design system do projeto (gradientes, dark theme)

**MCP Servers:** `context7` (documentação Django Templates, Bootstrap, JavaScript)

---

### 3. [AI/ML Engineer](ai-ml.md)
**Especialização:** OpenAI API, pgvector, Semantic Search, NLP

**Quando usar:**
- Implementar extração de dados via IA
- Desenvolver validação inteligente de dados
- Trabalhar com embeddings e pgvector
- Implementar busca semântica
- Otimizar prompts para GPT-4o-mini
- Melhorar confidence scores
- Integrar contexto histórico do cliente

**MCP Servers:** `context7` (documentação OpenAI, pgvector, machine learning)

---

### 4. [Integration Specialist](integration.md)
**Especialização:** APIs externas, WhatsApp (WAHA), Tecnospeed, SOAP/XML

**Quando usar:**
- Implementar webhooks do WhatsApp
- Integrar com gateway Tecnospeed
- Trabalhar com certificados digitais
- Desenvolver clients de APIs externas
- Implementar retry logic e error handling
- Criar mocks para desenvolvimento (FakeClients)

**MCP Servers:** `context7` (documentação APIs, SOAP, XML, webhooks)

---

### 5. [QA Engineer / Tester](qa-tester.md)
**Especialização:** Testes automatizados, Playwright, pytest, Django tests

**Quando usar:**
- Criar testes end-to-end
- Validar fluxos de usuário
- Testar integrações
- Verificar design e responsividade
- Testar multi-tenant isolation
- Validar state machine transitions
- Realizar testes de regressão

**MCP Servers:** `playwright` (testes E2E), `context7` (documentação pytest, Django testing)

---

### 6. [DevOps Engineer](devops.md)
**Especialização:** PostgreSQL, Redis, Celery, Docker, CI/CD

**Quando usar:**
- Configurar PostgreSQL (extensões, índices, schemas)
- Configurar Redis (namespaces, TTLs)
- Otimizar workers Celery
- Implementar estratégias de cache
- Configurar monitoramento e logs
- Trabalhar com ambiente de desenvolvimento

**MCP Servers:** `context7` (documentação PostgreSQL, Redis, Celery, Docker)

---

## 🎯 Diretrizes Gerais para Todos os Agentes

### Padrões de Código
- **Idioma**: Código em inglês, UI/docs em português brasileiro
- **Quotes**: Sempre aspas simples `'texto'`
- **Line length**: 120 caracteres
- **Style**: PEP8 para Python

### Princípios
1. **Simplicidade**: Sem over-engineering
2. **Django-way**: Usar recursos nativos do Django
3. **Multi-tenant**: Sempre filtrar por `contabilidade`
4. **Async**: Operações demoradas em Celery
5. **Cache**: Redis para dados frequentes (TTL 5min)
6. **Logs**: Estruturados em JSON

### Commits
Seguir Conventional Commits:
```
feat: adiciona funcionalidade X
fix: corrige bug Y
docs: atualiza documentação
refactor: refatora componente Z
test: adiciona testes para W
chore: atualiza dependências
```

## 🔄 Workflow de Desenvolvimento

### 1. Análise de Requisito
Qualquer agente pode analisar requisitos e definir escopo.

### 2. Implementação
- **Backend**: Backend Django Developer
- **Frontend**: Frontend Developer
- **IA**: AI/ML Engineer
- **Integrações**: Integration Specialist

### 3. Testes
- **QA Engineer**: Valida implementação com testes E2E

### 4. Deploy (futuro)
- **DevOps Engineer**: Prepara ambiente e deploy

## 📚 Documentação de Referência

Todos os agentes devem consultar:
- `../01-introducao.md` - Visão geral do sistema
- `../02-arquitetura.md` - Arquitetura C4
- `../03-padroes-codigo.md` - Padrões e guidelines
- `../04-estrutura-projeto.md` - Estrutura de apps
- `../05-fluxos-principais.md` - Fluxos de negócio
- `../06-desenvolvimento.md` - Guia de desenvolvimento
- `../CLAUDE.md` - Guia rápido para Claude Code

## 🛠️ MCP Servers Utilizados

### context7
Fornece documentação atualizada das tecnologias:
- Django 5.0
- Python 3.11
- PostgreSQL 16
- Redis 7
- Celery
- OpenAI API
- Bootstrap 5
- E outras tecnologias do stack

### playwright
Fornece capacidade de:
- Executar testes E2E no navegador
- Validar fluxos de usuário
- Verificar design e responsividade
- Capturar screenshots e vídeos
- Testar em múltiplos navegadores

## 💡 Dicas de Uso

### Escolhendo o Agente Certo

**Para features backend (models, services, APIs):**
→ Backend Django Developer

**Para features frontend (templates, UI, forms):**
→ Frontend Developer

**Para features de IA (extração, validação, busca):**
→ AI/ML Engineer

**Para integrações externas (WhatsApp, Tecnospeed):**
→ Integration Specialist

**Para validar qualquer implementação:**
→ QA Engineer

**Para configuração de infra (DB, cache, workers):**
→ DevOps Engineer

### Colaboração entre Agentes

Os agentes podem trabalhar em sequência:
1. Backend Developer cria API
2. Frontend Developer consome API
3. QA Engineer valida integração

Ou em paralelo:
- Backend Developer + AI/ML Engineer (feature com IA)
- Frontend Developer + QA Engineer (UI com validação)

## 🚀 Começando

1. Leia a documentação relevante em `/docs`
2. Escolha o agente apropriado para sua tarefa
3. Configure o ambiente conforme `06-desenvolvimento.md`
4. Implemente seguindo os padrões do agente
5. Valide com QA Engineer antes de commit
