#!/usr/bin/env python3
"""
Versão SIMPLES que FUNCIONA
Menos prompt, mais ação!
"""

from openai import OpenAI
import json
from typing import Dict, Optional

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

OPENAI_API_KEY = "sk-..."  # ← Sua chave
OPENAI_MODEL = "gpt-4o-mini"

# ============================================================================
# PROMPT SIMPLES E DIRETO
# ============================================================================

SYSTEM_PROMPT = """Você extrai dados de notas fiscais brasileiras.

EXTRAIR:
- CNPJ (14 dígitos)
- Valor (número positivo)
- Descrição (serviço prestado, 10-500 chars)

DESCRIÇÃO - REGRAS:

1. IGNORAR solicitações (não são descrição):
   "emitir nota", "fazer nota", "urgente", "por favor"

2. REJEITAR genéricas (muito vagas):
   "serviço", "serviços prestado", "trabalho"

3. ACEITAR específicas:
   "consultoria em TI", "manutenção de PCs"

QUANDO CHAMAR get_recent_descriptions:
- Descrição ausente
- Descrição é solicitação
- Descrição é genérica

EXEMPLOS:

Input: "cnpj 06305747000134 valor 150"
→ Descrição AUSENTE → Chamar get_recent_descriptions(cnpj="06305747000134")

Input: "cnpj 123 valor 150 emitir nota"
→ "emitir nota" = solicitação → Chamar get_recent_descriptions(cnpj="123")

Input: "cnpj 123 valor 150 serviços prestado"
→ "serviços prestado" = genérica → Chamar get_recent_descriptions(cnpj="123")

Input: "cnpj 123 valor 1500 consultoria empresarial"
→ "consultoria empresarial" = válida → NÃO chamar tool

IMPORTANTE:
- NÃO explique seu raciocínio
- NÃO narre suas ações
- APENAS chame tool quando necessário
- SEMPRE retorne JSON válido no final

JSON:
{
  "cnpj": {"cnpj": "14digits", "status": "validated|null"},
  "valor": {"valor": number, "status": "validated|null"},
  "descricao": {
    "descricao": "texto",
    "suggestion_source": "USER|HISTORY_CNPJ|HISTORY_GENERAL|null",
    "status": "validated|warning|null"
  },
  "data_complete": true|false,
  "user_message": "mensagem"
}"""

# ============================================================================
# TOOLS
# ============================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_recent_descriptions",
            "description": "Retorna descrições de notas anteriores. Use quando descrição ausente/genérica/solicitação.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cnpj": {"type": "string", "description": "CNPJ (14 dígitos)"},
                    "limit": {"type": "integer", "default": 5}
                }
            }
        }
    }
]

def get_recent_descriptions(cnpj: Optional[str] = None, limit: int = 5) -> Dict:
    print(f"\n🔧 TOOL: get_recent_descriptions(cnpj={cnpj})")
    
    data = {
        "06305747000134": [
            "Manutenção preventiva e corretiva em equipamentos de informática",
            "Consultoria em tecnologia da informação",
            "Serviços de infraestrutura de TI"
        ],
        "12345678000190": [
            "Consultoria empresarial e assessoria estratégica",
            "Treinamento corporativo"
        ]
    }
    
    if cnpj and cnpj in data:
        descs = data[cnpj][:limit]
        conf = "HIGH"
    else:
        descs = ["Consultoria e assessoria técnica", "Prestação de serviços profissionais"][:limit]
        conf = "MEDIUM"
    
    result = {
        "success": True,
        "suggested_description": descs[0],
        "confidence": conf,
        "total": len(descs) * 5
    }
    
    print(f"✅ Sugestão: '{result['suggested_description']}'")
    return result

AVAILABLE_FUNCTIONS = {"get_recent_descriptions": get_recent_descriptions}

# ============================================================================
# EXTRATOR
# ============================================================================

