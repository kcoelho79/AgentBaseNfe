"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from apps.core import views as core_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Home pública
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Apps
    path('account/', include('apps.account.urls', namespace='account')),
    path('app/', include('apps.contabilidade.urls', namespace='contabilidade')),

    # API existente (core)
    path('chat/', core_views.chat_local, name='chat'),
    path('send/', core_views.send_message, name='send_message'),
    path('clear/<str:telefone>/', core_views.clear_state, name='clear_state'),
    path('health/', core_views.health, name='health'),
]

# Servir arquivos de media em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
