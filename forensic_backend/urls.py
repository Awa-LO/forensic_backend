# forensic_backend/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    # Administration
    path('admin/', admin.site.urls),

    # Apps avec namespaces
    path('analysis/', include('analysis.urls', namespace='analysis')),
    path('recherche/', include('recherche.urls', namespace='recherche')),
    path('dashboard/', include('dashboard.urls')),

    # Authentification web (⚠️ ajouter namespace ici !)
    path('auth/', include(('authentication.urls', 'authentication'), namespace='authentication')),

    # Redirection de la racine vers le choix de rôle
    path('', lambda request: redirect('authentication:choose_role')),

    # API REST
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('api/v1/', include('api.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Debug Toolbar si besoin
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
