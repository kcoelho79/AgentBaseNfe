from django.urls import path
from . import views

app_name = 'whatsapp_api'

urlpatterns = [
    # Canais
    path('canais/', views.canal_list, name='canal_list'),
    path('canais/adicionar/', views.canal_create, name='canal_create'),
    path('canais/<int:pk>/', views.canal_detail, name='canal_detail'),
    path('canais/<int:pk>/qrcode/', views.canal_qrcode, name='canal_qrcode'),
    path('canais/<int:pk>/conectar/', views.canal_connect, name='canal_connect'),
    path('canais/<int:pk>/desconectar/', views.canal_disconnect, name='canal_disconnect'),
    path('canais/<int:pk>/reiniciar/', views.canal_restart, name='canal_restart'),
    path('canais/<int:pk>/excluir/', views.canal_delete, name='canal_delete'),
    
    # AJAX
    path('canais/<int:pk>/status/', views.canal_status, name='canal_status'),
    path('canais/<int:pk>/refresh-qrcode/', views.canal_refresh_qrcode, name='canal_refresh_qrcode'),
    
    # Webhook (público)
    path('webhook/<str:instance_name>/', views.webhook_receiver, name='webhook_receiver'),
]
