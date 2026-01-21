"""
Teste para validar o cenário reportado:
Mensagem: "emitir nota de R$ 150,00 pilas cnpj 06305747000133 serviços prestadis"

Esperado: 
- CNPJ deve estar com erro (dígitos verificadores inválidos)
- Valor e descrição devem estar validated
- data_complete deve ser False
- user_message DEVE informar o erro do CNPJ, NÃO "Tudo certo!"
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório raiz do projeto ao PYTHONPATH
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.core.agent_extractor import AIExtractor

def test_cnpj_invalido_com_outros_campos_ok():
    """Testa o cenário onde CNPJ é inválido mas outros campos estão OK"""
    
    # Mensagem problemática reportada
    mensagem = "emitir nota de R$ 150,00 pilas cnpj 06305747000133 serviços prestadis"
    
    print("="*80)
    print("TESTE: CNPJ Inválido com outros campos validados")
    print("="*80)
    print(f"\nMensagem: {mensagem}\n")
    
    # Inicializar extrator
    extractor = AIExtractor()
    
    # Fazer extração
    resultado = extractor.parse(mensagem)
    
    # Exibir resultado
    print("RESULTADO DA EXTRAÇÃO:")
    print("-"*80)
    print(f"data_complete: {resultado.data_complete}")
    print(f"missing_fields: {resultado.missing_fields}")
    print(f"invalid_fields: {resultado.invalid_fields}")
    print()
    
    print("CNPJ:")
    print(f"  - cnpj_extracted: {resultado.cnpj.cnpj_extracted}")
    print(f"  - cnpj: {resultado.cnpj.cnpj}")
    print(f"  - status: {resultado.cnpj.status}")
    print(f"  - error_type: {resultado.cnpj.error_type}")
    print(f"  - cnpj_issue: {resultado.cnpj.cnpj_issue}")
    print()
    
    print("VALOR:")
    print(f"  - valor_extracted: {resultado.valor.valor_extracted}")
    print(f"  - valor: {resultado.valor.valor}")
    print(f"  - status: {resultado.valor.status}")
    print(f"  - valor_formatted: {resultado.valor.valor_formatted}")
    print()
    
    print("DESCRIÇÃO:")
    print(f"  - descricao_extracted: {resultado.descricao.descricao_extracted}")
    print(f"  - descricao: {resultado.descricao.descricao}")
    print(f"  - status: {resultado.descricao.status}")
    print()
    
    print("="*80)
    print("MENSAGEM PARA O USUÁRIO:")
    print("="*80)
    print(resultado.user_message)
    print()
    
    # Validações
    print("="*80)
    print("VALIDAÇÕES:")
    print("="*80)
    
    # 1. CNPJ deve estar com erro
    assert resultado.cnpj.status == 'error', f"❌ CNPJ deveria estar com erro, mas está: {resultado.cnpj.status}"
    print("✅ CNPJ está com status='error'")
    
    # 2. Valor deve estar validated
    assert resultado.valor.status == 'validated', f"❌ Valor deveria estar validated, mas está: {resultado.valor.status}"
    print("✅ Valor está com status='validated'")
    
    # 3. Descrição deve estar validated
    assert resultado.descricao.status == 'validated', f"❌ Descrição deveria estar validated, mas está: {resultado.descricao.status}"
    print("✅ Descrição está com status='validated'")
    
    # 4. data_complete deve ser False
    assert resultado.data_complete == False, f"❌ data_complete deveria ser False, mas é: {resultado.data_complete}"
    print("✅ data_complete está False")
    
    # 5. Deve ter invalid_fields
    assert len(resultado.invalid_fields) > 0, "❌ Deveria ter invalid_fields"
    print(f"✅ Tem invalid_fields: {resultado.invalid_fields}")
    
    # 6. Mensagem NÃO deve conter "Tudo certo"
    assert "Tudo certo" not in resultado.user_message, f"❌ Mensagem NÃO deveria conter 'Tudo certo!': {resultado.user_message}"
    print("✅ Mensagem NÃO contém 'Tudo certo!'")
    
    # 7. Mensagem DEVE mencionar erro do CNPJ
    assert any(palavra in resultado.user_message.lower() for palavra in ['cnpj', 'incorreto', 'inválido', 'erro', 'conferir']), \
        f"❌ Mensagem deveria mencionar erro do CNPJ: {resultado.user_message}"
    print(f"✅ Mensagem menciona o erro do CNPJ")
    
    print()
    print("="*80)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("="*80)


if __name__ == "__main__":
    test_cnpj_invalido_com_outros_campos_ok()
