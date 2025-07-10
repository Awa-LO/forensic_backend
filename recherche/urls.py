from django.urls import path
from . import views

app_name = 'recherche'

urlpatterns = [
    path('', views.search_home, name='home'),
    path('session/<str:session_id>/', views.search_view, name='search_session'),
    path('history/<str:session_id>/', views.search_history, name='history'),
    path('result/<str:session_id>/<int:search_id>/', views.get_search_result, name='get_result'),
]