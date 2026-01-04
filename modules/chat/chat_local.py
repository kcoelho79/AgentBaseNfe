from flask import Flask, render_template, request, jsonify
from workflow import process_message
from state_manager import StateManager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# Simulação de telefones para teste
TELEFONES_TESTE = {
    'cliente1': '5511999999999',  # João Silva (cadastrado)
    'cliente2': '5511888888888',  # Maria Santos (cadastrado)
    'cliente3': '5511777777777',  # Pedro Costa (inativo)
    'nao_cadastrado': '5511666666666'
}

@app.route('/')
def index():
    """Interface do chat."""
    return render_template('chat.html', telefones=TELEFONES_TESTE)

@app.route('/send', methods=['POST'])
def send_message():
    """Processa mensagem do usuário."""
    data = request.json
    telefone = data.get('telefone')
    mensagem = data.get('mensagem')
    
    if not telefone or not mensagem:
        return jsonify({'error': 'Telefone e mensagem obrigatórios'}), 400
    
    try:
        # Processar mensagem (mesmo workflow do WhatsApp)
        result = process_message(telefone, mensagem, f'local_{id(mensagem)}')
        
        return jsonify({
            'status': 'success',
            'resposta': result['resposta'],
            'telefone': telefone
        })
    
    except Exception as e:
        logging.exception('Erro ao processar mensagem no chat local')
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/clear/<telefone>', methods=['POST'])
def clear_state(telefone):
    """Limpa estado de uma conversa."""
    try:
        sm = StateManager()
        sm.clear_state(telefone)
        
        return jsonify({'status': 'success', 'message': 'Estado limpo'})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({'status': 'ok', 'service': 'AgentNFe Chat Local'})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 AgentNFe - Chat Local iniciado!")
    print("="*60)
    print("\n📱 Acesse: http://localhost:5000")
    print("\n📞 Telefones de teste disponíveis:")
    for nome, tel in TELEFONES_TESTE.items():
        print(f"   • {nome:15s} → {tel}")
    print("\n💡 Dica: Abra o navegador e comece a testar!")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')
