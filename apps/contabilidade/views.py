from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import (
    TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView, View
)
from datetime import timedelta
import logging

from .mixins import TenantMixin, EmpresaContextMixin
from .models import Empresa, UsuarioEmpresa, Certificado
from .forms import EmpresaForm, UsuarioEmpresaForm, CertificadoForm
from apps.account.forms import UserForm
from apps.nfse.services.receita_federal import ReceitaFederalService

User = get_user_model()
logger = logging.getLogger(__name__)


# =============================================================================
# Dashboard
# =============================================================================

class DashboardView(LoginRequiredMixin, TemplateView):
    '''Dashboard principal com métricas.'''
    template_name = 'contabilidade/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contabilidade = self.request.user.contabilidade

        # Inicializa valores padrão
        context['hoje'] = timezone.now().date()
        context['total_empresas'] = 0
        context['certificados_vencendo'] = 0
        context['total_usuarios_empresas'] = 0
        context['total_notas'] = 0
        context['sessoes_ativas'] = 0
        context['sessoes_recentes'] = []
        context['certificados_lista'] = []

        if contabilidade:
            from apps.nfse.models import NFSeEmissao
            from apps.core.db_models import SessionSnapshot
            from apps.core.states import SessionState
            
            hoje = context['hoje']

            # Métricas básicas
            context['total_empresas'] = Empresa.objects.filter(
                contabilidade=contabilidade,
                is_active=True
            ).count()

            context['certificados_vencendo'] = Certificado.objects.filter(
                empresa__contabilidade=contabilidade,
                validade__lte=hoje + timedelta(days=30),
                validade__gte=hoje,
                is_active=True
            ).count()

            context['total_usuarios_empresas'] = UsuarioEmpresa.objects.filter(
                empresa__contabilidade=contabilidade,
                is_active=True
            ).count()

            # Total de notas emitidas de todas as empresas da contabilidade
            context['total_notas'] = NFSeEmissao.objects.filter(
                prestador__contabilidade=contabilidade
            ).count()

            # Total de sessões ativas (estados não finalizados)
            context['sessoes_ativas'] = SessionSnapshot.objects.filter(
                empresa_id__in=Empresa.objects.filter(
                    contabilidade=contabilidade
                ).values_list('id', flat=True),
                estado__in=SessionState.active_states()
            ).count()

            # Sessões recentes (últimas 10)
            context['sessoes_recentes'] = SessionSnapshot.objects.filter(
                empresa_id__in=Empresa.objects.filter(
                    contabilidade=contabilidade
                ).values_list('id', flat=True)
            ).order_by('-session_updated_at')[:10]

            # Lista de certificados vencendo (para alertas)
            context['certificados_lista'] = Certificado.objects.filter(
                empresa__contabilidade=contabilidade,
                validade__lte=hoje + timedelta(days=30),
                validade__gte=hoje,
                is_active=True
            ).select_related('empresa').order_by('validade')[:5]

        return context


# =============================================================================
# Empresas
# =============================================================================

class EmpresaListView(TenantMixin, ListView):
    '''Listagem de empresas.'''
    model = Empresa
    template_name = 'contabilidade/empresa/list.html'
    context_object_name = 'empresas'
    paginate_by = 20

    def get_queryset(self):
        from django.db.models import Count, Q
        from apps.core.db_models import SessionSnapshot
        
        # IMPORTANTE: super() chama TenantMixin que filtra por contabilidade
        qs = super().get_queryset()
        
        # Filtro de busca
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(razao_social__icontains=search) | 
                Q(cpf_cnpj__icontains=search) |
                Q(nome_fantasia__icontains=search)
            )
        
        # Filtro de status
        status = self.request.GET.get('status')
        if status == '1':
            qs = qs.filter(is_active=True)
        elif status == '0':
            qs = qs.filter(is_active=False)
        
        # Anotar com totalizadores via annotate (otimizado)
        qs = qs.annotate(
            total_usuarios=Count('usuarios_autorizados', distinct=True),
            total_clientes=Count('clientes_tomadores_vinculados', distinct=True),
            total_notas=Count('nfse_emitidas', distinct=True)
        )
        
        # Adicionar contagem de sessões via empresa_id
        empresas = list(qs)
        
        if empresas:
            # Pega IDs das empresas
            empresa_ids = [empresa.id for empresa in empresas]
            empresa_dict = {empresa.id: empresa for empresa in empresas}
            
            # Inicializa contador
            for empresa in empresas:
                empresa.total_sessoes = 0
            
            # Busca sessões por empresa_id
            sessoes_count = SessionSnapshot.objects.filter(
                empresa_id__in=empresa_ids
            ).values('empresa_id').annotate(total=Count('id'))
            
            # Mapeia contagem de volta para as empresas
            for sessao in sessoes_count:
                empresa_id = sessao['empresa_id']
                if empresa_id in empresa_dict:
                    empresa_dict[empresa_id].total_sessoes = sessao['total']
        
        return empresas


