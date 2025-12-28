# Documentação do AgentBase NFe

Bem-vindo à documentação oficial do projeto AgentBase NFe.

## Índice da Documentação

### 1. [Introdução](01-introducao.md)
Visão geral do projeto, problema que resolve, atores principais e fluxo básico de uso.

**Conteúdo:**
- Visão geral do sistema
- Problema que resolve
- Solução proposta
- Atores principais (Cliente e Contador)
- Sistemas integrados
- Fluxo básico de uso
- Tecnologias utilizadas
- Benefícios

### 2. [Arquitetura](02-arquitetura.md)
Detalhes da arquitetura do sistema usando modelo C4.

**Conteúdo:**
- Diagrama C4 Nível 1 (Contexto)
- Diagrama C4 Nível 2 (Containers)
- Componentes técnicos detalhados
- Comunicação entre componentes
- Estratégias de escalabilidade
- Segurança e proteção de dados
- Monitoramento e observabilidade
- Estimativa de recursos

### 3. [Padrões de Código](03-padroes-codigo.md)
Guidelines e padrões de desenvolvimento do projeto.

**Conteúdo:**
- Princípios gerais (simplicidade, sem over engineering)
- Convenções de código (inglês/português, aspas, PEP8)
- Estrutura de apps Django
- Nomenclatura (models, views, services)
- Padrões de Django (models, views, services, signals)
- Frontend (templates, design system)
- Boas práticas (database, segurança, performance)
- Logs estruturados
- O que NÃO fazer

### 4. [Estrutura do Projeto](04-estrutura-projeto.md)
Organização detalhada de apps, models e serviços.

**Conteúdo:**
- Organização em apps Django
- App Account (autenticação)
- App Core (protocolos, state machine, IA)
- App Contabilidade (tenants e clientes)
- App NFe (notas fiscais e integrações)
- Estrutura completa de diretórios
- Redis (gerenciamento de estados)
- PostgreSQL (schemas e extensões)
- Integração com Tecnospeed
- Multi-tenant e isolamento

### 5. [Fluxos Principais](05-fluxos-principais.md)
Detalhamento dos fluxos de negócio do sistema.

**Conteúdo:**
- Fluxo de emissão de nota (happy path)
- Fluxo de dados incompletos
- Fluxo de cancelamento
- Fluxo de timeout/expiração
- Fluxo de erro e retry
- Fluxo de busca semântica
- Decisões de design (TTLs, retry strategy, priorização)

### 6. [Desenvolvimento](06-desenvolvimento.md)
Guia prático para desenvolver no projeto.

**Conteúdo:**
- Configuração do ambiente
- Pré-requisitos e instalação
- Estrutura de desenvolvimento
- Criando models, views, services, tasks
- Comandos úteis (Django, Celery, PostgreSQL, Redis)
- Debugging (logs, breakpoints, debug toolbar)
- Testando localmente
- Padrões de commit
- Deploy (checklist futuro)
- Recursos úteis

## Navegação Rápida

### Para Novos Desenvolvedores
1. Comece pela [Introdução](01-introducao.md)
2. Entenda a [Arquitetura](02-arquitetura.md)
3. Leia os [Padrões de Código](03-padroes-codigo.md)
4. Configure seu ambiente seguindo [Desenvolvimento](06-desenvolvimento.md)

### Para Arquitetos/Tech Leads
1. [Arquitetura](02-arquitetura.md)
2. [Estrutura do Projeto](04-estrutura-projeto.md)
3. [Fluxos Principais](05-fluxos-principais.md)

### Para Product Managers
1. [Introdução](01-introducao.md)
2. [Fluxos Principais](05-fluxos-principais.md)

## Visão Geral Rápida

### O que é o AgentBase NFe?

Sistema SaaS que permite emissão de Notas Fiscais de Serviço (NFSe) através do WhatsApp, usando Inteligência Artificial para extrair dados de mensagens naturais.

### Stack Tecnológica

- **Backend**: Django 5.0 (Python)
- **Frontend**: Django Templates + Bootstrap
- **Database**: PostgreSQL 16 + pgvector
- **Cache**: Redis 7
- **Tasks**: Celery
- **IA**: OpenAI GPT-4o-mini
- **Integrações**: WhatsApp (WAHA), Tecnospeed

### Fluxo Básico

```
Cliente envia mensagem WhatsApp
    ↓
IA extrai dados (valor, tomador, descrição)
    ↓
Sistema busca histórico do cliente
    ↓
Sistema gera prévia e pede confirmação
    ↓
Cliente confirma
    ↓
Sistema emite nota fiscal
    ↓
Cliente recebe PDF via WhatsApp
```

### Apps Django

- **account**: Autenticação e perfis
- **core**: Mensagens, protocolos, state machine, IA
- **contabilidade**: Tenants e clientes (multi-tenant)
- **nfe**: Notas fiscais e integrações

### Princípios do Projeto

1. **Simplicidade**: Sem over engineering
2. **Django-way**: Usar recursos nativos sempre que possível
3. **Multi-tenant**: Isolamento completo entre contabilidades
4. **Assíncrono**: Operações demoradas em background (Celery)
5. **Inteligente**: IA aprende com histórico do cliente

## Contribuindo

### Regras Gerais

- Código em **inglês**
- Interface em **português brasileiro**
- Seguir **PEP8**
- Usar **aspas simples**
- **Não** fazer over engineering
- **Não** adicionar funcionalidades não solicitadas

### Workflow

```bash
# 1. Criar branch
git checkout -b feature/minha-feature

# 2. Desenvolver e testar
python manage.py test

# 3. Commit
git commit -m "feat: descrição da feature"

# 4. Push
git push origin feature/minha-feature

# 5. Abrir Pull Request
```

## Suporte

Para dúvidas sobre o projeto:

1. Consulte esta documentação
2. Veja os arquivos de escopo na raiz (`escopo-app.md`, `c4_nivel*.md`, etc.)
3. Entre em contato com o time de desenvolvimento

## Changelog

### v1.0.0 (Planejado)
- Emissão de NFSe via WhatsApp
- Extração de dados via IA
- Dashboard para contabilidades
- Multi-tenant
- Integração com Tecnospeed

---

**Última atualização**: Dezembro 2025
**Versão da documentação**: 1.0
