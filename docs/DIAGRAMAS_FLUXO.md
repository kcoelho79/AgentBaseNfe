# Diagramas de Fluxo - AgentNFe

Este documento contém os diagramas Mermaid para visualização dos fluxos do sistema.

---

## 📊 Diagrama 1: Máquina de Estados

Visualização completa da máquina de estados e transições.

```mermaid
stateDiagram-v2
    [*] --> coleta: Nova mensagem
    
    coleta --> dados_incompletos: IA extrai (parcial)
    dados_incompletos --> dados_incompletos: Mais dados (loop)
    dados_incompletos --> dados_completos: Campos OK
    
    dados_completos --> aguardando_confirmacao: Exibe espelho
    
    aguardando_confirmacao --> processando: Usuário: SIM
    aguardando_confirmacao --> cancelado_usuario: Usuário: NÃO
    
    processando --> aprovado: Gateway: sucesso
    processando --> rejeitado: Gateway: rejeição
    processando --> erro: Gateway: erro técnico
    
    coleta --> expirado: TTL > 1h
    dados_incompletos --> expirado: TTL > 1h
    aguardando_confirmacao --> expirado: TTL > 1h
    
    aprovado --> [*]
    rejeitado --> [*]
    erro --> [*]
    cancelado_usuario --> [*]
    expirado --> [*]
    
    note right of coleta
        SNAPSHOT: manual
        - sessao_id gerado
        - telefone vinculado
        - métricas zeradas
    end note
    
    note right of dados_completos
        SNAPSHOT: data_complete
        - cnpj_status: validated
        - valor_status: validated
        - descricao_status: validated
        - data_complete: True
    end note
    
    note right of processando
        SNAPSHOT: confirmed
        - Cria NFSeEmissao
        - Cria/busca ClienteTomador
        - Envia para gateway
    end note
    
    note right of aprovado
        SNAPSHOT: success
        - Cria NFSeProcessada
        - Armazena XML/PDF
        - Registra protocolo
    end note
```

---

## 🔄 Diagrama 2: Fluxo Completo de Dados

Visualização end-to-end do processamento de mensagens.

