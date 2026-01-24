from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
import json
import logging
from django.views.generic import (
    TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView, View
)
from apps.nfse.models import NFSeProcessada, NFSeEmissao, ClienteTomador
from apps.contabilidade.models import Empresa

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


class NotaFiscalEmissaoListView(LoginRequiredMixin, ListView):
    """Lista emissões de NFSe com filtros."""
    model = NFSeEmissao
    template_name = 'nfse/emissao_list.html'
    context_object_name = 'nfse'
    paginate_by = 20
    
    def get_queryset(self):
        """Aplica filtros de busca."""
        contabilidade = self.request.user.contabilidade
        
        # Base queryset com joins otimizados
        qs = NFSeEmissao.objects.select_related(
            'prestador',
            'tomador',
            'session',
            'nota_processada'
        ).filter(
            prestador__contabilidade=contabilidade
        )
        
        # Filtro: Prestador
        prestador_id = self.request.GET.get('prestador')
        if prestador_id:
            qs = qs.filter(prestador_id=prestador_id)
        
        # Filtro: Tomador (CNPJ ou Razão Social)
        tomador = self.request.GET.get('tomador')
        if tomador:
            qs = qs.filter(
                Q(tomador__cnpj__icontains=tomador) |
                Q(tomador__razao_social__icontains=tomador)
            )
        
        # Filtro: Sessão/ID Integração
        session = self.request.GET.get('session')
        if session:
            qs = qs.filter(
                Q(id_integracao__icontains=session) |
                Q(session__sessao_id__icontains=session)
            )
        
        # Filtro: Status
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        
        return qs.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """Adiciona dados para os filtros."""
        context = super().get_context_data(**kwargs)
        contabilidade = self.request.user.contabilidade
        
        # Lista de prestadores para o select
        context['prestadores'] = Empresa.objects.filter(
            contabilidade=contabilidade,
            is_active=True
        ).order_by('razao_social')
        
        return context


class NotaFiscalProcessadaListView(LoginRequiredMixin, ListView):
    """Lista NFSe Processadas (autorizadas) com filtros."""
    model = NFSeProcessada
    template_name = 'nfse/processada_list.html'
    context_object_name = 'notas'
    paginate_by = 20
    
    def get_queryset(self):
        """Aplica filtros de busca."""
        contabilidade = self.request.user.contabilidade
        
        # Base queryset com joins otimizados
        qs = NFSeProcessada.objects.select_related(
            'emissao__prestador',
            'emissao__tomador',
            'emissao__session'
        ).filter(
            emissao__prestador__contabilidade=contabilidade
        )
        
        # Filtro: Prestador (emitente)
        prestador_id = self.request.GET.get('prestador')
        if prestador_id:
            qs = qs.filter(emissao__prestador_id=prestador_id)
        
        # Filtro: Tomador (CNPJ ou Razão Social)
        tomador = self.request.GET.get('tomador')
        if tomador:
            qs = qs.filter(
                Q(emissao__tomador__cnpj__icontains=tomador) |
                Q(emissao__tomador__razao_social__icontains=tomador)
            )
        
        # Filtro: Número da nota
        numero = self.request.GET.get('numero')
        if numero:
            qs = qs.filter(numero__icontains=numero)
        
        # Filtro: Período
        data_inicio = self.request.GET.get('data_inicio')
        data_fim = self.request.GET.get('data_fim')
        if data_inicio:
            qs = qs.filter(data_emissao__gte=data_inicio)
        if data_fim:
            qs = qs.filter(data_emissao__lte=data_fim)
        
        return qs.order_by('-data_emissao', '-numero')
    
    def get_context_data(self, **kwargs):
        """Adiciona dados para os filtros."""
        context = super().get_context_data(**kwargs)
        contabilidade = self.request.user.contabilidade
        
        # Lista de prestadores para o select
        context['prestadores'] = Empresa.objects.filter(
            contabilidade=contabilidade,
            is_active=True
        ).order_by('razao_social')
        
        return context