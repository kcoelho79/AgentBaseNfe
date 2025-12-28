# Fluxos Principais do Sistema

## 1. Fluxo de Emissão de Nota Fiscal (Happy Path)

### Visão Geral
O fluxo principal ocorre quando um cliente envia uma mensagem via WhatsApp solicitando a emissão de uma nota fiscal.

### Passo a Passo

#### 1. Cliente Envia Mensagem
```
Cliente: "Emitir nota de 150 reais para empresa XYZ CNPJ 12345678000190 consultoria"
```

#### 2. Webhook Recebe Mensagem
- WhatsApp API envia POST para `/webhook/whatsapp/`
- Sistema valida assinatura WAHA
- Identifica telefone do remetente

#### 3. Validação de Cliente
```python
# Busca cliente pelo telefone
cliente = ClienteContabilidade.objects.get(
    telefone='+5511999999999',
    is_active=True
)

# Verifica se contabilidade pode operar
if not cliente.contabilidade.pode_emitir_nota():
    return erro_contabilidade_inativa
```

#### 4. Busca Estado no Redis
```python
# Verifica se há conversa em andamento
estado = state_manager.get_state(telefone)

# Se não há estado, cria novo protocolo
if not estado:
    protocolo = Protocolo.objects.create(
        cliente_contabilidade=cliente,
        contabilidade=cliente.contabilidade,
        telefone_from=telefone,
        mensagem=mensagem,
        estado_mensagem='coleta'
    )
```

#### 5. Extração de Dados via IA

##### 5.1. Busca Contexto Histórico
```python
# Gera embedding da mensagem
embedding = openai.embeddings.create(
    model='text-embedding-ada-002',
    input=mensagem
)

# Busca registros similares no PostgreSQL (pgvector)
similar_records = DadosHistoricosCliente.objects.raw('''
    SELECT *
    FROM dados_historicos_cliente
    WHERE cliente_contabilidade_id = %s
    ORDER BY embedding <=> %s::vector
    LIMIT 5
''', [cliente.id, embedding])
```

##### 5.2. Monta Prompt com Contexto
```python
prompt = f"""
Extraia informações para emissão de nota fiscal da mensagem abaixo.

MENSAGEM: "{mensagem}"

CONTEXTO HISTÓRICO (emissões anteriores deste cliente):
- CNPJ 12345678000190: Empresa XYZ (usado 15 vezes)
- Descrição "Consultoria empresarial" (usado 10 vezes)
- Código serviço 0107 (usado 20 vezes)

EXTRAIA OS CAMPOS:
1. cnpj_tomador: CNPJ da empresa tomadora
2. valor: Valor monetário da nota
3. descricao: Descrição do serviço prestado
4. codigo_servico: Código do serviço municipal

RETORNE JSON:
{
    "cnpj_tomador": "...",
    "valor": 150.00,
    "descricao": "...",
    "codigo_servico": "..."
}
"""
```

##### 5.3. Chama OpenAI
```python
response = openai.chat.completions.create(
    model='gpt-4o-mini',
    messages=[
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': prompt}
    ],
    response_format={'type': 'json_object'},
    temperature=0.1
)

dados_extraidos = json.loads(response.choices[0].message.content)
```

#### 6. Validação de Dados

##### 6.1. Verifica Completude
```python
campos_obrigatorios = ['cnpj_tomador', 'valor', 'descricao']
campos_faltantes = [
    campo for campo in campos_obrigatorios
    if not dados_extraidos.get(campo)
]

if campos_faltantes:
    # Solicita dados faltantes ao cliente
    protocolo.estado_mensagem = 'dados_incompletos'
    protocolo.save()

    state_manager.update_state(
        telefone=telefone,
        novo_estado='dados_incompletos',
        dados=dados_extraidos,
        ttl=3600  # 1 hora
    )

    return "Por favor, informe: CNPJ do tomador"
```

##### 6.2. Valida Dados com IA
```python
validation_prompt = f"""
Valide se os dados extraídos estão corretos para emissão de NFSe.

Dados: {dados_extraidos}

Verifique:
1. CNPJ é válido?
2. Valor é positivo?
3. Descrição é adequada?

Retorne: {{"valido": bool, "erros": list}}
"""

validation = openai.chat.completions.create(...)
resultado = json.loads(validation.choices[0].message.content)

if not resultado['valido']:
    # Informa erros ao cliente
    return f"Dados inválidos: {', '.join(resultado['erros'])}"
```