```mermaid
graph TB
    subgraph WhatsApp["📱 WhatsApp"]
        USER[Usuário envia mensagem]
    end
    
    subgraph MessageProcessor["🔄 MessageProcessor"]
        RECV[Recebe: telefone + mensagem]
        RECV --> GET_SESSION{Sessão existe?}
        GET_SESSION -->|Não| CREATE[SessionManager.create_session]
        GET_SESSION -->|Sim| LOAD[SessionManager.get_session]
        CREATE --> SESSION[Session Pydantic]
        LOAD --> SESSION
        
        SESSION --> ADD_USER[add_user_message]
        ADD_USER --> CHECK_STATE{Estado?}
        
        CHECK_STATE -->|aguardando_confirmacao| CONFIRM[_handle_confirmacao]
        CHECK_STATE -->|outros| EXTRACT[_processar_coleta]
    end
    
    subgraph AIExtraction["🤖 Extração IA"]
        EXTRACT --> AI[AIExtractor.parse]
        AI --> OPENAI[OpenAI API gpt-4o-mini]
        OPENAI --> PARSED[DadosNFSe extraídos]
        PARSED --> MERGE[invoice_data.merge]
    end
    
    subgraph Validation["✅ Validação"]
        MERGE --> VALIDATE{data_complete?}
        VALIDATE -->|Não| INCOMPLETE[Estado: dados_incompletos]
        VALIDATE -->|Sim| COMPLETE[Estado: dados_completos]
        COMPLETE --> WAIT[Estado: aguardando_confirmacao]
        
        INCOMPLETE --> MSG_INC[ResponseBuilder.build_dados_incompletos]
        WAIT --> MSG_ESP[ResponseBuilder.build_espelho]
    end
    
    subgraph Confirmation["🎯 Confirmação"]
        CONFIRM --> USER_CHOICE{Resposta?}
        USER_CHOICE -->|SIM| PROC[Estado: processando]
        USER_CHOICE -->|NÃO| CANCEL[Estado: cancelado_usuario]
        USER_CHOICE -->|Inválido| RETRY[Pede SIM/NÃO novamente]
    end
    
    subgraph Persistence["💾 Persistência SQLite"]
        PROC --> SAVE[SessionManager.save_session]
        CANCEL --> SAVE
        INCOMPLETE --> SAVE
        WAIT --> SAVE
        
        SAVE --> DB_SNAPSHOT[(SessionSnapshot)]
        SAVE --> DB_MSG[(SessionMessage)]
        
        DB_SNAPSHOT -.->|reason| R1[manual]
        DB_SNAPSHOT -.->|reason| R2[data_complete]
        DB_SNAPSHOT -.->|reason| R3[confirmed]
        DB_SNAPSHOT -.->|reason| R4[cancelled]
    end
    
    subgraph NFSeEmission["📄 Emissão NFSe"]
        PROC --> EMISSAO[NFSeEmissaoService.emitir_de_sessao]
        EMISSAO --> FIND_PREST[Busca Prestador por telefone]
        EMISSAO --> FIND_TOM[Busca/Cria ClienteTomador]
        
        FIND_TOM --> RECEITA[ReceitaFederalService.consultar_cnpj]
        RECEITA --> BRASIL_API[BrasilAPI]
        BRASIL_API --> TOM_DB[(ClienteTomador)]
        
        FIND_PREST --> BUILD[NFSeBuilder.build]
        FIND_TOM --> BUILD
        BUILD --> GATEWAY[MockNFSeGateway.enviar]
        
        GATEWAY --> DB_EMISSAO[(NFSeEmissao)]
        GATEWAY --> WEBHOOK_SIM{Simulação: sucesso?}
        WEBHOOK_SIM -->|Sim| DB_PROC[(NFSeProcessada)]
        WEBHOOK_SIM -->|Não| ERROR[Estado: erro]
    end
    
    subgraph Response["📤 Resposta"]
        MSG_INC --> SEND[Envia resposta WhatsApp]
        MSG_ESP --> SEND
        RETRY --> SEND
        DB_PROC --> MSG_SUCCESS[ResponseBuilder.build_nfse_emitida]
        MSG_SUCCESS --> SEND
        CANCEL --> MSG_CANCEL[ResponseBuilder.build_cancelado]
        MSG_CANCEL --> SEND
    end
    
    USER --> RECV
    SEND --> USER
    
    style DB_SNAPSHOT fill:#e1f5ff,stroke:#0066cc
    style DB_MSG fill:#e1f5ff,stroke:#0066cc
    style DB_EMISSAO fill:#ffe1e1,stroke:#cc0000
    style DB_PROC fill:#ffe1e1,stroke:#cc0000
    style TOM_DB fill:#ffe1e1,stroke:#cc0000
    style OPENAI fill:#fff4e1,stroke:#ff9900
    style BRASIL_API fill:#fff4e1,stroke:#ff9900
```

---

## 🏗️ Diagrama 3: Arquitetura de Componentes

Visão das camadas e responsabilidades.

