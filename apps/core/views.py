from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import logging
import os
import time
from datetime import datetime, timedelta
from apps.core.message_gateway import MessageGateway

logger = logging.getLogger(__name__)

# Armazenamento em memória para sessões de log ativas
# Formato: {session_id: {'start_time': datetime, 'start_marker': str, 'phone': str}}
LOG_SESSIONS = {}
LOG_SESSION_COUNTER = 0

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


# ==================== LOG VIEWER ====================

@require_http_methods(["GET"])
def get_logs(request):
    """
    Retorna as últimas linhas do arquivo debug.log.
    
    Query params:
        lines: número de linhas (default: 50, max: 200)
        phone: filtrar logs que contenham este telefone (opcional)
    """
    try:
        lines = min(int(request.GET.get('lines', 50)), 200)
        phone_filter = request.GET.get('phone', '').strip()
        
        # Caminho do arquivo de log
        log_path = os.path.join(settings.BASE_DIR, 'logs', 'debug.log')
        
        if not os.path.exists(log_path):
            return JsonResponse({
                'status': 'ok',
                'logs': ['Arquivo de log não encontrado'],
                'count': 0
            })
        
        # Ler arquivo
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
        
        # Filtrar por telefone se especificado
        if phone_filter:
            filtered_lines = [
                line for line in all_lines 
                if phone_filter in line
            ]
            last_lines = filtered_lines[-lines:] if len(filtered_lines) > lines else filtered_lines
        else:
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Limpar linhas
        logs = [line.strip() for line in last_lines if line.strip()]
        
        return JsonResponse({
            'status': 'ok',
            'logs': logs,
            'count': len(logs),
            'filter': phone_filter or None
        })
        
    except Exception as e:
        logger.exception('Erro ao ler logs')
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'logs': []
        }, status=500)


# ==================== LOG SESSION (START/STOP) ====================