#### 7. Gera Espelho e Pede Confirmação

```python
# Calcula ISS
aliquota_iss = cliente.aliquota_iss or 0.02  # 2% padrão
valor_iss = dados_extraidos['valor'] * aliquota_iss

# Monta espelho
espelho = f"""
📋 *ESPELHO DA NOTA FISCAL*

*Tomador:* {dados_extraidos['cnpj_tomador']}
*Valor:* R$ {dados_extraidos['valor']:.2f}
*Descrição:* {dados_extraidos['descricao']}
*Código Serviço:* {dados_extraidos.get('codigo_servico', 'Padrão')}

ISS: R$ {valor_iss:.2f}
*Valor Total:* R$ {dados_extraidos['valor']:.2f}

✅ Confirma a emissão? (Sim/Não)
"""

# Atualiza estado
protocolo.estado_mensagem = 'aguardando_confirmacao'
protocolo.dados_extraidos = dados_extraidos
protocolo.save()

state_manager.update_state(
    telefone=telefone,
    novo_estado='aguardando_confirmacao',
    dados=dados_extraidos,
    ttl=600  # 10 minutos
)

# Envia espelho
whatsapp_client.send_message(telefone, espelho)
```

#### 8. Cliente Confirma

```
Cliente: "Sim"
```

#### 9. Cria Nota Fiscal e Dispara Emissão

```python
# Cliente confirmou
if mensagem.lower().strip() in ['sim', 's', 'ok', 'confirmo']:

    # Cria nota fiscal (rascunho)
    nota_fiscal = NotaFiscal.objects.create(
        cliente_contabilidade=cliente,
        contabilidade=cliente.contabilidade,
        protocolo=protocolo,
        cnpj_tomador=dados['cnpj_tomador'],
        valor=dados['valor'],
        descricao=dados['descricao'],
        codigo_servico_municipal=dados.get('codigo_servico') or cliente.codigo_servico_municipal_padrao,
        aliquota_iss=cliente.aliquota_iss or Decimal('0.02'),
        valor_iss=dados['valor'] * (cliente.aliquota_iss or Decimal('0.02')),
        status='rascunho'
    )

    # Atualiza protocolo
    protocolo.estado_mensagem = 'confirmado'
    protocolo.save()

    # Dispara task assíncrona de emissão
    from apps.nfe.tasks import emitir_nfe_task
    emitir_nfe_task.delay(str(nota_fiscal.id))

    # Atualiza estado e limpa Redis
    protocolo.estado_mensagem = 'processando'
    protocolo.save()

    state_manager.clear_state(telefone)

    # Responde ao cliente
    return """
    ✅ *Nota fiscal em processamento!*

    Você receberá o PDF em alguns instantes.
    Protocolo: {protocolo.numero_protocolo}
    """
```

#### 10. Task Assíncrona de Emissão

