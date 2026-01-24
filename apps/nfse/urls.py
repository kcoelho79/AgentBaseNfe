# apps/nfse/urls.py
from django.urls import path
from . import views

app_name = 'nfse'

urlpatterns = [
    path('webhook/', views.webhook_nfse, name='webhook'),
    path('emissoes/', views.NotaFiscalEmissaoListView.as_view(), name='emissao_list'),
    path('processadas/', views.NotaFiscalProcessadaListView.as_view(), name='processada_list'),
    path('tomadores/', views.ClienteTomadorListView.as_view(), name='tomador_list'),
]