from django import forms
from django.contrib.auth import authenticate, get_user_model

User = get_user_model()


class LoginForm(forms.Form):
    '''Formulário de login com email.'''
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'seu@email.com',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '********',
        })
    )

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user = authenticate(email=email, password=password)
            if self.user is None:
                raise forms.ValidationError('E-mail ou senha inválidos.')
            if not self.user.is_active:
                raise forms.ValidationError('Esta conta está desativada.')

        return self.cleaned_data


class RegisterForm(forms.ModelForm):
    '''Formulário de registro de nova contabilidade.'''
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password_confirm = forms.CharField(
        label='Confirmar Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    contabilidade_cnpj = forms.CharField(
        label='CNPJ da Contabilidade',
        max_length=18,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    contabilidade_razao_social = forms.CharField(
        label='Razão Social',
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone']
        labels = {
            'email': 'E-mail',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'phone': 'Telefone',
        }
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('As senhas não conferem.')

        return self.cleaned_data


class ProfileForm(forms.ModelForm):
    '''Formulário de edição de perfil.'''
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone']
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'phone': 'Telefone',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserForm(forms.ModelForm):
    '''Formulário para criar/editar usuários do sistema.'''
    password1 = forms.CharField(
        label='Senha',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Deixe em branco para manter a senha atual (somente edição).'
    )
    password2 = forms.CharField(
        label='Confirmar Senha',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'role', 'is_active']
        labels = {
            'email': 'E-mail',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'phone': 'Telefone',
            'role': 'Função',
            'is_active': 'Ativo',
        }
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        # Se está criando um novo usuário, senha é obrigatória
        if not self.instance.pk and not password1:
            self.add_error('password1', 'Senha é obrigatória para novos usuários.')

        # Se senha foi informada, deve confirmar
        if password1 and password1 != password2:
            self.add_error('password2', 'As senhas não conferem.')

        return cleaned_data
