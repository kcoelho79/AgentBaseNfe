"""
Views para gerenciamento de canais WhatsApp.
"""

import json
import logging
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from apps.contabilidade.mixins import TenantMixin
from apps.core.message_processor import MessageProcessor
from .models import CanalWhatsApp, WebhookLog
from .forms import CanalWhatsAppForm
from .services.evolution import EvolutionService, EvolutionAPIError

logger = logging.getLogger(__name__)


# ==================== MIXINS ====================

class WhatsAppMixin:
    """Mixin com funcionalidades comuns para views de WhatsApp."""
    
    def get_evolution_service(self):
        """Retorna instância do serviço Evolution."""
        return EvolutionService()


def _extract_qrcode_base64(result: dict) -> str:
    """
    Extrai o QR Code base64 da resposta da Evolution API.
    Remove o prefixo data:image se existir.
    
    Args:
        result: Resposta da Evolution API
        
    Returns:
        String base64 pura (sem prefixo data:image)
    """
    qrcode_base64 = ''
    
    # Formato 1: {'qrcode': {'base64': '...'}}
    if 'qrcode' in result:
        qr_data = result['qrcode']
        if isinstance(qr_data, dict):
            qrcode_base64 = qr_data.get('base64', '') or qr_data.get('code', '')
        elif isinstance(qr_data, str):
            qrcode_base64 = qr_data
    
    # Formato 2: {'base64': '...'}
    elif 'base64' in result:
        qrcode_base64 = result['base64']
        
    # Formato 3: {'code': '...'}
    elif 'code' in result:
        qrcode_base64 = result['code']
    
    # Remover prefixo data:image se existir
    if qrcode_base64 and qrcode_base64.startswith('data:'):
        qrcode_base64 = qrcode_base64.split(',', 1)[-1]
    
    return qrcode_base64



# ==================== CANAL VIEWS ====================

@login_required
def canal_list(request):
    """Lista todos os canais WhatsApp da contabilidade."""
    if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
        messages.error(request, 'Você precisa estar vinculado a uma contabilidade.')
        return redirect('contabilidade:dashboard')
    
    canais = CanalWhatsApp.objects.filter(
        contabilidade=request.user.contabilidade,
        is_active=True
    ).order_by('-created_at')
    
    # Verificar conexão com Evolution API
    service = EvolutionService()
    evolution_online = service.check_connection()
    
    context = {
        'canais': canais,
        'evolution_online': evolution_online,
    }
    return render(request, 'whatsapp_api/canal_list.html', context)


@login_required
def canal_create(request):
    """Cria novo canal WhatsApp."""
    if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
        messages.error(request, 'Você precisa estar vinculado a uma contabilidade.')
        return redirect('contabilidade:dashboard')
    
    if request.method == 'POST':
        form = CanalWhatsAppForm(request.POST, contabilidade=request.user.contabilidade)
        
        if form.is_valid():
            try:
                # Gerar nome único para instância
                instance_name = f"agentbase_{request.user.contabilidade.id}_{uuid.uuid4().hex[:8]}"
                
                # Criar instância na Evolution API
                service = EvolutionService()
                webhook_url = service.get_webhook_url_for_instance(instance_name)
                
                result = service.create_instance(
                    instance_name=instance_name,
                    webhook_url=webhook_url,
                    qrcode=True
                )
                
                # Salvar canal
                canal = form.save(commit=False)
                canal.contabilidade = request.user.contabilidade
                canal.instance_name = instance_name
                canal.webhook_url = webhook_url
                canal.status = 'qrcode'
                
                # Extrair dados da resposta
                logger.debug(f"Create instance result keys: {result.keys() if isinstance(result, dict) else type(result)}")
                
                if 'instance' in result:
                    canal.instance_id = result['instance'].get('instanceId', '')
                
                # Extrair QR Code usando função auxiliar
                qrcode_base64 = _extract_qrcode_base64(result)
                
                if qrcode_base64:
                    canal.qrcode_base64 = qrcode_base64
                    logger.info(f"QR Code salvo com {len(qrcode_base64)} caracteres")
                else:
                    logger.warning(f"Nenhum QR Code encontrado na resposta: {list(result.keys())}")
                
                canal.save()
                
                messages.success(request, f'Canal "{canal.nome}" criado com sucesso!')
                return redirect('whatsapp_api:canal_qrcode', pk=canal.pk)
                
            except EvolutionAPIError as e:
                logger.error(f"Erro ao criar canal: {e.message}")
                messages.error(request, f'Erro ao criar canal: {e.message}')
                
            except Exception as e:
                logger.exception("Erro inesperado ao criar canal")
                messages.error(request, 'Erro inesperado ao criar canal.')
    else:
        form = CanalWhatsAppForm(contabilidade=request.user.contabilidade)
    
    context = {
        'form': form,
    }
    return render(request, 'whatsapp_api/canal_create.html', context)


