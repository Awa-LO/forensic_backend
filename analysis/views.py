from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse
from .models import AnalysisResult, ForensicReport
from .services import ForensicAI, PDFGenerator
from api.models import CollectedData, ForensicSession
import os

class AnalyzeDataView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = ForensicSession.objects.get(session_id=session_id, user=request.user)
        data_items = CollectedData.objects.filter(session=session)
        
        ai = ForensicAI()
        all_results = []
        
        for data in data_items:
            content = data.get_file_content()  # À implémenter dans CollectedData
            results = ai.analyze(content, data.data_type)
            
            # Sauvegarde en base
            for res_type, res_data in results.items():
                AnalysisResult.objects.create(
                    data=data,
                    analysis_type=res_type,
                    result_json=res_data,
                    confidence=0.8 if res_type == 'llm_summary' else 0.9,
                    is_critical=res_type == 'fraud'
                )
            all_results.append(results)
        
        return Response({'status': 'success', 'results': all_results})

class DownloadReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        session = ForensicSession.objects.get(session_id=session_id, user=request.user)
        results = AnalysisResult.objects.filter(data__session=session)
        
        # Génération PDF
        pdf_path = PDFGenerator.generate(session, {
            'fraud': [r.result_json for r in results if r.analysis_type == 'fraud'],
            'llm_summary': next((r.result_json for r in results if r.analysis_type == 'llm_summary'), '')
        })
        
        # Sauvegarde du rapport
        with open(pdf_path, 'rb') as f:
            report = ForensicReport.objects.create(
                session=session,
                pdf_file=f
            )
        
        return FileResponse(open(pdf_path, 'rb'), filename=os.path.basename(pdf_path))
    

from django.shortcuts import render, get_object_or_404
from api.models import ForensicSession

def session_analysis_view(request, session_id):
    session = get_object_or_404(
        ForensicSession.objects
            .prefetch_related('collected_items__results')  # Correction ici
            .select_related('user'),  # Si vous avez une relation ForeignKey vers user
        session_id=session_id
    )
    
    context = {
        'session': session,
        'fraud_results': session.collected_items.filter(
            results__analysis_type='fraud'
        ),
        'sentiment_results': session.collected_items.filter(
            results__analysis_type='sentiment'
        ).first(),
        'technical_results': session.collected_items.filter(
            results__analysis_type__in=['anomaly', 'llm']
        )
    }
    return render(request, 'analysis/session_detail.html', context)
from rest_framework import generics
from .models import ForensicReport
from .serializers import ForensicReportSerializer
from django_filters.rest_framework import DjangoFilterBackend

class ReportListView(generics.ListAPIView):
    serializer_class = ForensicReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['session__session_id', 'generated_at']

    def get_queryset(self):
        return ForensicReport.objects.filter(
            session__user=self.request.user
        ).select_related('session')

class ReportDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ForensicReportSerializer
    
    def get_queryset(self):
        return ForensicReport.objects.filter(
            session__user=self.request.user
        )
    

# analysis/views.py
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView
from api.models import ForensicSession

class AnalysisDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'analysis/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sessions'] = ForensicSession.objects.filter(
            user=self.request.user
        ).prefetch_related('collected_items__results')
        return context

class AnalysisDetailView(LoginRequiredMixin, DetailView):
    model = ForensicSession
    template_name = 'analysis/session_detail.html'
    slug_field = 'session_id'
    slug_url_kwarg = 'session_id'
    
    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
    




from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from .services import ForensicAI
from api.models import ForensicSession, CollectedData
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import logging
logger = logging.getLogger(__name__)

@require_POST
@login_required