```python
@shared_task(bind=True, max_retries=3)
def emitir_nfe_task(self, nota_fiscal_id):
    try:
        # 1. Busca nota fiscal
        nota = NotaFiscal.objects.select_related(
            'cliente_contabilidade',
            'contabilidade'
        ).get(id=nota_fiscal_id)

        # 2. Busca certificado digital ativo
        certificado = CertificadoDigital.objects.get(
            contabilidade=nota.contabilidade,
            is_active=True,
            validade__gte=timezone.now().date()
        )

        # 3. Monta RPS XML
        rps_xml = rps_builder.build(nota, certificado)

        # 4. Assina XML com certificado
        rps_assinado = sign_xml(rps_xml, certificado)

        # 5. Envia para Tecnospeed
        nota.status = 'enviado_gateway'
        nota.save()

        response = tecnospeed_client.enviar_rps(
            rps_xml=rps_assinado,
            certificado=certificado.certificado_arquivo
        )

        # 6. Processa retorno
        if response['sucesso']:
            # Sucesso!
            nota.numero_nfe = response['numero_nfe']
            nota.codigo_verificacao = response['codigo_verificacao']
            nota.xml_nfse = response['xml']
            nota.pdf_nfse = response['pdf']
            nota.status = 'aprovado'
            nota.emitida_em = timezone.now()
            nota.save()

            # Incrementa métricas do cliente
            nota.cliente_contabilidade.incrementar_metricas(nota.valor)

            # Envia PDF via WhatsApp
            whatsapp_client.send_document(
                telefone=nota.cliente_contabilidade.telefone,
                document=response['pdf'],
                caption=f"✅ Nota Fiscal #{nota.numero_nfe} emitida com sucesso!"
            )

            # Envia por email (se configurado)
            if nota.cliente_contabilidade.email and nota.cliente_contabilidade.notificar_por_email:
                send_email_task.delay(nota.id)

            # Salva no histórico para IA
            DadosHistoricosCliente.objects.create(
                cliente_contabilidade=nota.cliente_contabilidade,
                tipo_dado='emissao_completa',
                valor=json.dumps({
                    'cnpj_tomador': nota.cnpj_tomador,
                    'valor': float(nota.valor),
                    'descricao': nota.descricao
                }),
                contexto_original=nota.protocolo.mensagem,
                embedding=get_embedding(nota.descricao),
                validado=True
            )

        else:
            # Erro na emissão
            nota.status = 'rejeitado'
            nota.error_message = response['erro']
            nota.save()

            whatsapp_client.send_message(
                telefone=nota.cliente_contabilidade.telefone,
                mensagem=f"❌ Erro ao emitir nota: {response['erro']}"
            )

    except Exception as exc:
        # Retry com backoff
        nota.status = 'erro'
        nota.error_message = str(exc)
        nota.save()

        raise self.retry(exc=exc, countdown=30)
```

## 2. Fluxo de Dados Incompletos

### Cenário
Cliente envia mensagem sem todos os dados necessários.

```
Cliente: "Nota de 200 reais"
```

### Processo

1. **Extração identifica dados faltantes**
   - Tem: valor (200)
   - Falta: CNPJ tomador, descrição

2. **Sistema solicita complementação**
   ```
   Sistema: "Por favor, informe: CNPJ do tomador e descrição do serviço"
   ```

3. **Estado salvo no Redis**
   ```json
   {
     "estado": "dados_incompletos",
     "dados": {
       "valor": 200.00,
       "cnpj_tomador": null,
       "descricao": null
     },
     "protocolo_id": "uuid-123"
   }
   ```

4. **Cliente complementa**
   ```
   Cliente: "CNPJ 12345678000190 consultoria"
   ```

5. **Sistema faz merge dos dados**
   ```python
   # Recupera dados parciais do Redis
   estado = state_manager.get_state(telefone)
   dados_antigos = estado.dados

   # Extrai novos dados
   dados_novos = ai_extractor.extract(nova_mensagem, cliente.id)

   # Merge
   dados_completos = {**dados_antigos, **dados_novos}
   ```

6. **Continua fluxo normal** (validação → confirmação → emissão)

## 3. Fluxo de Cancelamento

### Cliente Cancela Operação

```
Cliente: "Cancelar"
```

### Processo

```python
# Em qualquer estado, permite cancelamento
protocolo.estado_mensagem = 'cancelado_usuario'
protocolo.save()

# Limpa estado do Redis
state_manager.clear_state(telefone)

# Responde
return "❌ Operação cancelada. Envie uma nova mensagem quando precisar."
```

### Exceção: Nota Já em Processamento

```python
if protocolo.estado_mensagem == 'processando':
    # Já disparou a task assíncrona
    return "⚠️ A nota já está sendo processada. Não é possível cancelar."
```

## 4. Fluxo de Timeout/Expiração

### Cron Job Verifica Estados Expirados

```python
# Executado a cada 5 minutos
@periodic_task(run_every=crontab(minute='*/5'))
def cleanup_expired_states():
    # Busca todos os estados no Redis
    keys = redis_client.keys('state:*')

    for key in keys:
        # Verifica TTL
        ttl = redis_client.ttl(key)

        if ttl <= 0:  # Expirado
            # Busca dados
            data = redis_client.get(key)
            estado = json.loads(data)

            # Busca protocolo
            protocolo = Protocolo.objects.get(id=estado['protocolo_id'])

            # Marca como expirado
            protocolo.estado_mensagem = 'expirado'
            protocolo.expirado_em = timezone.now()
            protocolo.save()

            # Notifica cliente
            if estado['estado'] == 'aguardando_confirmacao':
                whatsapp_client.send_message(
                    telefone=protocolo.telefone_from,
                    mensagem="⏱️ Tempo esgotado. A solicitação de nota fiscal expirou."
                )

            # Remove do Redis
            redis_client.delete(key)
```

## 5. Fluxo de Erro e Retry

### Erro no Gateway (Timeout)

```python
@shared_task(bind=True, max_retries=3)
def emitir_nfe_task(self, nota_fiscal_id):
    try:
        # Envia para gateway
        response = tecnospeed_client.enviar_rps(rps_xml, certificado)

    except TecnospeedTimeoutError as exc:
        # Timeout - Fazer retry
        nota.tentativas += 1
        nota.save()

        # Retry com backoff exponencial
        countdown = 30 * (2 ** self.request.retries)  # 30s, 60s, 120s
        raise self.retry(exc=exc, countdown=countdown)

    except MaxRetriesExceededError:
        # Esgotou tentativas
        nota.status = 'erro'
        nota.error_message = 'Gateway não respondeu após 3 tentativas'
        nota.save()

        whatsapp_client.send_message(
            telefone=nota.cliente_contabilidade.telefone,
            mensagem="❌ Erro ao emitir nota. Entre em contato com sua contabilidade."
        )
```

## 6. Fluxo de Busca Semântica

### Como Funciona o Histórico Inteligente

```python
# 1. Gera embedding da mensagem
mensagem = "nota para empresa xyz"
embedding = openai.embeddings.create(
    model='text-embedding-ada-002',
    input=mensagem
).data[0].embedding

# 2. Busca no PostgreSQL usando pgvector
sql = """
    SELECT
        tipo_dado,
        valor,
        contexto_original,
        frequencia_uso,
        1 - (embedding <=> %s::vector) as similarity
    FROM dados_historicos_cliente
    WHERE cliente_contabilidade_id = %s
        AND validado = true
    ORDER BY
        embedding <=> %s::vector,  -- Similaridade vetorial
        frequencia_uso DESC,        -- Mais usado
        ultima_utilizacao DESC      -- Mais recente
    LIMIT 5
"""

results = cursor.execute(sql, [embedding, cliente.id, embedding])

# 3. Usa matches para enriquecer prompt da IA
contexto = "\n".join([
    f"- {r.tipo_dado}: {r.valor} (usado {r.frequencia_uso}x, similaridade {r.similarity:.2f})"
    for r in results
])

prompt = f"""
Mensagem: {mensagem}

Histórico do cliente:
{contexto}

Extraia os dados...
"""
```

### Salvando Novos Dados no Histórico

```python
# Após emissão bem-sucedida
DadosHistoricosCliente.objects.create(
    cliente_contabilidade=cliente,
    tipo_dado='cnpj_tomador',
    valor='12345678000190',
    contexto_original='empresa xyz',
    embedding=get_embedding('12345678000190 empresa xyz'),
    frequencia_uso=1,
    validado=True
)

# Na próxima vez que o cliente mencionar "empresa xyz",
# o sistema encontrará o CNPJ automaticamente!
```

## Decisões de Design

### TTLs dos Estados
- **COLETA**: 1 hora (usuário pode demorar a responder)
- **DADOS_INCOMPLETOS**: 1 hora
- **AGUARDANDO_CONFIRMACAO**: 10 minutos (decisão rápida esperada)
- **PROCESSANDO**: Sem TTL (gerenciado por task)

### Retry Strategy
- **OpenAI**: 3 tentativas, backoff exponencial (1s, 2s, 4s)
- **Gateway NFe**: 3 tentativas, backoff fixo (30s, 60s, 120s)
- **WhatsApp**: 5 tentativas, backoff exponencial

### Priorização de Filas Celery
1. **high**: Emissão de NFe (crítico para o usuário)
2. **default**: Envio de emails, PDFs
3. **low**: Cleanup, métricas, relatórios
