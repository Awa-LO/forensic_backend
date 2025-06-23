from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.parsers import MultiPartParser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import ForensicSession, CollectedData
from .serializers import DataUploadSerializer
from rest_framework.permissions import IsAuthenticated 
import uuid
import logging

logger = logging.getLogger(__name__)

class StartSessionView(APIView):
    def post(self, request):
        session_id = str(uuid.uuid4())
        device_info = request.data.get('device_info', {})
        
        session = ForensicSession.objects.create(
            user=request.user,
            session_id=session_id,
            device_info=device_info
        )
        
        return Response({
            'session_id': session_id,
            'start_time': session.start_time,
            'status': 'Session started successfully'
        }, status=status.HTTP_201_CREATED)

class UploadDataView(APIView):
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
                'status': 'success',
                'message': f'{data_type} data uploaded successfully',
                'data_id': collected_data.id
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def complete_session(request):
    session_id = request.data.get('session_id')
    session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
    
    session.status = 'completed'
    session.end_time = timezone.now()
    session.save()
    
    return Response({
        'status': 'success',
        'message': 'Session marked as completed',
        'end_time': session.end_time,
        'total_items': session.total_items
    })


from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.response import Response

@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'start-session': reverse('api:start_session', request=request),
        'upload-data': reverse('api:upload_data', request=request),
        'complete-session': reverse('api:complete_session', request=request),
    })