def analyze_session(request, session_id):
    """Version complètement revue de la vue d'analyse"""
    try:
        # 1. Vérification de base
        session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
        data_items = session.collected_items.all()
        
        if not data_items.exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Aucune donnée à analyser'
            }, status=400)

        # 2. Initialisation
        ai = ForensicAI()
        results = []
        analysed_count = 0
        failed_count = 0
        error_details = []

        # 3. Analyse séquentielle avec logging
        for index, data in enumerate(data_items, 1):
            try:
                logger.info(f"Analyse item {index}/{len(data_items)} (ID: {data.id}, Type: {data.data_type})")
                
                content = data.get_file_content()
                if content is None:
                    error_details.append(f"Donnée {data.id}: contenu vide ou inaccessible")
                    failed_count += 1
                    continue
                
                # Journalisation du contenu (debug)
                logger.debug(f"Contenu à analyser (extrait): {str(content)[:200]}...")
                
                # Analyse réelle
                result = ai.analyze(content, data.data_type)
                if not result:
                    error_details.append(f"Donnée {data.id}: analyse retour vide")
                    failed_count += 1
                    continue
                
                # Sauvegarde des résultats
                for res_type, res_data in result.items():
                    AnalysisResult.objects.update_or_create(
                        data=data,
                        analysis_type=res_type,
                        defaults={
                            'result_json': res_data,
                            'confidence': 0.8 if res_type == 'llm_summary' else 0.9,
                            'is_critical': res_type == 'fraud' and bool(res_data)
                        }
                    )
                
                analysed_count += 1
                results.append({'data_id': data.id, 'result_keys': list(result.keys())})
                
            except Exception as e:
                logger.error(f"Échec analyse donnée {data.id}: {str(e)}")
                failed_count += 1
                error_details.append(f"Donnée {data.id}: {str(e)}")
                continue

        # 4. Mise à jour de la session
        session.refresh_from_db()
        
        # 5. Réponse détaillée
        response_data = {
            'status': 'success',
            'session_id': session_id,
            'analysed_items': analysed_count,
            'failed_items': failed_count,
            'total_items': len(data_items),
            'results_count': len(results),
            'message': (
                f"Analyse terminée - {analysed_count} succès, {failed_count} échecs. "
                f"Voir les logs pour détails."
            )
        }
        
        if error_details:
            response_data['error_details'] = error_details[:10]  # Limite à 10 erreurs
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.critical(f"Erreur critique dans analyze_session: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f"Erreur système: {str(e)}"
        }, status=500)
    


    from django.http import FileResponse
from django.shortcuts import get_object_or_404
from .services import PDFGenerator  # Importez votre classe PDFGenerator

def generate_report(request, session_id):
    session = get_object_or_404(
        ForensicSession.objects
            .prefetch_related('collected_items__results')
            .select_related('user'),
        session_id=session_id
    )
    
    # Générer le PDF
    pdf_path = PDFGenerator.generate(session, {
        'fraud_results': session.collected_items.filter(results__analysis_type='fraud'),
        'sentiment_results': session.collected_items.filter(results__analysis_type='sentiment').first(),
        'technical_results': session.collected_items.filter(results__analysis_type__in=['anomaly', 'llm'])
    })
    
    # Retourner le fichier PDF
    return FileResponse(open(pdf_path, 'rb'), filename=f'report_{session_id}.pdf')






# Ajoutez ces imports en haut du fichier
from django.conf import settings  # Pour résoudre 'settings' is not defined
import traceback  # Pour résoudre 'traceback' is not defined
import os
import logging
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from api.models import ForensicSession
from .services import ForensicAI

logger = logging.getLogger(__name__)

@login_required
def test_analysis_pipeline(request, session_id):
    """
    Vue de test pour vérifier chaque étape du processus d'analyse
    Accès via: /analysis/test_pipeline/<session_id>/
    """
    try:
        session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
        test_results = []
        
        # Limite aux 5 premiers éléments pour le test
        for data in session.collected_items.all()[:5]:
            entry = {
                'data_id': data.id,
                'data_type': data.data_type,
                'file_path': data.get_absolute_file_path(),
                'file_exists': os.path.exists(data.get_absolute_file_path()),
                'file_size': os.path.getsize(data.get_absolute_file_path()) if os.path.exists(data.get_absolute_file_path()) else 0
            }
            
            # Test lecture fichier
            try:
                content = data.get_file_content()
                entry['content_type'] = type(content).__name__ if content else 'None'
                entry['content_length'] = len(content) if hasattr(content, '__len__') else 'N/A'
                
                # Sample du contenu
                if isinstance(content, (list, dict, str)):
                    entry['content_sample'] = str(content)[:200] + ('...' if len(str(content)) > 200 else '')
                else:
                    entry['content_sample'] = 'Type non affichable'
                
                # Test analyse
                if content:
                    ai = ForensicAI()
                    try:
                        result = ai.analyze(content, data.data_type)
                        entry['analysis_success'] = bool(result)
                        if result:
                            entry['result_keys'] = list(result.keys())
                            entry['result_sample'] = {k: str(v)[:100] for k, v in list(result.items())[:2]}
                    except Exception as e:
                        entry['analysis_error'] = str(e)
                        logger.error(f"Test failed for data {data.id}: {str(e)}", exc_info=True)
            
            except Exception as e:
                entry['content_error'] = str(e)
                logger.error(f"Failed to read content for data {data.id}: {str(e)}", exc_info=True)
            
            test_results.append(entry)
        
        return JsonResponse({
            'session': session_id,
            'test_results': test_results,
            'debug_info': {
                'MEDIA_ROOT': settings.MEDIA_ROOT,
                'ai_config': getattr(settings, 'AI_CONFIG', {}),
                'total_items': session.collected_items.count()
            }
        })
        
    except Exception as e:
        logger.exception("Critical error in test_analysis_pipeline")
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)