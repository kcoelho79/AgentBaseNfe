from django import forms
from .models import Empresa, UsuarioEmpresa, Certificado


class EmpresaForm(forms.ModelForm):
    '''Formulário para cadastro e edição de empresa.'''
    class Meta:
        model = Empresa
        exclude = ['contabilidade', 'tecnospeed_id', 'created_at', 'updated_at']
        widgets = {
            'cpf_cnpj': forms.TextInput(attrs={'class': 'form-control'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'inscricao_municipal': forms.TextInput(attrs={'class': 'form-control'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control'}),
            'simples_nacional': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'regime_tributario': forms.Select(attrs={'class': 'form-select'}),
            'incentivo_fiscal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'incentivador_cultural': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'regime_tributario_especial': forms.Select(attrs={'class': 'form-select'}),
            'cep': forms.TextInput(attrs={'class': 'form-control'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao_cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
            'codigo_pais': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao_pais': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone_ddd': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
            'telefone_numero': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'nfse_ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'nfse_producao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campos com valores padrão não são obrigatórios
        self.fields['codigo_pais'].required = False
        self.fields['descricao_pais'].required = False
        self.fields['regime_tributario'].required = False
        self.fields['regime_tributario_especial'].required = False

    def clean_codigo_pais(self):
        return self.cleaned_data.get('codigo_pais') or '1058'

    def clean_descricao_pais(self):
        return self.cleaned_data.get('descricao_pais') or 'Brasil'

    def clean_regime_tributario(self):
        return self.cleaned_data.get('regime_tributario') or 3

    def clean_regime_tributario_especial(self):
        return self.cleaned_data.get('regime_tributario_especial') or 0


class UsuarioEmpresaForm(forms.ModelForm):
    '''Formulário para cadastro e edição de usuário da empresa.'''
    class Meta:
        model = UsuarioEmpresa
        exclude = ['empresa', 'created_at', 'updated_at']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'cep': forms.TextInput(attrs={'class': 'form-control'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CertificadoForm(forms.ModelForm):
    '''Formulário para upload de certificado digital.'''
    class Meta:
        model = Certificado
        fields = ['arquivo', 'senha', 'nome_titular', 'cnpj_titular', 'validade', 'is_active']
        widgets = {
            'arquivo': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pfx,.p12'}),
            'senha': forms.PasswordInput(attrs={'class': 'form-control'}),
            'nome_titular': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj_titular': forms.TextInput(attrs={'class': 'form-control'}),
            'validade': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Arquivo só é obrigatório na criação
        if self.instance.pk:
            self.fields['arquivo'].required = False
            self.fields['senha'].required = False
