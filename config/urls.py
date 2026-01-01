from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from website.views import index, doacao # <--- IMPORTAR AS VIEWS NOVAS

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ROTA PRINCIPAL (SITE PÚBLICO)
    path('', index, name='index_site'), 
    
    path('doacao/', doacao, name='doacao'),

    # ROTAS DO SISTEMA (ACADEMIA)
    path('sistema/', include('academia.urls')), # <--- MUDAMOS PARA /SISTEMA/
    
    path('accounts/', include('django.contrib.auth.urls')),
] 
# + configurações de media...