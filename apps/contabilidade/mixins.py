from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from .models import Empresa


class TenantMixin(LoginRequiredMixin):
    '''
    Mixin que filtra querysets pela contabilidade do usuário logado.
    '''

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.request.user, 'contabilidade') and self.request.user.contabilidade:
            return qs.filter(contabilidade=self.request.user.contabilidade)
        return qs.none()

    def form_valid(self, form):
        if hasattr(form, 'instance') and hasattr(form.instance, 'contabilidade'):
            form.instance.contabilidade = self.request.user.contabilidade
        return super().form_valid(form)


class EmpresaContextMixin(LoginRequiredMixin):
    '''
    Mixin para views que operam dentro do contexto de uma empresa.
    Adiciona a empresa ao contexto e valida acesso.
    '''

    def get_empresa(self):
        empresa_pk = self.kwargs.get('empresa_pk')
        return get_object_or_404(
            Empresa,
            pk=empresa_pk,
            contabilidade=self.request.user.contabilidade
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = self.get_empresa()
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(empresa=self.get_empresa())

    def form_valid(self, form):
        if hasattr(form, 'instance'):
            form.instance.empresa = self.get_empresa()
        return super().form_valid(form)
