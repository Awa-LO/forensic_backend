from django.db.models import Q
from api.models import CollectedData

def prepare_analysis_context(session_id):
    """Version corrigée avec gestion des None"""
    data_items = CollectedData.objects.filter(session__session_id=session_id)
    
    context = {
        'fraud_results': [],
        'sentiment_results': {},
        'technical_results': []
    }

    if data_items.exists():
        # Résultats de fraude
        context['fraud_results'] = data_items.filter(
            results__analysis_type='fraud'
        ).select_related('results') or []
        
        # Analyse de sentiment (premier résultat trouvé)
        sentiment_data = data_items.filter(
            results__analysis_type='sentiment'
        ).first()
        context['sentiment_results'] = (
            sentiment_data.results.result_json 
            if sentiment_data and hasattr(sentiment_data, 'results') 
            else {}
        )
        
        # Résultats techniques
        context['technical_results'] = data_items.filter(
            Q(results__analysis_type='anomaly') | 
            Q(results__analysis_type='llm')
        ) or []

    return context