class EmpresaCreateView(TenantMixin, CreateView):
    '''Cadastro de empresa.'''
    model = Empresa
    form_class = EmpresaForm
    template_name = 'contabilidade/empresa/form.html'
    success_url = reverse_lazy('contabilidade:empresa_list')

    def form_valid(self, form):
        form.instance.contabilidade = self.request.user.contabilidade
        messages.success(self.request, 'Empresa cadastrada com sucesso!')
        return super().form_valid(form)


class EmpresaDetailView(TenantMixin, DetailView):
    '''Detalhe da empresa com submenu.'''
    model = Empresa
    template_name = 'contabilidade/empresa/detail.html'
    context_object_name = 'empresa'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_usuarios'] = self.object.usuarios_autorizados.filter(is_active=True).count()
        context['total_certificados'] = self.object.certificados.filter(is_active=True).count()
        return context


class EmpresaUpdateView(TenantMixin, UpdateView):
    '''Edição de empresa.'''
    model = Empresa
    form_class = EmpresaForm
    template_name = 'contabilidade/empresa/form.html'

    def get_success_url(self):
        messages.success(self.request, 'Empresa atualizada com sucesso!')
        return reverse_lazy('contabilidade:empresa_detail', kwargs={'pk': self.object.pk})


class EmpresaDeleteView(TenantMixin, DeleteView):
    '''Exclusão de empresa.'''
    model = Empresa
    template_name = 'contabilidade/empresa/confirm_delete.html'
    success_url = reverse_lazy('contabilidade:empresa_list')

    def form_valid(self, form):
        messages.success(self.request, 'Empresa excluída com sucesso!')
        return super().form_valid(form)


# =============================================================================
# Usuários da Empresa
# =============================================================================

class UsuarioEmpresaListView(EmpresaContextMixin, ListView):
    '''Listagem de usuários da empresa.'''
    model = UsuarioEmpresa
    template_name = 'contabilidade/empresa/usuario_list.html'
    context_object_name = 'usuarios'
    paginate_by = 20


class UsuarioEmpresaCreateView(EmpresaContextMixin, CreateView):
    '''Cadastro de usuário da empresa.'''
    model = UsuarioEmpresa
    form_class = UsuarioEmpresaForm
    template_name = 'contabilidade/empresa/usuario_form.html'

    def get_success_url(self):
        messages.success(self.request, 'Usuário cadastrado com sucesso!')
        return reverse('contabilidade:usuario_empresa_list', kwargs={'empresa_pk': self.kwargs['empresa_pk']})


class UsuarioEmpresaUpdateView(EmpresaContextMixin, UpdateView):
    '''Edição de usuário da empresa.'''
    model = UsuarioEmpresa
    form_class = UsuarioEmpresaForm
    template_name = 'contabilidade/empresa/usuario_form.html'

    def get_success_url(self):
        messages.success(self.request, 'Usuário atualizado com sucesso!')
        return reverse('contabilidade:usuario_empresa_list', kwargs={'empresa_pk': self.kwargs['empresa_pk']})


class UsuarioEmpresaDeleteView(EmpresaContextMixin, DeleteView):
    '''Exclusão de usuário da empresa.'''
    model = UsuarioEmpresa
    template_name = 'contabilidade/empresa/usuario_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, 'Usuário excluído com sucesso!')
        return reverse('contabilidade:usuario_empresa_list', kwargs={'empresa_pk': self.kwargs['empresa_pk']})


# =============================================================================
# Certificados
# =============================================================================

class CertificadoListView(EmpresaContextMixin, ListView):
    '''Listagem de certificados da empresa.'''
    model = Certificado
    template_name = 'contabilidade/empresa/certificado_list.html'
    context_object_name = 'certificados'
    paginate_by = 20