```mermaid
graph TB
    subgraph External["🌐 Serviços Externos"]
        WA[WhatsApp Business API]
        OPENAI_EXT[OpenAI API]
        BRASIL[BrasilAPI Receita Federal]
        GATEWAY_EXT[TecnoSpeed Gateway NFSe]
    end
    
    subgraph Interface["📱 Interface Layer"]
        WEBHOOK[Webhook Endpoint<br/>/whatsapp/webhook/]
    end
    
    subgraph Processing["⚙️ Processing Layer"]
        MP[MessageProcessor<br/>Orquestrador principal]
        SM[SessionManager<br/>Gerencia sessões Redis]
        EXT[AIExtractor<br/>Extração com IA]
        RB[ResponseBuilder<br/>Formata respostas]
    end
    
    subgraph Business["💼 Business Logic"]
        EMISSAO[NFSeEmissaoService<br/>Orquestra emissão]
        BUILDER[NFSeBuilder<br/>Monta payload XML]
        RF[ReceitaFederalService<br/>Consulta CNPJ]
        MOCK[MockNFSeGateway<br/>Simula processamento]
    end
    
    subgraph Data["💾 Data Layer"]
        REDIS[(Redis<br/>Sessões ativas)]
        SQLITE[(SQLite<br/>Persistência)]
    end
    
    subgraph Models["📦 Django Models"]
        SS[SessionSnapshot]
        SM_MODEL[SessionMessage]
        EMIS[NFSeEmissao]
        PROC[NFSeProcessada]
        TOM[ClienteTomador]
        EMP[Empresa]
    end
    
    WA --> WEBHOOK
    WEBHOOK --> MP
    
    MP --> SM
    MP --> EXT
    MP --> RB
    
    SM --> REDIS
    SM --> SS
    SM --> SM_MODEL
    
    EXT --> OPENAI_EXT
    
    MP --> EMISSAO
    EMISSAO --> BUILDER
    EMISSAO --> RF
    EMISSAO --> MOCK
    
    RF --> BRASIL
    RF --> TOM
    
    MOCK --> GATEWAY_EXT
    MOCK --> EMIS
    MOCK --> PROC
    
    SS --> SQLITE
    SM_MODEL --> SQLITE
    EMIS --> SQLITE
    PROC --> SQLITE
    TOM --> SQLITE
    EMP --> SQLITE
    
    BUILDER --> EMP
    
    RB --> WA
    
    style REDIS fill:#ff6b6b,stroke:#c92a2a
    style SQLITE fill:#4dabf7,stroke:#1971c2
    style OPENAI_EXT fill:#ffd43b,stroke:#f59f00
    style BRASIL fill:#51cf66,stroke:#2f9e44
    style GATEWAY_EXT fill:#ff922b,stroke:#e8590c
```

---

## 🔐 Diagrama 4: Segurança Multi-Tenant

Isolamento de dados por contabilidade.

```mermaid
graph TB
    subgraph Tenant1["🏢 Contabilidade A"]
        USER1[Usuário Admin A]
        EMP1A[Empresa 1A]
        EMP1B[Empresa 2A]
        USR_EMP1A[UsuarioEmpresa 1A<br/>Tel: +5511111111111]
        USR_EMP1B[UsuarioEmpresa 2A<br/>Tel: +5511222222222]
    end
    
    subgraph Tenant2["🏢 Contabilidade B"]
        USER2[Usuário Admin B]
        EMP2A[Empresa 1B]
        USR_EMP2A[UsuarioEmpresa 1B<br/>Tel: +5511333333333]
    end
    
    subgraph Sessions["💬 Sessões WhatsApp"]
        SESS1[Sessão: +5511111111111<br/>Estado: dados_completos]
        SESS2[Sessão: +5511222222222<br/>Estado: aguardando_confirmacao]
        SESS3[Sessão: +5511333333333<br/>Estado: coleta]
    end
    
    subgraph NFSe["📄 NFSe Emitidas"]
        NFSE1[NFSe 001<br/>Prestador: Empresa 1A<br/>Tomador: Cliente X]
        NFSE2[NFSe 002<br/>Prestador: Empresa 1B<br/>Tomador: Cliente Y]
    end
    
    subgraph Filters["🔒 Filtros de Segurança"]
        FILTER_SESS[SessionSnapshot.filter<br/>telefone__in=telefones_contab]
        FILTER_NFSE[NFSeEmissao.filter<br/>prestador__contabilidade=contab]
    end
    
    USER1 --> EMP1A
    USER1 --> EMP1B
    EMP1A --> USR_EMP1A
    EMP1B --> USR_EMP1B
    
    USER2 --> EMP2A
    EMP2A --> USR_EMP2A
    
    USR_EMP1A -.->|WhatsApp| SESS1
    USR_EMP1B -.->|WhatsApp| SESS2
    USR_EMP2A -.->|WhatsApp| SESS3
    
    SESS1 --> NFSE1
    SESS3 --> NFSE2
    
    EMP1A --> NFSE1
    EMP2A --> NFSE2
    
    USER1 -.->|Visualiza apenas| FILTER_SESS
    FILTER_SESS -.->|Retorna| SESS1
    FILTER_SESS -.->|Retorna| SESS2
    FILTER_SESS -.->|Bloqueia| SESS3
    
    USER1 -.->|Visualiza apenas| FILTER_NFSE
    FILTER_NFSE -.->|Retorna| NFSE1
    FILTER_NFSE -.->|Bloqueia| NFSE2
    
    style SESS1 fill:#d0f4de,stroke:#52b788
    style SESS2 fill:#fff1b8,stroke:#f4a261
    style SESS3 fill:#ffcccc,stroke:#e76f51
    style FILTER_SESS fill:#ffe5e5,stroke:#ff6b6b
    style FILTER_NFSE fill:#ffe5e5,stroke:#ff6b6b
```

