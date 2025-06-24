from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from api.models import ForensicSession, CollectedData

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

from django.shortcuts import render, get_object_or_404
import json
import os
from django.conf import settings

@login_required
def session_detail(request, session_id):
    session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
    
    data_types = CollectedData.DATA_TYPES
    data_items = {}
    
    for dtype, _ in data_types:
        data = CollectedData.objects.filter(session=session, data_type=dtype).first()
        if data:
            data_items[dtype] = data

    context = {
        'session': session,
        'data_items': data_items,
        'MEDIA_ROOT': settings.MEDIA_ROOT,  # Passer MEDIA_ROOT au template
    }
    return render(request, 'dashboard/session_detail.html', context)