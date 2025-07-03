# analysis/urls.py
from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    # Dashboard principal
    path('dashboard/', views.AnalysisDashboardView.as_view(), name='analysis_dashboard'),
    
    # Gestion des sessions
    path('sessions/<uuid:session_id>/', views.session_detail_view, name='session_detail'),
    path('sessions/<uuid:session_id>/analyze/', views.analyze_session, name='analyze'),
    path('sessions/<uuid:session_id>/results/', views.session_analysis_view, name='session_analysis'),
    
    # Génération de rapports
    path('sessions/<uuid:session_id>/generate-report/', views.generate_report, name='generate_report'),
    path('reports/', views.ReportListView.as_view(), name='report_list'),
    path('reports/<int:pk>/', views.ReportDetailView.as_view(), name='report_detail'),
    
    # API REST (optionnel)
    path('api/sessions/<uuid:session_id>/analyze/', views.AnalyzeDataView.as_view(), name='api_analyze'),
    # Dans analysis/urls.py
path('debug/sessions/<uuid:session_id>/', views.debug_analysis_session, name='debug_analysis_session'),
    # Debug/Test
    path('sessions/<uuid:session_id>/test-pipeline/', views.test_analysis_pipeline, name='test_pipeline'),
]