---

## 📊 Diagrama 5: Modelo de Dados Simplificado

Relacionamentos entre entidades principais.

```mermaid
erDiagram
    Contabilidade ||--o{ Empresa : possui
    Contabilidade ||--o{ User : tem_usuarios
    
    Empresa ||--o{ UsuarioEmpresa : vincula
    Empresa ||--o{ NFSeEmissao : emite_como_prestador
    Empresa ||--o{ Certificado : possui
    
    User ||--o{ UsuarioEmpresa : pode_acessar
    
    UsuarioEmpresa ||--o{ SessionSnapshot : inicia_sessoes
    
    SessionSnapshot ||--o{ SessionMessage : contem
    SessionSnapshot ||--o| NFSeEmissao : gera
    
    NFSeEmissao ||--o| NFSeProcessada : resulta_em
    NFSeEmissao }o--|| ClienteTomador : para
    
    Contabilidade {
        int id PK
        string nome
        string slug
        bool is_active
    }
    
    Empresa {
        int id PK
        int contabilidade_id FK
        string razao_social
        string cpf_cnpj
        bool is_active
    }
    
    UsuarioEmpresa {
        int id PK
        int empresa_id FK
        string nome
        string telefone UK
        bool is_active
    }
    
    SessionSnapshot {
        int id PK
        string sessao_id UK
        string telefone
        string estado
        bool data_complete
        datetime session_created_at
    }
    
    SessionMessage {
        int id PK
        int session_id FK
        string role
        text content
        datetime timestamp
        int order
    }
    
    NFSeEmissao {
        int id PK
        int session_id FK
        int prestador_id FK
        int tomador_id FK
        string id_integracao UK
        string status
        decimal valor_servico
        datetime created_at
    }
    
    NFSeProcessada {
        int id PK
        int emissao_id FK
        string numero
        string chave
        string protocolo
        int c_stat
        date data_emissao
        string url_pdf
        string url_xml
    }
    
    ClienteTomador {
        int id PK
        string cnpj UK
        string razao_social
        string cidade
        string estado
        datetime created_at
    }
```

---

## 🎨 Legenda de Cores

### Nos Diagramas de Fluxo:
- 🔵 **Azul claro** (`#e1f5ff`): Persistência principal (SessionSnapshot, SessionMessage)
- 🔴 **Vermelho claro** (`#ffe1e1`): Dados NFSe (NFSeEmissao, NFSeProcessada, ClienteTomador)
- 🟡 **Amarelo claro** (`#fff4e1`): APIs externas (OpenAI, BrasilAPI)

### Nos Diagramas de Estados:
- 🟢 **Verde**: Estados de sucesso (aprovado, dados_completos)
- 🟡 **Amarelo**: Estados de espera (aguardando_confirmacao)
- 🔴 **Vermelho**: Estados de erro/cancelamento
- 🔵 **Azul**: Estados em processamento

---

## 📖 Como Usar Este Documento

1. **Para entender o fluxo geral**: Comece pelo **Diagrama 2** (Fluxo Completo)
2. **Para entender estados**: Veja **Diagrama 1** (Máquina de Estados)
3. **Para entender arquitetura**: Consulte **Diagrama 3** (Componentes)
4. **Para entender segurança**: Analise **Diagrama 4** (Multi-Tenant)
5. **Para entender dados**: Estude **Diagrama 5** (Modelo de Dados)

Combine com a leitura de [`ESTADOS_E_PERSISTENCIA.md`](ESTADOS_E_PERSISTENCIA.md) para detalhes completos.
