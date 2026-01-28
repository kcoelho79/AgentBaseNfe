from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView, UpdateView
from django.contrib import messages
from django.db import IntegrityError

from .forms import LoginForm, RegisterForm, ProfileForm

User = get_user_model()


class LoginView(FormView):
    '''View de login.'''
    template_name = 'account/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('contabilidade:dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, form.user)
        messages.success(self.request, f'Bem-vindo, {form.user.first_name or form.user.email}!')
        return super().form_valid(form)


class LogoutView(TemplateView):
    '''View de logout.'''

    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, 'Você saiu do sistema.')
        return redirect('home')


class RegisterView(FormView):
    '''View de registro de nova contabilidade.'''
    template_name = 'account/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('account:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('contabilidade:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        from apps.contabilidade.models import Contabilidade

        try:
            # Criar contabilidade
            contabilidade = Contabilidade.objects.create(
                cnpj=form.cleaned_data['contabilidade_cnpj'],
                razao_social=form.cleaned_data['contabilidade_razao_social'],
                email=form.cleaned_data['email'],
            )

            # Criar usuário admin
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.contabilidade = contabilidade
            user.role = 'admin'
            user.save()

            messages.success(
                self.request,
                'Conta criada com sucesso! Faça login para continuar.'
            )
            return super().form_valid(form)
            
        except IntegrityError as e:
            # Verificar se é erro de CNPJ duplicado
            if 'contabilidade_contabilidade.cnpj' in str(e):
                form.add_error(
                    'contabilidade_cnpj',
                    'Este CNPJ já está cadastrado no sistema. Entre em contato com o suporte se precisar de ajuda.'
                )
            else:
                form.add_error(None, 'Erro ao criar conta. Tente novamente.')
            
            return self.form_invalid(form)


class ProfileView(LoginRequiredMixin, UpdateView):
    '''View de edição de perfil.'''
    template_name = 'account/profile.html'
    form_class = ProfileForm
    success_url = reverse_lazy('account:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Perfil atualizado com sucesso!')
        return super().form_valid(form)
