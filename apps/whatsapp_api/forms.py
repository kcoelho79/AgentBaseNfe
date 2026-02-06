from django import forms
from .models import CanalWhatsApp


class CanalWhatsAppForm(forms.ModelForm):
    """Formulário para criar/editar canal WhatsApp."""
    
    class Meta:
        model = CanalWhatsApp
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: WhatsApp Principal'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.contabilidade = kwargs.pop('contabilidade', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.contabilidade:
            instance.contabilidade = self.contabilidade
        if commit:
            instance.save()
        return instance
