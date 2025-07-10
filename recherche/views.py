from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from api.models import ForensicSession, CollectedData
from analysis.models import AnalysisResult
from .models import SearchResult
import json
import logging

logger = logging.getLogger(__name__)

def _search_in_item(item, data, search_term, results):
    """Méthode utilitaire pour rechercher dans un élément de données"""
    if isinstance(item, dict):
        for key, value in item.items():
            if isinstance(value, str) and search_term in value.lower():
                count = value.lower().count(search_term)
                results['total_occurrences'] += count
                results['matches'].append({
                    'data_type': data.data_type,
                    'data_id': data.id,
                    'field': key,
                    'content': value[:200] + '...' if len(value) > 200 else value,
                    'occurrences': count
                })
    elif isinstance(item, str):
        if search_term in item.lower():
            count = item.lower().count(search_term)
            results['total_occurrences'] += count
            results['matches'].append({
                'data_type': data.data_type,
                'data_id': data.id,
                'content': item[:200] + '...' if len(item) > 200 else item,
                'occurrences': count
            })

@login_required
def search_home(request):
    """Vue pour sélectionner une session avant de faire la recherche"""
    sessions = ForensicSession.objects.filter(user=request.user).order_by('-start_time')  # Changé ici
    
    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        if session_id:
            return redirect('recherche:search_session', session_id=session_id)
    
    return render(request, 'recherche/select_session.html', {'sessions': sessions})

@login_required
def search_view(request, session_id):
    """Vue pour effectuer la recherche dans une session spécifique"""
    session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
    
    if request.method == 'POST':
        search_term = request.POST.get('search_term', '').strip().lower()
        
        if not search_term:
            return JsonResponse({'error': 'Terme de recherche vide'}, status=400)
        
        # Vérifier si une recherche similaire existe déjà
        existing_search = SearchResult.objects.filter(
            session=session, 
            search_term__iexact=search_term
        ).first()
        
        if existing_search:
            return JsonResponse(existing_search.results_json)
        
        results = {
            'search_term': search_term,
            'total_occurrences': 0,
            'matches': []
        }
        
        try:
            # Rechercher dans toutes les données collectées
            collected_data = session.collected_items.all()
            
            if not collected_data.exists():
                return JsonResponse({
                    'search_term': search_term,
                    'total_occurrences': 0,
                    'matches': [],
                    'info': 'Aucune donnée collectée trouvée dans cette session'
                })
            
            for data in collected_data:
                try:
                    content = data.get_file_content()
                    if not content:
                        continue
                        
                    if isinstance(content, list):
                        for item in content:
                            _search_in_item(item, data, search_term, results)
                    elif isinstance(content, dict):
                        _search_in_item(content, data, search_term, results)
                    elif isinstance(content, str):
                        if search_term in content.lower():
                            count = content.lower().count(search_term)
                            results['total_occurrences'] += count
                            results['matches'].append({
                                'data_type': data.data_type,
                                'data_id': data.id,
                                'content': content[:200] + '...' if len(content) > 200 else content,
                                'occurrences': count
                            })
                except Exception as e:
                    logger.warning(f"Erreur lors de la lecture du contenu de {data.id}: {str(e)}")
                    continue
            
            # Enregistrer les résultats pour une future recherche
            SearchResult.objects.create(
                session=session,
                search_term=search_term,
                results_json=results
            )
            
            return JsonResponse(results)
        
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {str(e)}")
            return JsonResponse({'error': f'Erreur lors de la recherche: {str(e)}'}, status=500)
    
    # GET request - afficher le formulaire de recherche
    return render(request, 'recherche/search.html', {
        'session': session,
        'data_count': session.collected_items.count()
    })

@login_required
def search_history(request, session_id):
    """Vue pour afficher l'historique des recherches"""
    session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
    searches = SearchResult.objects.filter(session=session).order_by('-created_at')
    return render(request, 'recherche/history.html', {
        'searches': searches, 
        'session': session
    })

@login_required
def get_search_result(request, session_id, search_id):
    """Vue pour récupérer les résultats d'une recherche précédente"""
    session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
    search = get_object_or_404(SearchResult, id=search_id, session=session)
    return JsonResponse(search.results_json)