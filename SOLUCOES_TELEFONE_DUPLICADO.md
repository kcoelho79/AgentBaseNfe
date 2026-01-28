# Soluções para Telefone Duplicado em Múltiplas Empresas

## Problema
Um `UsuarioEmpresa` pode ter o mesmo telefone cadastrado em várias empresas. Quando uma sessão é aberta, o sistema não sabe qual empresa usar.

## Código Atual (Problema)
```python
# apps/nfse/services/emissao.py linha 57-60
usuario_empresa = UsuarioEmpresa.objects.filter(
    telefone=session.telefone,
    is_active=True
).select_related('empresa').first()  # ⚠️ Pega a primeira - pode ser a errada!
```

---

## Solução 1: UNIQUE Constraint (MVP - Mais Simples) ✅

### O que faz:
- Um telefone só pode estar em **uma empresa**
- Banco rejeita cadastro duplicado
- Ideal para MVP

### Implementação:

#### 1. Alterar Model
```python
# apps/contabilidade/models.py
class UsuarioEmpresa(models.Model):
    # ... campos existentes ...
    
    class Meta:
        verbose_name = 'usuário da empresa'
        verbose_name_plural = 'usuários da empresa'
        ordering = ['nome']
        # REMOVER: unique_together = ['empresa', 'telefone']
        # ADICIONAR:
        constraints = [
            models.UniqueConstraint(
                fields=['telefone'],
                condition=models.Q(is_active=True),
                name='unique_telefone_ativo'
            )
        ]
```

#### 2. Criar Migration
```bash
python manage.py makemigrations contabilidade
python manage.py migrate
```

#### 3. Atualizar Form com Validação
```python
# apps/contabilidade/forms.py
class UsuarioEmpresaForm(forms.ModelForm):
    # ... campos existentes ...
    
    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone', '')
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        
        # Verifica se já existe em outra empresa (apenas para ativos)
        qs = UsuarioEmpresa.objects.filter(
            telefone=telefone_limpo,
            is_active=True
        )
        
        # Se está editando, exclui o próprio registro
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            usuario_existente = qs.first()
            raise forms.ValidationError(
                f'Este telefone já está cadastrado para {usuario_existente.empresa.razao_social}. '
                f'Um telefone só pode estar ativo em uma empresa por vez.'
            )
        
        return telefone_limpo
```

### Prós:
- ✅ Simples de implementar
- ✅ Sem ambiguidade
- ✅ Perfeito para MVP

### Contras:
- ❌ Não atende caso real onde uma pessoa trabalha em múltiplas empresas

---

## Solução 2: Seleção Manual com Prefixo/Comando (Intermediária) 🎯

### O que faz:
- Permite telefone em múltiplas empresas
- Usuário informa qual empresa quer usar via **prefixo** ou **menu**

### Opção A: Prefixo no Início da Conversa
```
Usuário: #empresa2 Emitir nota de 1500 reais
Sistema: Ok, usando empresa "Minha Empresa Ltda". Como posso ajudar?
```

### Opção B: Menu de Seleção
```
Sistema: Olá! Você tem acesso a 3 empresas:
1. Empresa A
2. Empresa B  
3. Empresa C

Digite o número da empresa para continuar.
```

### Implementação Opção B (Menu):

#### 1. Adicionar Campo na Session
```python
# apps/core/models.py
class Session(BaseModel):
    # ... campos existentes ...
    empresa_id: Optional[int] = None  # ID da empresa selecionada
```

#### 2. Criar Estado de Seleção
```python
# apps/core/states.py
class SessionState(str, Enum):
    # ... estados existentes ...
    SELECAO_EMPRESA = 'selecao_empresa'  # Novo estado
```