@login_required
def canal_detail(request, pk):
    """Exibe detalhes de um canal WhatsApp."""
    if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
        messages.error(request, 'Você precisa estar vinculado a uma contabilidade.')
        return redirect('contabilidade:dashboard')
    
    canal = get_object_or_404(
        CanalWhatsApp,
        pk=pk,
        contabilidade=request.user.contabilidade,
        is_active=True
    )
    
    # Buscar logs recentes
    logs = WebhookLog.objects.filter(canal=canal).order_by('-created_at')[:20]
    
    context = {
        'canal': canal,
        'logs': logs,
    }
    return render(request, 'whatsapp_api/canal_detail.html', context)


@login_required
def canal_qrcode(request, pk):
    """Exibe QR Code para conexão."""
    if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
        messages.error(request, 'Você precisa estar vinculado a uma contabilidade.')
        return redirect('contabilidade:dashboard')
    
    canal = get_object_or_404(
        CanalWhatsApp,
        pk=pk,
        contabilidade=request.user.contabilidade,
        is_active=True
    )
    
    # Se já está conectado, redirecionar para detalhes
    if canal.status == 'connected':
        messages.info(request, 'Este canal já está conectado.')
        return redirect('whatsapp_api:canal_detail', pk=pk)
    
    context = {
        'canal': canal,
    }
    return render(request, 'whatsapp_api/canal_qrcode.html', context)


@login_required
def canal_connect(request, pk):
    """Inicia conexão e gera novo QR Code."""
    if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
        messages.error(request, 'Você precisa estar vinculado a uma contabilidade.')
        return redirect('contabilidade:dashboard')
    
    canal = get_object_or_404(
        CanalWhatsApp,
        pk=pk,
        contabilidade=request.user.contabilidade,
        is_active=True
    )
    
    try:
        service = EvolutionService()
        result = service.connect_instance(canal.instance_name)
        
        # Atualizar QR Code usando função auxiliar
        qrcode_base64 = _extract_qrcode_base64(result)
        if qrcode_base64:
            canal.qrcode_base64 = qrcode_base64
        
        canal.status = 'qrcode'
        canal.save()
        
        messages.success(request, 'QR Code gerado! Escaneie com seu WhatsApp.')
        return redirect('whatsapp_api:canal_qrcode', pk=pk)
        
    except EvolutionAPIError as e:
        logger.error(f"Erro ao conectar canal: {e.message}")
        messages.error(request, f'Erro ao conectar: {e.message}')
        return redirect('whatsapp_api:canal_detail', pk=pk)


