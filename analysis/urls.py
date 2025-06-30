from django.urls import path
from .views import (
    AnalyzeDataView,
    DownloadReportView,
    ReportListView,
    AnalysisDashboardView, 
    ReportDetailView
)
from .views import session_analysis_view
from . import views 
from .views import generate_report
app_name = 'analysis'

urlpatterns = [
        # Tableau de bord principal
    path('dashboard/', AnalysisDashboardView.as_view(), name='analysis_dashboard'),
    path('reports/', ReportListView.as_view(), name='report_list'),
    path('sessions/<uuid:session_id>/report/', generate_report, name='generate_report'),
    path('reports/<int:pk>/', ReportDetailView.as_view(), name='report_detail'),
    path('sessions/<str:session_id>/', session_analysis_view, name='session_analysis'),
    path('sessions/<uuid:session_id>/analyze/', views.analyze_session, name='analyze'),
    path('sessions/<str:session_id>/analyze/', AnalyzeDataView.as_view(), name='analyze'),
    path('sessions/<str:session_id>/download-report/', DownloadReportView.as_view(), name='download_report'),
]