@csrf_exempt
@require_http_methods(["POST"])
def start_log_session(request):
    """
    Inicia uma sessão de captura de logs.
    Insere uma marcação no debug.log e retorna o session_id.
    """
    global LOG_SESSION_COUNTER
    
    try:
        data = json.loads(request.body) if request.body else {}
        phone = data.get('phone', '')
        
        # Gerar ID da sessão
        LOG_SESSION_COUNTER += 1
        session_id = f"LOG_{LOG_SESSION_COUNTER}"
        
        # Criar marcação
        now = datetime.now()
        start_marker = f"===== LOG_SESSION_START | ID:{session_id} | TIME:{now.strftime('%Y-%m-%d %H:%M:%S.%f')} | PHONE:{phone} ====="
        
        # Inserir marcação no log
        logger.info(start_marker)
        
        # Salvar sessão
        LOG_SESSIONS[session_id] = {
            'start_time': now,
            'start_marker': start_marker,
            'phone': phone
        }
        
        return JsonResponse({
            'status': 'ok',
            'session_id': session_id,
            'start_time': now.isoformat(),
            'message': 'Sessão de log iniciada'
        })
        
    except Exception as e:
        logger.exception('Erro ao iniciar sessão de log')
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def stop_log_session(request):
    """
    Finaliza uma sessão de captura de logs.
    Insere marcação de fim e retorna todos os logs entre as marcações.
    
    Limites:
    - Máximo 50 mensagens
    - Máximo 10 minutos
    """
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if not session_id or session_id not in LOG_SESSIONS:
            return JsonResponse({
                'status': 'error',
                'error': 'Sessão não encontrada'
            }, status=404)
        
        session = LOG_SESSIONS[session_id]
        now = datetime.now()
        
        # Verificar limite de tempo (10 minutos)
        elapsed = now - session['start_time']
        if elapsed > timedelta(minutes=10):
            del LOG_SESSIONS[session_id]
            return JsonResponse({
                'status': 'error',
                'error': 'Sessão expirada (máximo 10 minutos)',
                'discarded': True
            })
        
        # Criar marcação de fim
        end_marker = f"===== LOG_SESSION_END | ID:{session_id} | TIME:{now.strftime('%Y-%m-%d %H:%M:%S.%f')} ====="
        logger.info(end_marker)
        
        # Ler arquivo de log e extrair linhas entre as marcações
        log_path = os.path.join(settings.BASE_DIR, 'logs', 'debug.log')
        
        if not os.path.exists(log_path):
            del LOG_SESSIONS[session_id]
            return JsonResponse({
                'status': 'error',
                'error': 'Arquivo de log não encontrado'
            })
        
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
        
        # Encontrar linhas entre as marcações
        start_marker = session['start_marker']
        capturing = False
        captured_logs = []
        
        for line in all_lines:
            line_stripped = line.strip()
            
            if start_marker in line_stripped:
                capturing = True
                continue
            
            if end_marker in line_stripped:
                break
            
            if capturing and line_stripped:
                captured_logs.append(line_stripped)
        
        # Remover sessão
        del LOG_SESSIONS[session_id]
        
        # Verificar limite de mensagens (50)
        if len(captured_logs) > 50:
            return JsonResponse({
                'status': 'error',
                'error': f'Limite excedido ({len(captured_logs)} mensagens, máximo 50)',
                'discarded': True
            })
        
        return JsonResponse({
            'status': 'ok',
            'session_id': session_id,
            'logs': captured_logs,
            'count': len(captured_logs),
            'duration_seconds': elapsed.total_seconds()
        })
        
    except Exception as e:
        logger.exception('Erro ao finalizar sessão de log')
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def cancel_log_session(request):
    """Cancela uma sessão de log sem capturar."""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if session_id and session_id in LOG_SESSIONS:
            del LOG_SESSIONS[session_id]
        
        return JsonResponse({
            'status': 'ok',
            'message': 'Sessão cancelada'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


# ==================== AI TEST SIMULATION ====================

@require_http_methods(["GET"])
def list_ai_scenarios(request):
    """Lista cenários de teste disponíveis."""
    try:
        from apps.core.tests.ai_test_client import SCENARIOS
        
        scenarios = []
        for key, scenario in SCENARIOS.items():
            scenarios.append({
                'id': key,
                'name': scenario.name,
                'description': scenario.description,
                'max_turns': scenario.max_turns
            })
        
        return JsonResponse({
            'status': 'ok',
            'scenarios': scenarios
        })
        
    except Exception as e:
        logger.exception('Erro ao listar cenários')
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def run_ai_scenario(request):
    """
    Executa um cenário de teste de IA e retorna resultado via streaming.
    """
    try:
        data = json.loads(request.body)
        scenario_id = data.get('scenario_id')
        telefone = data.get('telefone', '5500000000001')
        
        if not scenario_id:
            return JsonResponse(
                {'error': 'scenario_id obrigatório'},
                status=400
            )
        
        from apps.core.tests.ai_test_client import AITestClient, SCENARIOS
        
        if scenario_id not in SCENARIOS:
            return JsonResponse(
                {'error': f'Cenário não encontrado: {scenario_id}'},
                status=404
            )
        
        scenario = SCENARIOS[scenario_id]
        
        # Executar teste
        client = AITestClient(base_url="http://localhost:8000")
        try:
            execution = client.run_scenario(scenario, telefone)
            
            # Montar resultado
            conversation = []
            for turn in execution.conversation:
                conversation.append({
                    'turn': turn.turn_number,
                    'user': turn.user_message,
                    'bot': turn.bot_response
                })
            
            return JsonResponse({
                'status': 'ok',
                'scenario': scenario.name,
                'result': execution.result.value,
                'final_state': execution.final_state,
                'total_turns': execution.total_turns,
                'error_message': execution.error_message,
                'conversation': conversation
            })
            
        finally:
            client.close()
        
    except Exception as e:
        logger.exception('Erro ao executar cenário de IA')
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def run_ai_scenario_stream(request):
    """
    Executa cenário de teste com streaming - envia cada turno em tempo real.
    """
    try:
        data = json.loads(request.body)
        scenario_id = data.get('scenario_id')
        telefone = data.get('telefone', '5500000000001')
        
        if not scenario_id:
            return JsonResponse(
                {'error': 'scenario_id obrigatório'},
                status=400
            )
        
        from apps.core.tests.ai_test_client import SCENARIOS
        
        if scenario_id not in SCENARIOS:
            return JsonResponse(
                {'error': f'Cenário não encontrado: {scenario_id}'},
                status=404
            )
        
        def generate():
            from apps.core.tests.ai_test_client import AITestClient, TestResult
            
            scenario = SCENARIOS[scenario_id]
            client = AITestClient(base_url="http://localhost:8000")
            
            try:
                # Enviar info inicial
                yield f"data: {json.dumps({'type': 'start', 'scenario': scenario.name, 'description': scenario.description})}\n\n"
                
                # Limpar sessão
                client._clear_session(telefone)
                
                conversation_history = []
                last_bot_response = None
                final_result = TestResult.TIMEOUT
                final_state = None
                error_message = None
                
                for turn in range(scenario.max_turns):
                    # Gerar mensagem do usuário
                    user_message = client._generate_user_message(
                        scenario,
                        conversation_history,
                        last_bot_response
                    )
                    
                    # Enviar user message
                    yield f"data: {json.dumps({'type': 'user', 'turn': turn + 1, 'message': user_message})}\n\n"
                    time.sleep(0.5)  # Delay para visualização
                    
                    # Enviar para o sistema
                    response = client._send_message(telefone, user_message)
                    bot_response = response.get("resposta", "")
                    
                    # Enviar bot response
                    yield f"data: {json.dumps({'type': 'bot', 'turn': turn + 1, 'message': bot_response})}\n\n"
                    time.sleep(0.5)
                    
                    # Guardar histórico
                    conversation_history.append({
                        "user": user_message,
                        "bot": bot_response
                    })
                    last_bot_response = bot_response
                    
                    # Verificar se chegou na confirmação
                    if client._check_confirmation_request(bot_response):
                        final_state = "aguardando_confirmacao"
                        
                        if scenario.should_confirm:
                            # Confirmar
                            yield f"data: {json.dumps({'type': 'user', 'turn': turn + 2, 'message': 'sim'})}\n\n"
                            time.sleep(0.5)
                            
                            confirm_response = client._send_message(telefone, "sim")
                            confirm_text = confirm_response.get("resposta", "")
                            
                            yield f"data: {json.dumps({'type': 'bot', 'turn': turn + 2, 'message': confirm_text})}\n\n"
                            
                            if client._check_processing(confirm_text):
                                final_state = "processando"
                                final_result = TestResult.SUCCESS
                            else:
                                final_result = TestResult.FAILED
                                error_message = "Confirmação não gerou processamento"
                        else:
                            final_result = TestResult.SUCCESS
                        break
                    
                    # Verificar se já está processando
                    if client._check_processing(bot_response):
                        final_state = "processando"
                        final_result = TestResult.SUCCESS
                        break
                
                else:
                    error_message = f"Atingiu limite de {scenario.max_turns} turnos"
                
                # Enviar resultado final
                yield f"data: {json.dumps({'type': 'end', 'result': final_result.value, 'final_state': final_state, 'error': error_message})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            finally:
                client._clear_session(telefone)
                client.close()
        
        response = StreamingHttpResponse(
            generate(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
        
    except Exception as e:
        logger.exception('Erro ao executar cenário de IA')
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