@login_required
def canal_disconnect(request, pk):
    """Desconecta um canal WhatsApp."""
    if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
        messages.error(request, 'Você precisa estar vinculado a uma contabilidade.')
        return redirect('contabilidade:dashboard')
    
    canal = get_object_or_404(
        CanalWhatsApp,
        pk=pk,
        contabilidade=request.user.contabilidade,
        is_active=True
    )
    
    try:
        service = EvolutionService()
        service.logout_instance(canal.instance_name)
        
        canal.status = 'disconnected'
        canal.phone_number = ''
        canal.qrcode_base64 = ''
        canal.save()
        
        messages.success(request, 'Canal desconectado com sucesso.')
        
    except EvolutionAPIError as e:
        logger.error(f"Erro ao desconectar canal: {e.message}")
        messages.error(request, f'Erro ao desconectar: {e.message}')
    
    return redirect('whatsapp_api:canal_detail', pk=pk)


@login_required
def canal_restart(request, pk):
    """Reinicia um canal WhatsApp."""
    if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
        messages.error(request, 'Você precisa estar vinculado a uma contabilidade.')
        return redirect('contabilidade:dashboard')
    
    canal = get_object_or_404(
        CanalWhatsApp,
        pk=pk,
        contabilidade=request.user.contabilidade,
        is_active=True
    )
    
    try:
        service = EvolutionService()
        service.restart_instance(canal.instance_name)
        
        messages.success(request, 'Canal reiniciado com sucesso.')
        
    except EvolutionAPIError as e:
        logger.error(f"Erro ao reiniciar canal: {e.message}")
        messages.error(request, f'Erro ao reiniciar: {e.message}')
    
    return redirect('whatsapp_api:canal_detail', pk=pk)


@login_required
def canal_delete(request, pk):
    """Exclui um canal WhatsApp."""
    if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
        messages.error(request, 'Você precisa estar vinculado a uma contabilidade.')
        return redirect('contabilidade:dashboard')
    
    canal = get_object_or_404(
        CanalWhatsApp,
        pk=pk,
        contabilidade=request.user.contabilidade,
        is_active=True
    )
    
    if request.method == 'POST':
        try:
            # Remover da Evolution API
            service = EvolutionService()
            try:
                service.delete_instance(canal.instance_name)
            except EvolutionAPIError:
                pass  # Continuar mesmo se falhar na Evolution
            
            # Soft delete
            canal.is_active = False
            canal.save()
            
            messages.success(request, f'Canal "{canal.nome}" excluído com sucesso.')
            return redirect('whatsapp_api:canal_list')
            
        except Exception as e:
            logger.exception("Erro ao excluir canal")
            messages.error(request, 'Erro ao excluir canal.')
    
    context = {
        'canal': canal,
    }
    return render(request, 'whatsapp_api/canal_delete.html', context)


@login_required
def canal_status(request, pk):
    """Retorna status atual do canal (AJAX)."""
    if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
        return JsonResponse({'error': 'Não autorizado'}, status=403)
    
    canal = get_object_or_404(
        CanalWhatsApp,
        pk=pk,
        contabilidade=request.user.contabilidade,
        is_active=True
    )
    
    try:
        service = EvolutionService()
        result = service.get_connection_state(canal.instance_name)
        
        # Mapear estado da Evolution para nosso status
        state = result.get('state', result.get('instance', {}).get('state', 'close'))
        
        status_map = {
            'open': 'connected',
            'close': 'disconnected',
            'connecting': 'connecting',
        }
        
        new_status = status_map.get(state, 'disconnected')
        
        # Atualizar se mudou
        if canal.status != new_status:
            canal.status = new_status
            canal.save(update_fields=['status', 'updated_at'])
        
        return JsonResponse({
            'status': new_status,
            'status_display': canal.get_status_display(),
            'phone_number': canal.phone_number,
            'is_connected': canal.is_connected,
        })
        
    except EvolutionAPIError as e:
        return JsonResponse({
            'status': 'error',
            'error': e.message
        }, status=500)


