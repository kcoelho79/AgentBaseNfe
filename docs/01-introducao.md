# Introdução ao AgentBase NFe

## Visão Geral

O **AgentBase NFe** é um sistema SaaS (Software as a Service) desenvolvido para atender escritórios de contabilidade na emissão automatizada de Notas Fiscais de Serviço Eletrônicas (NFSe) através do WhatsApp.

## Problema que Resolve

Microempreendedores e MEIs atendidos por escritórios de contabilidade frequentemente têm dificuldade em emitir notas fiscais devido a:
- Falta de conhecimento técnico sobre o processo
- Interfaces complexas de sistemas tradicionais
- Necessidade de acesso a computadores

## Solução

O AgentBase NFe permite que os clientes da contabilidade emitam notas fiscais simplesmente enviando uma mensagem via WhatsApp, como:

```
"Emitir nota de 150 reais para empresa XYZ"
```

O sistema utiliza Inteligência Artificial (GPT-4o-mini) para:
- Extrair dados da mensagem (valor, tomador, descrição)
- Buscar informações históricas do cliente
- Validar os dados extraídos
- Gerar a nota fiscal automaticamente

## Atores Principais

### 1. Cliente da Contabilidade
- Microempreendedor ou MEI
- Interage apenas via WhatsApp
- Não precisa de conhecimento técnico sobre notas fiscais

### 2. Contador/Contabilidade (Tenant)
- Escritório de contabilidade assinante do sistema
- Gerencia múltiplos clientes
- Configura certificados digitais
- Monitora emissões através do dashboard web

## Sistemas Integrados

### WhatsApp Business API (via WAHA)
- Interface de comunicação com os clientes
- Recebe e envia mensagens
- Webhook para notificações em tempo real

### OpenAI API (GPT-4o-mini)
- Extração inteligente de dados
- Validação de informações
- Busca semântica em histórico

### Tecnospeed Gateway
- Gateway de emissão de NFSe
- Integração com prefeituras
- Validação de certificados digitais
- Geração de XML e PDF

### Serviço de Email
- Notificações por email
- Envio de PDFs das notas emitidas

## Fluxo Básico de Uso

1. Cliente envia mensagem pelo WhatsApp
2. Sistema extrai dados usando IA
3. Sistema busca histórico do cliente para completar informações
4. Sistema gera prévia da nota e pede confirmação
5. Cliente confirma
6. Sistema emite a nota fiscal
7. Cliente recebe PDF via WhatsApp e email

## Características Principais

- **Multi-tenant**: Cada escritório de contabilidade é um tenant isolado
- **Processamento assíncrono**: Emissões processadas em background
- **Inteligência artificial**: Extração e validação automática de dados
- **Busca semântica**: Aprende com histórico do cliente
- **Estados de conversa**: Gerencia diálogos complexos com clientes

## Tecnologias Utilizadas

- **Backend**: Django 5.0 (Python)
- **Frontend**: Django Template Language + Bootstrap
- **Banco de dados**: PostgreSQL 16 + pgvector
- **Cache/Estado**: Redis 7
- **Filas**: Celery
- **IA**: OpenAI GPT-4o-mini
- **Integrações**: WhatsApp API (WAHA), Tecnospeed

## Benefícios

### Para o Cliente
- Emissão simplificada via WhatsApp
- Sem necessidade de aprender sistemas complexos
- Recebimento automático de PDFs

### Para a Contabilidade
- Redução de atendimentos manuais
- Automatização de processos repetitivos
- Dashboard centralizado de gestão
- Histórico completo de emissões
