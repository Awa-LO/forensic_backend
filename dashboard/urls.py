from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('sessions/', views.session_list, name='sessions'),
    path('sessions/<str:session_id>/', views.session_detail, name='session_detail'),
]