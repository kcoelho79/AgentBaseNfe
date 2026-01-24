from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from django.contrib import messages
from django.shortcuts import redirect
import json
import logging
import httpx
from django.views.generic import (
    TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView, View
)
from apps.nfse.models import NFSeProcessada, NFSeEmissao, ClienteTomador
from apps.contabilidade.models import Empresa
from apps.nfse.services.receita_federal import ReceitaFederalService

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


class ClienteTomadorListView(LoginRequiredMixin, ListView):
    """Lista clientes tomadores com filtros."""
    model = ClienteTomador
    template_name = 'nfse/tomador_list.html'
    context_object_name = 'tomadores'
    paginate_by = 20
    
    def get_queryset(self):
        """Aplica filtros de busca e anota quantidade de notas."""
        queryset = ClienteTomador.objects.annotate(
            total_notas=Count('nfse_recebidas')
        ).order_by('-created_at')
        
        # Filtro por CNPJ
        cnpj = self.request.GET.get('cnpj', '').strip()
        if cnpj:
            queryset = queryset.filter(cnpj__icontains=cnpj)
        
        # Filtro por razão social
        razao_social = self.request.GET.get('razao_social', '').strip()
        if razao_social:
            queryset = queryset.filter(
                Q(razao_social__icontains=razao_social) |
                Q(nome_fantasia__icontains=razao_social)
            )
        
        # Filtro por cidade
        cidade = self.request.GET.get('cidade', '').strip()
        if cidade:
            queryset = queryset.filter(cidade__icontains=cidade)
        
        # Filtro por estado
        estado = self.request.GET.get('estado', '').strip()
        if estado:
            queryset = queryset.filter(estado__iexact=estado)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Adiciona estatísticas ao contexto."""
        context = super().get_context_data(**kwargs)
        
        # Listar estados únicos para filtro
        context['estados'] = ClienteTomador.objects.values_list(
            'estado', flat=True
        ).distinct().order_by('estado')
        
        # Estatísticas gerais
        context['total_tomadores'] = ClienteTomador.objects.count()
        
        return context


class ConsultaReceitaFederalView(LoginRequiredMixin, TemplateView):
    """View para consultar CNPJ na Receita Federal."""
    template_name = 'nfse/consulta_cnpj.html'
    
    def post(self, request, *args, **kwargs):
        """Processa consulta de CNPJ."""
        cnpj = request.POST.get('cnpj', '').strip()
        acao = request.POST.get('acao', '')  # 'consultar' ou 'adicionar'
        
        if not cnpj:
            messages.error(request, 'CNPJ é obrigatório')
            return self.get(request, *args, **kwargs)
        
        # Limpar CNPJ
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        
        if len(cnpj_limpo) != 14:
            messages.error(request, 'CNPJ inválido. Deve conter 14 dígitos.')
            return self.get(request, *args, **kwargs)
        
        try:
            # Ação: Adicionar cliente tomador
            if acao == 'adicionar':
                # Verifica se já existe
                tomador_existente = ClienteTomador.objects.filter(cnpj=cnpj_limpo).first()
                if tomador_existente:
                    messages.warning(
                        request, 
                        f'Cliente {tomador_existente.razao_social} já está cadastrado!'
                    )
                    return redirect('nfse:tomador_list')
                
                # Consulta e cria
                tomador = ReceitaFederalService.buscar_ou_criar_tomador(cnpj_limpo)
                messages.success(
                    request, 
                    f'Cliente {tomador.razao_social} adicionado com sucesso!'
                )
                return redirect('nfse:tomador_list')
            
            # Ação padrão: Apenas consultar
            dados = ReceitaFederalService.consultar_cnpj(cnpj_limpo)
            
            # Verifica se já está cadastrado
            ja_cadastrado = ClienteTomador.objects.filter(cnpj=cnpj_limpo).exists()
            
            # Estrutura dados para exibição
            dados_formatados = {
                'cnpj': cnpj_limpo,
                'cnpj_formatado': f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}",
                'razao_social': dados.get('razao_social', '-'),
                'nome_fantasia': dados.get('nome_fantasia', '-'),
                'situacao_cadastral': dados.get('descricao_situacao_cadastral', '-'),
                'data_situacao': dados.get('data_situacao_cadastral', '-'),
                'tipo': dados.get('descricao_tipo_de_logradouro', '') + ' ' + dados.get('logradouro', ''),
                'numero': dados.get('numero', '-'),
                'complemento': dados.get('complemento', '-'),
                'bairro': dados.get('bairro', '-'),
                'cep': dados.get('cep', '-'),
                'municipio': dados.get('municipio', '-'),
                'uf': dados.get('uf', '-'),
                'email': dados.get('email', '-'),
                'telefone': dados.get('ddd_telefone_1', '-'),
                'natureza_juridica': dados.get('natureza_juridica', '-'),
                'capital_social': dados.get('capital_social', '-'),
                'porte': dados.get('porte', '-'),
                'cnae_principal': dados.get('cnae_fiscal_descricao', '-'),
                'data_abertura': dados.get('data_inicio_atividade', '-'),
                'ja_cadastrado': ja_cadastrado,
            }
            
            messages.success(request, 'CNPJ consultado com sucesso!')
            
            context = self.get_context_data(**kwargs)
            context['dados'] = dados_formatados
            context['cnpj_pesquisado'] = cnpj
            
            return self.render_to_response(context)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                messages.error(request, 'CNPJ não encontrado na Receita Federal')
            else:
                messages.error(request, f'Erro ao consultar CNPJ: {e.response.status_code}')
            logger.exception(f"Erro HTTP ao consultar CNPJ {cnpj_limpo}")
            
        except Exception as e:
            messages.error(request, f'Erro ao consultar CNPJ: {str(e)}')
            logger.exception(f"Erro ao consultar CNPJ {cnpj_limpo}")
        
        return self.get(request, *args, **kwargs)