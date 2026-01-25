# Implementação: Snapshot de Usuário e Empresa

## 📋 Resumo

Implementação de campos de snapshot para capturar dados de usuário e empresa no momento da criação da sessão, permitindo auditoria histórica e visualização dos dados originais mesmo após alterações cadastrais.

## 🎯 Objetivos

- ✅ Capturar nome do usuário no momento da sessão
- ✅ Capturar nome da empresa no momento da sessão
- ✅ Manter referência à empresa original
- ✅ Permitir auditoria histórica
- ✅ Exibir informações nas listagens sem JOINs complexos

## 🗄️ Mudanças no Banco de Dados

### Novos Campos em `SessionSnapshot`

```python
# apps/core/db_models.py

usuario_nome_snapshot = models.CharField(
    max_length=200,
    blank=True,
    null=True,
    verbose_name='Nome do Usuário (Snapshot)'
)

empresa_nome_snapshot = models.CharField(
    max_length=200,
    blank=True,
    null=True,
    verbose_name='Nome da Empresa (Snapshot)'
)

empresa_id_snapshot = models.IntegerField(
    blank=True,
    null=True,
    db_index=True,
    verbose_name='ID da Empresa (Snapshot)'
)
```

**Migration:** `0005_sessionsnapshot_empresa_id_snapshot_and_more`

## 🔧 Mudanças no Código

### 1. `SessionSnapshot.from_session()` - [db_models.py](apps/core/db_models.py#L270)

```python
@classmethod
def from_session(cls, session, reason: str = 'manual', usuario_context: dict = None):
    """Aceita dicionário com contexto do usuário"""
    
    usuario_nome = None
    empresa_nome = None
    empresa_id = None
    
    if usuario_context:
        usuario_nome = usuario_context.get('nome')
        empresa_nome = usuario_context.get('empresa_nome')
        empresa_id = usuario_context.get('empresa_id')
    
    return cls(
        # ... outros campos ...
        usuario_nome_snapshot=usuario_nome,
        empresa_nome_snapshot=empresa_nome,
        empresa_id_snapshot=empresa_id,
    )
```

### 2. `SessionManager._get_usuario_context()` - [session_manager.py](apps/core/session_manager.py)

Novo método privado que busca dados do usuário:

```python
def _get_usuario_context(self, telefone: str) -> dict:
    """Busca contexto do usuário pelo telefone"""
    try:
        from apps.contabilidade.models import UsuarioEmpresa
        
        usuario = UsuarioEmpresa.objects.select_related('empresa').filter(
            telefone=telefone,
            is_active=True
        ).first()
        
        if usuario:
            return {
                'nome': usuario.nome,
                'empresa_nome': usuario.empresa.nome_fantasia or usuario.empresa.razao_social,
                'empresa_id': usuario.empresa.id
            }
    except Exception as e:
        logger.warning(f'Erro ao buscar contexto: {e}')
    
    return {}
```

### 3. `SessionManager.save_session()` - [session_manager.py](apps/core/session_manager.py)

Captura contexto apenas na criação:

```python
@transaction.atomic
def save_session(self, session: Session, reason: str = 'manual') -> None:
    usuario_context = None
    existing = SessionSnapshot.objects.filter(sessao_id=session.sessao_id).first()
    
    if not existing:
        # Primeira vez - captura contexto
        usuario_context = self._get_usuario_context(session.telefone)
    
    if not existing:
        snapshot = SessionSnapshot.from_session(session, reason, usuario_context)
        snapshot.save()
```

### 4. Template - [list.html](apps/contabilidade/templates/contabilidade/sessao/list.html)

Exibição simples dos dados snapshots:

```html
<td>
    <code>{{ sessao.sessao_id }}</code>
    {% if sessao.empresa_nome_snapshot %}
    <div class="small text-muted">
        <i class="bi bi-building"></i>{{ sessao.empresa_nome_snapshot }}
    </div>
    {% endif %}
</td>
<td>
    {{ sessao.telefone }}
    {% if sessao.usuario_nome_snapshot %}
    <div class="small text-muted">
        <i class="bi bi-person"></i>{{ sessao.usuario_nome_snapshot }}
    </div>
    {% endif %}
</td>
```