@login_required
def canal_refresh_qrcode(request, pk):
    """Atualiza QR Code (AJAX)."""
    if not hasattr(request.user, 'contabilidade') or not request.user.contabilidade:
        return JsonResponse({'error': 'Não autorizado'}, status=403)
    
    canal = get_object_or_404(
        CanalWhatsApp,
        pk=pk,
        contabilidade=request.user.contabilidade,
        is_active=True
    )
    
    try:
        service = EvolutionService()
        result = service.connect_instance(canal.instance_name)
        
        # Extrair QR Code usando função auxiliar
        qrcode_base64 = _extract_qrcode_base64(result)
        
        if qrcode_base64:
            canal.qrcode_base64 = qrcode_base64
            canal.status = 'qrcode'
            canal.save()
        
        return JsonResponse({
            'success': True,
            'qrcode_base64': qrcode_base64,
        })
        
    except EvolutionAPIError as e:
        return JsonResponse({
            'success': False,
            'error': e.message
        }, status=500)


# ==================== WEBHOOK ====================

@csrf_exempt
@require_POST
def webhook_receiver(request, instance_name):
    """
    Recebe eventos da Evolution API via webhook.
    
    Eventos tratados:
    - MESSAGES_UPSERT: Nova mensagem recebida
    - CONNECTION_UPDATE: Mudança no status da conexão
    - QRCODE_UPDATED: Novo QR Code gerado
    """

    logger.info(f"\n\n\n Webhook recebido para {instance_name}\n\n\n")
    try:
        # Parse do payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning(f"Webhook payload inválido: {request.body[:200]}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        # Extrair tipo do evento e normalizar (Evolution API pode enviar em formatos diferentes)
        event_type_raw = payload.get('event', 'UNKNOWN')
        # Normalizar: messages.upsert -> MESSAGES_UPSERT, connection.update -> CONNECTION_UPDATE
        event_type = event_type_raw.upper().replace('.', '_')
        
        logger.info(f"Webhook recebido: {event_type_raw} -> {event_type} para {instance_name}")
        
        # Buscar canal
        canal = CanalWhatsApp.objects.filter(
            instance_name=instance_name,
            is_active=True
        ).first()
        
        # Criar log do webhook
        webhook_log = WebhookLog.objects.create(
            canal=canal,
            event_type=event_type,
            instance_name=instance_name,
            payload=payload,
            processed=False
        )
        
        # Processar evento
        try:
            if event_type == 'MESSAGES_UPSERT':
                _handle_message_event(canal, payload, webhook_log)
            
            elif event_type == 'CONNECTION_UPDATE':
                _handle_connection_event(canal, payload, webhook_log)
            
            elif event_type == 'QRCODE_UPDATED':
                _handle_qrcode_event(canal, payload, webhook_log)
            
            else:
                logger.debug(f"Evento não tratado: {event_type}")
                webhook_log.processed = True
                webhook_log.save()
        
        except Exception as e:
            logger.exception(f"Erro ao processar evento {event_type}")
            webhook_log.error_message = str(e)
            webhook_log.save()
        
        return JsonResponse({'status': 'ok'})
        
    except Exception as e:
        logger.exception("Erro no webhook receiver")
        return JsonResponse({'error': str(e)}, status=500)


