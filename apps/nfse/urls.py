from django.urls import path
from . import views

app_name = 'nfse'

urlpatterns = [
    path('webhook/', views.webhook_nfse, name='webhook'),
]
