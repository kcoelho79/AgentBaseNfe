from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import (
    TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView, View
)
from datetime import timedelta

from .mixins import TenantMixin, EmpresaContextMixin
from .models import Empresa, UsuarioEmpresa, Certificado
from .forms import EmpresaForm, UsuarioEmpresaForm, CertificadoForm
from apps.account.forms import UserForm

User = get_user_model()


# =============================================================================
# Dashboard
# =============================================================================

class DashboardView(LoginRequiredMixin, TemplateView):
    '''Dashboard principal com métricas.'''
    template_name = 'contabilidade/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contabilidade = self.request.user.contabilidade

        if contabilidade:
            hoje = timezone.now().date()

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

            # TODO: Integrar com SessionSnapshot para métricas de notas
            context['notas_mes'] = 0
            context['notas_hoje'] = 0
            context['notas_sucesso'] = 0
            context['notas_erro'] = 0

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
        qs = super().get_queryset()
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(razao_social__icontains=search) | qs.filter(cpf_cnpj__icontains=search)
        return qs


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

        telefone_busca = self.request.GET.get('telefone')
        if telefone_busca:
            qs = qs.filter(telefone__icontains=telefone_busca)  

        # Filtro por estado
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)

        return qs.order_by('-session_created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.core.states import SessionState
        
        # Usar estados do enum centralizado
        context['estados'] = SessionState.choices()
        context['estado_selecionado'] = self.request.GET.get('estado', '')
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

    def form_valid(self, form):
        messages.success(self.request, 'Usuário excluído com sucesso!')
        return super().form_valid(form)
