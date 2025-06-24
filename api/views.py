from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import ForensicSession, CollectedData
from .serializers import DataUploadSerializer
import uuid
import logging
import zipfile
import os
import json
import tempfile

logger = logging.getLogger(__name__)

@api_view(['GET'])
def api_root(request, format=None):
    """Point d'entrée de l'API"""
    return Response({
        'message': 'Forensic Investigation API',
        'user': request.user.username if request.user.is_authenticated else 'Anonymous',
        'endpoints': {
            'auth': '/api-token-auth/',
            'start-session': '/api/v1/start-session/',
            'upload-session': '/api/v1/upload-session/',
            'complete-session': '/api/v1/complete-session/',
        }
    })

@api_view(['GET', 'POST'])
def test_auth(request):
    """Endpoint de test pour l'authentification"""
    if request.user.is_authenticated:
        return Response({
            'authenticated': True,
            'user': request.user.username,
            'message': 'Authentication successful'
        })
    else:
        return Response({
            'authenticated': False,
            'message': 'Not authenticated',
            'required': 'Token authentication in header: Authorization: Token <your-token>'
        }, status=status.HTTP_401_UNAUTHORIZED)

class StartSessionView(APIView):
    """Démarre une nouvelle session forensique"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            session_id = str(uuid.uuid4())
            device_info = request.data.get('device_info', {})
            
            session = ForensicSession.objects.create(
                user=request.user,
                session_id=session_id,
                device_info=device_info
            )
            
            logger.info(f"Session créée: {session_id} pour utilisateur {request.user.username}")
            
            return Response({
                'success': True,
                'session_id': session_id,
                'start_time': session.start_time,
                'message': 'Session started successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Erreur création session: {str(e)}")
            return Response({
                'success': False,
                'message': f'Erreur lors de la création de session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UploadSessionView(APIView):
    """
    Endpoint pour l'upload de session ZIP depuis AuthService.
    Correspond à UPLOAD_ENDPOINT = "/api/upload-session/"
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Endpoint de test pour vérifier que l'API fonctionne"""
        return Response({
            'message': 'Upload Session Endpoint',
            'method': 'POST required',
            'content_type': 'multipart/form-data',
            'authentication': 'Token required',
            'user': request.user.username if request.user.is_authenticated else 'Anonymous'
        })

    def post(self, request):
        try:
            # Récupération du fichier ZIP
            data_file = request.FILES.get('data_file')
            if not data_file:
                return Response({
                    'success': False,
                    'message': 'Aucun fichier fourni'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Vérification que c'est un ZIP
            if not data_file.name.endswith('.zip'):
                return Response({
                    'success': False,
                    'message': 'Le fichier doit être un ZIP'
                }, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"Réception ZIP: {data_file.name} ({data_file.size} bytes)")

            # Traitement du ZIP
            session_id = self.process_zip_upload(request.user, data_file)
            
            return Response({
                'success': True,
                'id': session_id,
                'message': 'Session uploadée avec succès',
                'session_id': session_id
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Erreur upload session: {str(e)}")
            return Response({
                'success': False,
                'message': f'Erreur lors de l\'upload: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def process_zip_upload(self, user, zip_file):
    session_id = str(uuid.uuid4())
    
    # Dictionnaire par défaut pour device_info
    device_info = {
        'uploaded_via': 'zip', 
        'filename': zip_file.name,
        'model': 'Inconnu',
        'manufacturer': 'Inconnu',
        'android_version': 'Inconnu'
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, zip_file.name)
        with open(zip_path, 'wb') as f:
            for chunk in zip_file.chunks():
                f.write(chunk)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                
                # Chercher le fichier de rapport
                report_file = None
                for root, dirs, files in os.walk(temp_dir):
                    if 'collection_report.json' in files:
                        report_file = os.path.join(root, 'collection_report.json')
                        break
                
                # Extraire les infos de l'appareil si le rapport existe
                if report_file and os.path.exists(report_file):
                    with open(report_file, 'r') as f:
                        report_data = json.load(f)
                        if report_data and isinstance(report_data, list) and len(report_data) > 0:
                            device_data = report_data[0].get('device_info', {})
                            device_info.update({
                                'model': device_data.get('model', 'Inconnu'),
                                'manufacturer': device_data.get('manufacturer', 'Inconnu'),
                                'android_version': device_data.get('android_version', 'Inconnu'),
                                'api_level': device_data.get('api_level', 0)
                            })

        except Exception as e:
            logger.error(f"Erreur traitement ZIP: {str(e)}")

    # Création de la session avec les infos de l'appareil
    session = ForensicSession.objects.create(
        user=user,
        session_id=session_id,
        device_info=device_info,
        device_name=device_info['model'],
        android_version=device_info['android_version']
    )



def process_extracted_file(self, session, file_path, filename):
    """Traite un fichier extrait du ZIP"""
    try:
        data_type = self.determine_data_type(filename)
        
        # Cas spécial pour le rapport d'appareil
        if data_type == 'device_report':
            with open(file_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
                if isinstance(report_data, list) and report_data:
                    device_info = report_data[0].get('device_info', {})
                    
                    # Met à jour les infos de l'appareil dans la session
                    session.device_info = {
                        'model': device_info.get('model', 'Inconnu'),
                        'manufacturer': device_info.get('manufacturer', 'Inconnu'),
                        'android_version': device_info.get('android_version', 'Inconnu'),
                        'api_level': device_info.get('api_level', 0)
                    }
                    session.save()
            return  # On sort car c'est un fichier spécial
    
        
        # Traitement normal pour les autres fichiers
        with open(file_path, 'r', encoding='utf-8') as f:
            if filename.endswith('.json'):
                data = json.load(f)
                item_count = len(data) if isinstance(data, list) else 1
            else:  # CSV
                lines = f.readlines()
                item_count = max(0, len(lines) - 1)

        # Sauvegarde du fichier
        with open(file_path, 'rb') as f:
            django_file = ContentFile(f.read(), name=filename)
            
            CollectedData.objects.create(
                session=session,
                data_type=data_type,
                file=django_file,
                file_size=os.path.getsize(file_path),
                item_count=item_count,
                metadata={
                    'original_filename': filename,
                    'extracted_from_zip': True
                }
            )
            
            session.total_items += item_count
            session.save()
            
    except Exception as e:
        logger.error(f"Erreur traitement fichier {filename}: {str(e)}")

def determine_data_type(self, filename):
    """Détermine le type de données basé sur le nom du fichier"""
    filename_lower = filename.lower()
    
    # Vérifie si le fichier commence par "collection_report" (peu importe la casse et la suite)
    if filename_lower.startswith('collection_report'):
        return 'device_report'  # Type spécial pour le rapport d'appareil
    elif 'sms' in filename_lower or 'message' in filename_lower:
        return 'sms'
    elif 'call' in filename_lower or 'appel' in filename_lower:
        return 'calls'
    elif 'contact' in filename_lower:
        return 'contacts'
    elif 'image' in filename_lower or 'photo' in filename_lower:
        return 'images'
    elif 'video' in filename_lower:
        return 'videos'
    elif 'audio' in filename_lower:
        return 'audio'
    else:
        return 'other'  # Type par défaut

class UploadDataView(APIView):
    """Upload de données individuelles (conservé pour compatibilité)"""
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DataUploadSerializer(data=request.data)
        if serializer.is_valid():
            session_id = serializer.validated_data['session_id']
            data_type = serializer.validated_data['data_type']
            data_file = serializer.validated_data['data_file']
            
            session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
            
            collected_data = CollectedData.objects.create(
                session=session,
                data_type=data_type,
                file=data_file,
                file_size=data_file.size,
                item_count=serializer.validated_data.get('item_count', 0),
                metadata={
                    'device_model': request.data.get('device_model'),
                    'android_version': request.data.get('android_version')
                }
            )
            
            session.total_items += collected_data.item_count
            session.save()
            
            return Response({
                'success': True,
                'message': f'{data_type} data uploaded successfully',
                'data_id': collected_data.id
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_session(request):
    """Marque une session comme terminée"""
    try:
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({
                'success': False,
                'message': 'session_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)

        session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
        
        session.status = 'completed'
        session.end_time = timezone.now()
        session.save()
        
        logger.info(f"Session {session_id} marquée comme terminée")
        
        return Response({
            'success': True,
            'message': 'Session marked as completed',
            'end_time': session.end_time,
            'total_items': session.total_items
        })
        
    except Exception as e:
        logger.error(f"Erreur completion session: {str(e)}")
        return Response({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)