class SimpleExtractor:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def extract(self, message: str) -> Dict:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message}
        ]
        
        print(f"\n{'='*70}")
        print(f"🤖 INPUT: {message}")
        print(f"{'='*70}")
        
        for i in range(5):
            print(f"\n📡 Call {i+1}...")
            
            try:
                response = self.client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.1,
                    max_tokens=800
                )
                
                msg = response.choices[0].message
                messages.append(msg)
                
                # Tool calls?
                if msg.tool_calls:
                    print(f"🔧 Tool calls: {len(msg.tool_calls)}")
                    
                    for tc in msg.tool_calls:
                        fname = tc.function.name
                        fargs = json.loads(tc.function.arguments)
                        result = AVAILABLE_FUNCTIONS[fname](**fargs)
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": fname,
                            "content": json.dumps(result, ensure_ascii=False)
                        })
                    continue
                
                # Parse JSON
                content = msg.content
                if not content:
                    return self._error("Empty response")
                
                # Extrai JSON
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    print("✅ OK")
                    return result
                else:
                    # Tenta parsear direto
                    result = json.loads(content)
                    print("✅ OK")
                    return result
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
        
        return self._error("Max iterations")
    
    def _error(self, msg: str) -> dict:
        return {
            "cnpj": {"status": "null"},
            "valor": {"status": "null"},
            "descricao": {"status": "null"},
            "data_complete": False,
            "user_message": f"Erro: {msg}"
        }

# ============================================================================
# TESTES
# ============================================================================

def run_tests():
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-...":
        print("❌ Configure OPENAI_API_KEY!")
        return
    
    ext = SimpleExtractor(OPENAI_API_KEY)
    
    tests = [
        {
            "name": "✅ Descrição válida (NÃO deve chamar tool)",
            "msg": "CNPJ 12345678000190 valor R$ 1.500,00 consultoria empresarial e assessoria",
            "should_call": False
        },
        {
            "name": "🔧 Descrição genérica (DEVE chamar tool)",
            "msg": "nota serviços prestado cnpj 06305747000134 valor 150,00",
            "should_call": True
        },
        {
            "name": "🔧 Sem descrição (DEVE chamar tool)",
            "msg": "cnpj 06305747000134 valor 150,00",
            "should_call": True
        },
        {
            "name": "🔧 Solicitação (DEVE chamar tool)",
            "msg": "nota 200 cnpj 06305747000134 por favor emitir",
            "should_call": True
        }
    ]
    
    for t in tests:
        print(f"\n\n{'#'*70}")
        print(f"# {t['name']}")
        print(f"{'#'*70}")
        
        r = ext.extract(t['msg'])
        
        print(f"\n📋 RESULTADO:")
        print(json.dumps(r, indent=2, ensure_ascii=False))
        
        called = bool(r.get('descricao', {}).get('suggestion_source'))
        
        if t['should_call']:
            if called:
                print("\n✅✅✅ CORRETO: Tool chamada!")
            else:
                print("\n❌❌❌ ERRO: Deveria chamar tool!")
        else:
            if not called:
                print("\n✅ CORRETO: Tool não chamada!")
            else:
                print("\n⚠️ Tool chamada desnecessariamente")
        
        input("\n[ENTER]")

def interactive():
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-...":
        print("❌ Configure OPENAI_API_KEY!")
        return
    
    ext = SimpleExtractor(OPENAI_API_KEY)
    
    print("\n🤖 MODO INTERATIVO - Versão Simples")
    print("Digite 'sair' para sair\n")
    
    while True:
        inp = input("Você: ").strip()
        if inp.lower() in ['sair', 'exit']:
            break
        if not inp:
            continue
        
        r = ext.extract(inp)
        print(f"\n🤖: {r.get('user_message', '')}\n")

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║  🚀 NFe Extraction - VERSÃO SIMPLES QUE FUNCIONA                    ║
║  Menos prompt = mais efetivo!                                       ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    from decouple import config
    OPENAI_API_KEY = config('OPENAI_API_KEY', default="sk-...") 
    
    choice = input("1=Testes | 2=Interativo: ").strip()
    
    if choice == "1":
        run_tests()
    elif choice == "2":
        interactive()
    

