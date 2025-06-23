from django.urls import path
from .views import (
    StartSessionView,
    UploadDataView,
    complete_session
)
from . import views
app_name = 'api'

urlpatterns = [
     path('', views.api_root, name='api_root'),
    path('start-session/', StartSessionView.as_view(), name='start_session'),
    path('upload-data/', UploadDataView.as_view(), name='upload_data'),
    path('complete-session/', complete_session, name='complete_session'),
]