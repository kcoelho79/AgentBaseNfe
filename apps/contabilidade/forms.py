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

    def clean_cpf_cnpj(self):
        cpf_cnpj = self.cleaned_data.get('cpf_cnpj', '')
        return ''.join(filter(str.isdigit, cpf_cnpj))


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
    
    # Campos auxiliares para o formulário (não salvos diretamente no banco)
    telefone_codigo_pais = forms.CharField(
        label='Código País',
        max_length=3,
        initial='55',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': 3, 'placeholder': '55'})
    )
    telefone_numero = forms.CharField(
        label='Número',
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1199999-9999'})
    )
    
    class Meta:
        model = UsuarioEmpresa
        exclude = ['empresa', 'created_at', 'updated_at', 'telefone']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Se está editando, separa o telefone completo em código país + número
        if self.instance and self.instance.pk and self.instance.telefone:
            telefone_completo = self.instance.telefone
            # Assume que os primeiros 2 dígitos são o código do país (55)
            if len(telefone_completo) >= 12:  # 55 + 11 (DDD+número)
                self.initial['telefone_codigo_pais'] = telefone_completo[:2]
                self.initial['telefone_numero'] = telefone_completo[2:]
            else:
                # Se não tiver código de país, assume 55
                self.initial['telefone_codigo_pais'] = '55'
                self.initial['telefone_numero'] = telefone_completo
        
        # Define is_active como True por padrão para novos usuários
        if not self.instance.pk:
            self.initial['is_active'] = True

    def clean(self):
        cleaned_data = super().clean()
        
        # Concatena código país + número e salva no campo telefone
        codigo_pais = cleaned_data.get('telefone_codigo_pais', '55')
        telefone_numero = cleaned_data.get('telefone_numero', '')
        
        # Remove caracteres não numéricos
        codigo_pais = ''.join(filter(str.isdigit, codigo_pais)) or '55'
        telefone_numero = ''.join(filter(str.isdigit, telefone_numero))
        
        # Concatena e salva no campo telefone do modelo
        telefone_completo = codigo_pais + telefone_numero
        cleaned_data['telefone'] = telefone_completo
        
        # Validar se telefone já existe em outro usuário ativo
        if telefone_completo:
            qs = UsuarioEmpresa.objects.filter(
                telefone=telefone_completo,
                is_active=True
            )
            
            # Se está editando, exclui o próprio registro
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                usuario_existente = qs.first()
                raise forms.ValidationError(
                    f'⚠️ Este telefone já está cadastrado para "{usuario_existente.nome}" '
                    f'na empresa "{usuario_existente.empresa.razao_social}". '
                    f'Um telefone só pode estar ativo em uma empresa por vez.'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Garante que o telefone foi concatenado corretamente
        codigo_pais = self.cleaned_data.get('telefone_codigo_pais', '55')
        telefone_numero = self.cleaned_data.get('telefone_numero', '')
        
        codigo_pais = ''.join(filter(str.isdigit, codigo_pais)) or '55'
        telefone_numero = ''.join(filter(str.isdigit, telefone_numero))
        
        instance.telefone = codigo_pais + telefone_numero
        
        if commit:
            instance.save()
        return instance


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