class CertificadoCreateView(EmpresaContextMixin, CreateView):
    '''Upload de certificado digital.'''
    model = Certificado
    form_class = CertificadoForm
    template_name = 'contabilidade/empresa/certificado_form.html'

    def get_success_url(self):
        messages.success(self.request, 'Certificado cadastrado com sucesso!')
        return reverse('contabilidade:certificado_list', kwargs={'empresa_pk': self.kwargs['empresa_pk']})


class CertificadoDetailView(EmpresaContextMixin, DetailView):
    '''Detalhe do certificado.'''
    model = Certificado
    template_name = 'contabilidade/empresa/certificado_detail.html'
    context_object_name = 'certificado'


class CertificadoDeleteView(EmpresaContextMixin, DeleteView):
    '''Exclusão de certificado.'''
    model = Certificado
    template_name = 'contabilidade/empresa/certificado_confirm_delete.html'

    def get_success_url(self):
        messages.success(self.request, 'Certificado excluído com sucesso!')
        return reverse('contabilidade:certificado_list', kwargs={'empresa_pk': self.kwargs['empresa_pk']})


class CertificadoEnviarTecnospeedView(EmpresaContextMixin, View):
    '''Envia certificado para Tecnospeed.'''

    def post(self, request, *args, **kwargs):
        certificado = get_object_or_404(
            Certificado,
            pk=kwargs['pk'],
            empresa__pk=kwargs['empresa_pk'],
            empresa__contabilidade=request.user.contabilidade
        )

        # TODO: Implementar integração com Tecnospeed
        messages.warning(request, 'Integração com Tecnospeed ainda não implementada.')

        return redirect('contabilidade:certificado_list', empresa_pk=kwargs['empresa_pk'])


# =============================================================================
# Sessões
# =============================================================================

