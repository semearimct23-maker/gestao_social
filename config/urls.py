from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Aponta para o app academia
    path('', include('academia.urls')), 
    
    # Aponta para o sistema de login do Django
    path('contas/', include('django.contrib.auth.urls')),
]

# Configuração para servir arquivos de mídia (Uploads)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)