def _handle_message_event(canal, payload, webhook_log):
    """
    Processa evento de nova mensagem.
    
    Extrai telefone e mensagem, envia para MessageProcessor,
    e responde via WhatsApp.
    """
    data = payload.get('data', {})


    logger.info(f"\n\nProcessando mensagem do webhook para {canal.instance_name if canal else 'instância desconhecida'}\n\n")
    logger.debug(f"\n\nPayload do evento: {json.dumps(payload)[:500]}\n\n")  # Log do payload para debug
    
    # Verificar se é mensagem de grupo (ignorar)
    key = data.get('key', {})
    remote_jid = key.get('remoteJid', '')
    

    logger.debug(f"\n\nRemote JID: {remote_jid}\n\n")

    if '@g.us' in remote_jid:
        logger.debug(f"Mensagem de grupo ignorada: {remote_jid}")
        webhook_log.processed = True
        webhook_log.save()
        return
    
    # Verificar se é mensagem própria (ignorar)
    if key.get('fromMe', False):
        logger.debug("Mensagem própria ignorada")
        webhook_log.processed = True
        webhook_log.save()
        return
    
    # Extrair telefone
    # Primeiro tenta do remoteJid, mas se for @lid (linked ID), usa o campo 'sender'
    if '@lid' in remote_jid:
        # Formato @lid é um ID interno, o número real está em 'sender'
        sender = key.get('senderPn', '')
        phone = sender.replace('@s.whatsapp.net', '').replace('@lid', '')
        logger.debug(f"Convertido @lid para sender: {remote_jid} -> {phone}")
    else:
        phone = remote_jid.replace('@s.whatsapp.net', '')
    
    logger.debug(f"\n\nMensagem recebida de {phone}\n\n")
    
    # Extrair mensagem
    message_data = data.get('message', {})
    message_text = (
        message_data.get('conversation') or
        message_data.get('extendedTextMessage', {}).get('text') or
        ''
    )
    
    if not message_text:
        logger.debug("Mensagem sem texto ignorada")
        webhook_log.processed = True
        webhook_log.save()
        return
    
    # Atualizar log
    webhook_log.phone_from = phone
    webhook_log.message_text = message_text
    
    logger.info(f"Mensagem recebida de {phone}: {message_text[:50]}...")
    
    # Processar com MessageProcessor
    try:
        processor = MessageProcessor()
        response_text = processor.process(phone, message_text)
        
        webhook_log.response_text = response_text
        webhook_log.processed = True
        webhook_log.save()
        
        # Enviar resposta via WhatsApp
        if canal and response_text:
            try:
                service = EvolutionService()
                service.send_text_message(
                    instance_name=canal.instance_name,
                    phone_number=phone,
                    message=response_text
                )
                logger.info(f"Resposta enviada para {phone}")
            except EvolutionAPIError as e:
                logger.error(f"Erro ao enviar resposta: {e.message}")
                webhook_log.error_message = f"Erro ao enviar: {e.message}"
                webhook_log.save()
        
    except Exception as e:
        logger.exception(f"Erro ao processar mensagem de {phone}")
        webhook_log.error_message = str(e)
        webhook_log.save()


def _handle_connection_event(canal, payload, webhook_log):
    """
    Processa evento de mudança de conexão.
    
    Atualiza status do canal conforme estado reportado.
    """
    if not canal:
        webhook_log.processed = True
        webhook_log.save()
        return
    
    data = payload.get('data', {})
    state = data.get('state', '')
    
    # Mapear estado
    status_map = {
        'open': 'connected',
        'close': 'disconnected',
        'connecting': 'connecting',
    }
    
    new_status = status_map.get(state)
    
    if new_status:
        canal.status = new_status
        
        # Extrair número se conectado
        if new_status == 'connected':
            instance_data = data.get('instance', {})
            owner = instance_data.get('owner', '')
            if owner:
                canal.phone_number = owner.replace('@s.whatsapp.net', '')
        
        canal.save()
        logger.info(f"Canal {canal.instance_name} status: {new_status}")
    
    webhook_log.processed = True
    webhook_log.save()


def _handle_qrcode_event(canal, payload, webhook_log):
    """
    Processa evento de novo QR Code.
    
    Atualiza QR Code no canal para exibição.
    """
    if not canal:
        webhook_log.processed = True
        webhook_log.save()
        return
    
    data = payload.get('data', {})
    
    # Extrair QR Code usando função auxiliar
    # A estrutura do webhook pode ser diferente, então tentamos do 'data' primeiro
    base64_code = _extract_qrcode_base64(data)
    
    # Se não encontrou, tenta diretamente do payload
    if not base64_code:
        base64_code = _extract_qrcode_base64(payload)
    
    if base64_code:
        canal.qrcode_base64 = base64_code
        canal.status = 'qrcode'
        canal.save()
        logger.info(f"QR Code atualizado para {canal.instance_name}")
    
    webhook_log.processed = True
    webhook_log.save()