#### 3. Lógica no MessageProcessor
```python
# apps/core/message_processor.py
def process(self, telefone: str, mensagem: str) -> str:
    session = self.session_manager.get_or_create_session(telefone)
    
    # Verificar se precisa selecionar empresa
    if not session.empresa_id:
        empresas = UsuarioEmpresa.objects.filter(
            telefone=telefone,
            is_active=True
        ).select_related('empresa')
        
        if empresas.count() > 1:
            session.estado = SessionState.SELECAO_EMPRESA.value
            # Salvar lista de empresas temporariamente
            return self._montar_menu_empresas(empresas)
        elif empresas.count() == 1:
            session.empresa_id = empresas.first().empresa.id
        else:
            return "❌ Telefone não cadastrado em nenhuma empresa."
    
    # Se está no estado de seleção, processar escolha
    if session.estado == SessionState.SELECAO_EMPRESA.value:
        return self._processar_selecao_empresa(session, mensagem)
    
    # Continuar fluxo normal...
```

### Prós:
- ✅ Atende caso real de múltiplas empresas
- ✅ Usuário tem controle
- ✅ UX clara

### Contras:
- ⚠️ Mais complexo
- ⚠️ Passo extra na conversa

---

## Solução 3: Contexto Inteligente (Avançada) 🚀

### O que faz:
- Sistema **lembra** a última empresa usada
- Usuário pode trocar com comando

### Implementação:

#### 1. Tabela de Histórico
```python
# apps/core/models.py (novo model)
class UsuarioEmpresaHistorico(models.Model):
    '''Registra última empresa usada por telefone.'''
    telefone = models.CharField(max_length=20, unique=True, db_index=True)
    empresa = models.ForeignKey('contabilidade.Empresa', on_delete=models.CASCADE)
    ultima_sessao = models.DateTimeField(auto_now=True)
    total_sessoes = models.IntegerField(default=0)
```

#### 2. Lógica Inteligente
```python
# apps/nfse/services/emissao.py
def _buscar_empresa_usuario(telefone: str) -> Empresa:
    '''Busca empresa para o telefone com inteligência.'''
    
    # 1. Tentar histórico (última empresa usada)
    historico = UsuarioEmpresaHistorico.objects.filter(
        telefone=telefone
    ).first()
    
    if historico:
        # Verificar se usuário ainda está ativo nessa empresa
        if UsuarioEmpresa.objects.filter(
            telefone=telefone,
            empresa=historico.empresa,
            is_active=True
        ).exists():
            return historico.empresa
    
    # 2. Se não tem histórico, buscar empresa única
    usuarios = UsuarioEmpresa.objects.filter(
        telefone=telefone,
        is_active=True
    ).select_related('empresa')
    
    if usuarios.count() == 1:
        empresa = usuarios.first().empresa
        # Salvar no histórico
        UsuarioEmpresaHistorico.objects.update_or_create(
            telefone=telefone,
            defaults={'empresa': empresa}
        )
        return empresa
    
    # 3. Múltiplas empresas - precisa menu
    raise MultipleEmpresasException(
        f"Telefone {telefone} cadastrado em {usuarios.count()} empresas"
    )
```

### Prós:
- ✅ Melhor UX (sem passo extra na maioria dos casos)
- ✅ Atende casos reais
- ✅ Sistema "aprende"

### Contras:
- ⚠️ Mais complexo
- ⚠️ Precisa gerenciar histórico

---

## Recomendação por Fase:

### 🟢 **MVP (Agora)**: Solução 1 - Unique Constraint
- Simples e eficaz
- Resolve o problema imediato
- Fácil migrar depois

### 🟡 **v0.3**: Solução 2 - Menu de Seleção  
- Quando precisar suportar múltiplas empresas
- UX clara

### 🔵 **v1.0**: Solução 3 - Contexto Inteligente
- Melhor experiência
- Produção

---

## Implementação Imediata (MVP)

Execute agora para implementar Solução 1:

```bash
# 1. Aplicar alterações no modelo (veja código acima)
# 2. Criar migration
python manage.py makemigrations contabilidade --name unique_telefone_constraint

# 3. Verificar conflitos existentes (antes de migrar)
python manage.py shell
>>> from apps.contabilidade.models import UsuarioEmpresa
>>> from django.db.models import Count
>>> duplicados = UsuarioEmpresa.objects.values('telefone').annotate(count=Count('id')).filter(count__gt=1, is_active=True)
>>> for dup in duplicados:
...     print(f"Telefone {dup['telefone']} em {dup['count']} empresas")

# 4. Se tiver duplicados, desativar ou remover manualmente
# 5. Executar migration
python manage.py migrate
```
