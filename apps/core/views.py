from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from apps.core.message_gateway import MessageGateway

logger = logging.getLogger(__name__)

# Simulação de telefones para teste
TELEFONES_TESTE = {
    'cliente1': '5511999999999',  # João Silva (cadastrado)
    'cliente2': '5511888888888',  # Maria Santos (cadastrado)
    'cliente3': '5511777777777',  # Pedro Costa (inativo)
    'nao_cadastrado': '5511666666666'
}


def chat_local(request):
    """Interface do chat."""
    return render(request, 'core/chat.html', {'telefones': TELEFONES_TESTE})


@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    
    try:
        data = json.loads(request.body)
        telefone = data.get('telefone')
        mensagem = data.get('mensagem')
        
        if not telefone or not mensagem:
            return JsonResponse(
                {'error': 'Telefone e mensagem obrigatórios'},
                status=400
            )
        
        # Usar Gateway para validar e processar
        gateway = MessageGateway(send_rejection_message=True)
        result = gateway.process(telefone, mensagem)
        
        logger.info(f"Resposta: {result.response}")
        
        return JsonResponse({
            'status': 'success' if result.success else 'rejected',
            'resposta': result.response,
            'telefone': telefone
        })
    
    except Exception as e:
        logger.exception('Erro ao processar mensagem no chat local')
        return JsonResponse(
            {'status': 'error', 'error': str(e)},
            status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def clear_state(request, telefone):
    """Limpa estado de uma conversa."""
    try:
        from apps.core.session_manager import SessionManager
        sm = SessionManager()
        sm.delete_session(telefone)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Estado limpo para {telefone}'
        })
    except Exception as e:
        logger.exception('Erro ao limpar estado')
        return JsonResponse(
            {'status': 'error', 'error': str(e)},
            status=500
        )


@require_http_methods(["GET"])
def health(request):
    """Health check."""
    return JsonResponse({
        'status': 'ok',
        'service': 'AgentNFe Chat Local'
    })
