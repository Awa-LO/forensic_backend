# authentication/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
app_name = 'authentication'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),
    path('choose-role/', views.choose_role_view, name='choose_role'),
    path('guest-code/', views.guest_code_view, name='guest_code'),
     path('logout/', auth_views.LogoutView.as_view(next_page='authentication:choose_role'), name='logout'),
]