## ✅ Vantagens da Abordagem

1. **Auditoria Histórica**
   - Dados permanecem como estavam no momento da criação
   - Útil para compliance e rastreabilidade

2. **Performance**
   - Sem JOINs na listagem
   - Query simples: `SELECT * FROM core_sessionsnapshot`

3. **Resiliência**
   - Se usuário for deletado, snapshot preserva os dados
   - Se empresa mudar de nome, histórico mantém original

4. **Simplicidade no Template**
   - Acesso direto: `{{ sessao.usuario_nome_snapshot }}`
   - Sem filtros customizados ou dicionários

## ⚠️ Trade-offs

### Desvantagens

1. **Dados desatualizados**
   - Se usuário mudar nome, sessões antigas não atualizam
   - **Solução:** Isso é esperado para auditoria

2. **Duplicação de dados**
   - Mesmo nome armazenado em múltiplas sessões
   - **Impacto:** Mínimo (~400 bytes por sessão)

3. **Dependência circular**
   - `core` importa `contabilidade.models` em runtime
   - **Solução:** Import dentro do método (lazy import)

### Quando NÃO usar snapshot

- ❌ Se precisa sempre mostrar dados atualizados
- ❌ Se tabela terá milhões de registros (considerar normalização)
- ❌ Se mudanças cadastrais devem refletir no histórico

## 🔄 Migrations

```bash
# Aplicar mudanças
python manage.py migrate core

# Verificar campos
python manage.py shell -c "from apps.core.db_models import SessionSnapshot; \
print([f.name for f in SessionSnapshot._meta.fields if 'snapshot' in f.name])"
```

**Saída esperada:**
```
['usuario_nome_snapshot', 'empresa_nome_snapshot', 'empresa_id_snapshot', ...]
```

## 📊 Exemplo de Uso

### Criando uma sessão

```python
# Usuário 5511999999999 (João da Silva, empresa RBK Ltda)
processor = MessageProcessor()
response = processor.process('5511999999999', 'emitir nota')

# No banco:
SessionSnapshot.objects.filter(telefone='5511999999999').values(
    'sessao_id',
    'usuario_nome_snapshot',
    'empresa_nome_snapshot'
)
# Resultado:
# {
#   'sessao_id': '250126-a3f2',
#   'usuario_nome_snapshot': 'João da Silva',
#   'empresa_nome_snapshot': 'RBK Ltda'
# }
```

### Listando sessões

```python
# View
sessoes = SessionSnapshot.objects.all()

# Template
{% for sessao in sessoes %}
  {{ sessao.sessao_id }} - {{ sessao.usuario_nome_snapshot }} ({{ sessao.empresa_nome_snapshot }})
{% endfor %}
```

**Resultado:**
```
250126-a3f2 - João da Silva (RBK Ltda)
250126-b7e1 - Maria Santos (ABC Contadores)
```

## 🎯 Casos de Uso Ideais

✅ **Recomendado para:**
- Sistemas de auditoria
- Histórico de transações
- Compliance/LGPD (rastreabilidade)
- Relatórios com dados "no momento da ação"

❌ **Evitar para:**
- Cadastros que precisam sempre estar atualizados
- Dashboards em tempo real
- Dados que mudam frequentemente

## 📝 Próximos Passos

1. ✅ Implementado: Campos de snapshot
2. ✅ Implementado: Captura automática na criação
3. ✅ Implementado: Exibição no template
4. ⏳ Futuro: Adicionar ao DetailView também
5. ⏳ Futuro: Criar relatório de auditoria usando snapshots

---

**Data da Implementação:** 25/01/2026  
**Autor:** Sistema AgentNFe  
**Migration:** `0005_sessionsnapshot_empresa_id_snapshot_and_more`