class SessaoListView(LoginRequiredMixin, ListView):
    '''Listagem de sessões do APP Core.'''
    template_name = 'contabilidade/sessao/list.html'
    context_object_name = 'sessoes'
    paginate_by = 20

    def get_queryset(self):
        from apps.core.db_models import SessionSnapshot

        contabilidade = self.request.user.contabilidade
        if not contabilidade:
            return SessionSnapshot.objects.none()

        # Busca telefones dos usuários das empresas desta contabilidade
        telefones = UsuarioEmpresa.objects.filter(
            empresa__contabilidade=contabilidade,
            is_active=True
        ).values_list('telefone', flat=True)

        qs = SessionSnapshot.objects.filter(telefone__in=telefones)

        # Filtro por telefone (remove caracteres não numéricos)
        telefone_busca = self.request.GET.get('telefone')
        if telefone_busca:
            # Limpar telefone: remover tudo exceto dígitos
            telefone_limpo = ''.join(filter(str.isdigit, telefone_busca))
            if telefone_limpo:
                qs = qs.filter(telefone__icontains=telefone_limpo)
        
        # Filtro por nome da empresa
        empresa_busca = self.request.GET.get('empresa')
        if empresa_busca:
            qs = qs.filter(empresa_nome__icontains=empresa_busca)

        # Filtro por estado
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        
        # Filtro: Conexões Ativas
        ativas = self.request.GET.get('ativas')
        if ativas == '1':
            from apps.core.states import SessionState
            qs = qs.filter(estado__in=SessionState.active_states())

        return qs.order_by('-session_created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.states import SessionState
        
        # Usar estados do enum centralizado
        context['estados'] = SessionState.choices()
        context['estado_selecionado'] = self.request.GET.get('estado', '')
        context['ativas_selecionado'] = self.request.GET.get('ativas', '')
        return context


class SessaoDetailView(LoginRequiredMixin, DetailView):
    '''Detalhes de uma sessão.'''
    template_name = 'contabilidade/sessao/detail.html'
    context_object_name = 'sessao'
    
    def get_queryset(self):
        from apps.core.db_models import SessionSnapshot
        
        contabilidade = self.request.user.contabilidade
        if not contabilidade:
            return SessionSnapshot.objects.none()
        
        # Busca telefones dos usuários das empresas desta contabilidade
        telefones = UsuarioEmpresa.objects.filter(
            empresa__contabilidade=contabilidade,
            is_active=True
        ).values_list('telefone', flat=True)
        
        return SessionSnapshot.objects.filter(telefone__in=telefones).prefetch_related('messages')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Buscar emissão NFSe relacionada (se existir)
        from apps.nfse.models import NFSeEmissao
        context['emissao_nfse'] = NFSeEmissao.objects.filter(
            session=self.object
        ).select_related('prestador', 'tomador', 'nota_processada').first()
        
        return context


# =============================================================================
# Notas Fiscais
# =============================================================================

class NotaFiscalListView(LoginRequiredMixin, ListView):
    '''Listagem de notas fiscais.'''
    template_name = 'contabilidade/nota_fiscal/list.html'
    context_object_name = 'notas'
    paginate_by = 20

    def get_queryset(self):
        from apps.core.db_models import SessionSnapshot

        contabilidade = self.request.user.contabilidade
        if not contabilidade:
            return SessionSnapshot.objects.none()

        # Busca CNPJs das empresas desta contabilidade
        cnpjs = Empresa.objects.filter(
            contabilidade=contabilidade,
            is_active=True
        ).values_list('cpf_cnpj', flat=True)

        # Normaliza CNPJs (remove pontuação)
        cnpjs_normalizados = [c.replace('.', '').replace('/', '').replace('-', '') for c in cnpjs]

        qs = SessionSnapshot.objects.filter(
            cnpj__in=cnpjs_normalizados,
            estado='processando'
        )

        # Filtro por empresa
        empresa_id = self.request.GET.get('empresa')
        if empresa_id:
            empresa = Empresa.objects.filter(pk=empresa_id, contabilidade=contabilidade).first()
            if empresa:
                cnpj_normalizado = empresa.cpf_cnpj.replace('.', '').replace('/', '').replace('-', '')
                qs = qs.filter(cnpj=cnpj_normalizado)

        return qs.order_by('-session_created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresas'] = Empresa.objects.filter(
            contabilidade=self.request.user.contabilidade,
            is_active=True
        )
        context['empresa_selecionada'] = self.request.GET.get('empresa', '')
        return context


class NotaFiscalCreateView(LoginRequiredMixin, TemplateView):
    '''Formulário para emissão manual de nota fiscal.'''
    template_name = 'contabilidade/nota_fiscal/form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contabilidade = self.request.user.contabilidade
        context['empresas'] = Empresa.objects.filter(
            contabilidade=contabilidade,
            is_active=True,
            nfse_ativo=True
        )
        return context

    def post(self, request, *args, **kwargs):
        # TODO: Implementar emissão manual de nota
        messages.warning(request, 'Emissão manual de nota fiscal ainda não implementada.')
        return redirect('contabilidade:nota_fiscal_list')


# =============================================================================
# Usuários do Sistema (Funcionários da Contabilidade)
# =============================================================================

class UsuarioListView(LoginRequiredMixin, ListView):
    '''Listagem de usuários do sistema.'''
    model = User
    template_name = 'contabilidade/usuario/list.html'
    context_object_name = 'usuarios'
    paginate_by = 20

    def get_queryset(self):
        contabilidade = self.request.user.contabilidade
        if not contabilidade:
            return User.objects.none()
        return User.objects.filter(contabilidade=contabilidade)


class UsuarioCreateView(LoginRequiredMixin, CreateView):
    '''Cadastro de usuário do sistema.'''
    model = User
    form_class = UserForm
    template_name = 'contabilidade/usuario/form.html'
    success_url = reverse_lazy('contabilidade:usuario_list')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.contabilidade = self.request.user.contabilidade

        # Define senha
        password = form.cleaned_data.get('password1')
        if password:
            user.set_password(password)

        user.save()
        messages.success(self.request, 'Usuário cadastrado com sucesso!')
        return redirect(self.success_url)


class UsuarioUpdateView(LoginRequiredMixin, UpdateView):
    '''Edição de usuário do sistema.'''
    model = User
    form_class = UserForm
    template_name = 'contabilidade/usuario/form.html'
    success_url = reverse_lazy('contabilidade:usuario_list')

    def get_queryset(self):
        contabilidade = self.request.user.contabilidade
        if not contabilidade:
            return User.objects.none()
        return User.objects.filter(contabilidade=contabilidade)

    def form_valid(self, form):
        user = form.save(commit=False)

        # Atualiza senha se fornecida
        password = form.cleaned_data.get('password1')
        if password:
            user.set_password(password)

        user.save()
        messages.success(self.request, 'Usuário atualizado com sucesso!')
        return redirect(self.success_url)


class UsuarioDeleteView(LoginRequiredMixin, DeleteView):
    '''Exclusão de usuário do sistema.'''
    model = User
    template_name = 'contabilidade/usuario/confirm_delete.html'
    success_url = reverse_lazy('contabilidade:usuario_list')

    def get_queryset(self):
        contabilidade = self.request.user.contabilidade
        if not contabilidade:
            return User.objects.none()
        # Não permite excluir o próprio usuário
        return User.objects.filter(contabilidade=contabilidade).exclude(pk=self.request.user.pk)


# =============================================================================
# API/AJAX Views
# =============================================================================

class ConsultarCNPJView(LoginRequiredMixin, View):
    '''Consulta CNPJ na Receita Federal via BrasilAPI.'''
    
    def get(self, request):
        cnpj = request.GET.get('cnpj', '').strip()
        
        if not cnpj:
            return JsonResponse({'error': 'CNPJ não informado'}, status=400)
        
        # Remove formatação
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        
        if len(cnpj_limpo) != 14:
            return JsonResponse({'error': 'CNPJ inválido'}, status=400)
        
        try:
            dados = ReceitaFederalService.consultar_cnpj(cnpj_limpo)

            # Formatar código CNAE: 9430800 → "9430-8/00"
            def formatar_cnae(codigo):
                s = str(codigo).strip()
                if len(s) == 7 and s.isdigit():
                    return f"{s[:4]}-{s[4]}/{s[5:]}"
                return s

            # Processar CNAEs
            cnae_principal = ''
            cnae_secundarios = ''
            if dados.get('cnae_fiscal'):
                cnae_principal = formatar_cnae(dados['cnae_fiscal'])
            if dados.get('cnaes_secundarios'):
                cnaes = [formatar_cnae(c.get('codigo', '')) for c in dados['cnaes_secundarios'] if c.get('codigo')]
                cnae_secundarios = ', '.join(cnaes)

            # Determinar regime tributário baseado em natureza jurídica e porte
            regime_tributario = 3  # Regime Normal por padrão
            simples_nacional = False

            # Códigos de natureza jurídica que indicam Simples Nacional (MEI, ME, EPP)
            natureza = str(dados.get('codigo_natureza_juridica', ''))
            porte = (dados.get('porte') or '').upper()

            opcao_simples = dados.get('opcao_pelo_simples')
            if porte in ['ME', 'MEI', 'EPP'] or opcao_simples is True or 'SIMPLES' in str(opcao_simples or '').upper():
                regime_tributario = 1  # Simples Nacional
                simples_nacional = True

            # Extrair tipo de logradouro
            tipo_logradouro = dados.get('descricao_tipo_de_logradouro', '')

            # Separar DDD e número do telefone
            telefone_raw = (dados.get('ddd_telefone_1') or '').strip()
            telefone_ddd = ''
            telefone_numero = ''
            if telefone_raw:
                telefone_digits = ''.join(filter(str.isdigit, telefone_raw))
                if len(telefone_digits) >= 10:
                    telefone_ddd = telefone_digits[:2]
                    telefone_numero = telefone_digits[2:]
                else:
                    telefone_numero = telefone_digits

            # Formatar resposta para o frontend
            response_data = {
                'success': True,
                'cnpj': cnpj_limpo,
                'razao_social': dados.get('razao_social', ''),
                'nome_fantasia': dados.get('nome_fantasia', ''),
                'cnae_principal': cnae_principal,
                'cnae_secundarios': cnae_secundarios,
                'simples_nacional': simples_nacional,
                'regime_tributario': regime_tributario,
                'cep': (dados.get('cep') or '').replace('-', ''),
                'tipo_logradouro': tipo_logradouro,
                'logradouro': dados.get('logradouro', ''),
                'numero': dados.get('numero', ''),
                'complemento': dados.get('complemento', ''),
                'bairro': dados.get('bairro', ''),
                'cidade': dados.get('municipio', ''),
                'estado': dados.get('uf', ''),
                'codigo_cidade': str(dados.get('codigo_municipio_ibge', ''))[:7],
                'email': dados.get('email', ''),
                'telefone_ddd': telefone_ddd,
                'telefone_numero': telefone_numero,
            }
            
            logger.info(f"CNPJ {cnpj_limpo} consultado com sucesso via AJAX")
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Erro ao consultar CNPJ {cnpj_limpo}: {str(e)}")
            return JsonResponse({
                'error': f'Erro ao consultar CNPJ: {str(e)}'
            }, status=400)

    def form_valid(self, form):
        messages.success(self.request, 'Usuário excluído com sucesso!')
        return super().form_valid(form)
