"""
URL configuration for forensic_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# forensic_backend/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    # Administration
    path('admin/', admin.site.urls),
    
    # Authentification Web
    path('auth/', include('authentication.urls')),
    path('', auth_views.LoginView.as_view(template_name='auth/login.html'), name='home'),
    
    # API REST pour Android
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),  # Endpoint standard DRF
    path('api/v1/', include('api.urls')),
    
    # Dashboard Web
    path('dashboard/', include('dashboard.urls'))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Configuration pour le debug
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns