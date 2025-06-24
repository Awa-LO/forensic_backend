from django.urls import path
from .views import (
    StartSessionView,
    UploadSessionView,
    UploadDataView,
    complete_session,
    api_root,
    test_auth
)

app_name = 'api'

urlpatterns = [
    # Point d'entrée API
    path('', api_root, name='api_root'),
    
    # Test d'authentification
    path('test-auth/', test_auth, name='test_auth'),
    
    # Endpoints correspondant à AuthService.kt
    path('start-session/', StartSessionView.as_view(), name='start_session'),
    path('upload-session/', UploadSessionView.as_view(), name='upload_session'),  # Nouveau endpoint principal
    path('complete-session/', complete_session, name='complete_session'),
    
    # Endpoint legacy pour compatibilité
    path('upload-data/', UploadDataView.as_view(), name='upload_data'),
]