from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_nfse(request):
    """
    Recebe webhook de processamento de NFSe.
    
    Endpoint: POST /nfse/webhook/
    """
    try:
        payload = json.loads(request.body)
        logger.info(f"Webhook recebido: {payload.get('id')}")
        
        # TODO: Processar em background (Celery futuramente)
        # from apps.nfse.services.emissao import NFSeEmissaoService
        # NFSeEmissaoService.processar_webhook(payload)
        
        return JsonResponse({"status": "received"}, status=200)
        
    except Exception as e:
        logger.exception("Erro ao processar webhook")
        return JsonResponse({"error": str(e)}, status=500)
