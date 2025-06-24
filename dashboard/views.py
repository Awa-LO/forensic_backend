from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from api.models import ForensicSession, CollectedData
import logging
logger = logging.getLogger(__name__)

@login_required
def home(request):
    # Dernière session
    last_session = ForensicSession.objects.filter(user=request.user).first()
    
    # Statistiques globales
    stats = {
        'sms_count': CollectedData.objects.filter(
            session__user=request.user, 
            data_type='sms'
        ).aggregate(total=Sum('item_count'))['total'] or 0,
        'calls_count': CollectedData.objects.filter(
            session__user=request.user, 
            data_type='calls'
        ).aggregate(total=Sum('item_count'))['total'] or 0,
        'contacts_count': CollectedData.objects.filter(
            session__user=request.user, 
            data_type='contacts'
        ).aggregate(total=Sum('item_count'))['total'] or 0,
        'images_count': CollectedData.objects.filter(
            session__user=request.user, 
            data_type='images'
        ).aggregate(total=Sum('item_count'))['total'] or 0,
        'videos_count': CollectedData.objects.filter(
            session__user=request.user, 
            data_type='videos'
        ).aggregate(total=Sum('item_count'))['total'] or 0,
        'audio_count': CollectedData.objects.filter(
            session__user=request.user, 
            data_type='audio'
        ).aggregate(total=Sum('item_count'))['total'] or 0,
    }
    stats['total_items'] = sum(stats.values())

    context = {
        'last_session': last_session,
        **stats
    }
    return render(request, 'dashboard/home.html', context)

@login_required
def session_list(request):
    sessions = ForensicSession.objects.filter(user=request.user).order_by('-start_time')
    return render(request, 'dashboard/sessions.html', {'sessions': sessions})

import json
import os
from django.conf import settings

@login_required
def session_detail(request, session_id):
    session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
    
    # Récupère le fichier de rapport
    report_file = session.collected_items.filter(
        file__icontains='collection_report'
    ).first()
    
    # Initialise device_info
    device_info = session.device_info if session.device_info else {}
    
    # Si pas d'info mais fichier rapport existe
    if not device_info and report_file:
        try:
            with open(report_file.file.path, 'r') as f:
                report_data = json.load(f)
                if isinstance(report_data, list) and report_data:
                    device_info = report_data[0].get('device_info', {})
                    # Met à jour la session pour les prochains accès
                    session.device_info = device_info
                    session.save()
        except Exception as e:
            logger.error(f"Error loading report: {str(e)}")

    context = {
        'session': session,
        'data_items': {dtype: session.collected_items.filter(data_type=dtype).first() 
                      for dtype, _ in CollectedData.DATA_TYPES},
        'device_info': device_info,
        'report_file_url': report_file.file.url if report_file else None,
        'MEDIA_ROOT': settings.MEDIA_ROOT,
    }
    return render(request, 'dashboard/session_detail.html', context)