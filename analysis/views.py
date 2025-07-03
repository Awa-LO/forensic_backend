# analysis/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone

from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveDestroyAPIView
from django_filters.rest_framework import DjangoFilterBackend
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.urls import reverse
import json
import logging
import os

from api.models import ForensicSession, CollectedData
from .models import AnalysisResult, ForensicReport
from .services import ForensicAI, PDFGenerator
from .serializers import ForensicReportSerializer

logger = logging.getLogger(__name__)

class AnalysisDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard principal d'analyse"""
    template_name = 'analysis/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sessions'] = ForensicSession.objects.filter(
            user=self.request.user
        ).prefetch_related('collected_items__results').order_by('-start_time')
        return context

@login_required
def session_detail_view(request, session_id):
    """Vue détaillée d'une session avec état d'analyse"""
    session = get_object_or_404(
        ForensicSession.objects.prefetch_related('collected_items__results'),
        session_id=session_id,
        user=request.user
    )
    
    # Vérifier si l'analyse a été faite
    is_analyzed = session.collected_items.filter(results__isnull=False).exists()
    
    # Préparer les données pour l'affichage
    context = {
        'session': session,
        'is_analyzed': is_analyzed,
        'data_count': session.collected_items.count(),
        'device_info': session.device_info or {},
    }
    
    # Si analysé, charger les résultats de base
    if is_analyzed:
        context.update({
            'fraud_count': session.collected_items.filter(results__analysis_type='fraud').count(),
            'technical_count': session.collected_items.filter(results__analysis_type__in=['anomaly', 'llm']).count(),
            'has_critical': session.collected_items.filter(results__is_critical=True).exists(),
        })
    
    return render(request, 'analysis/session_detail.html', context)

@login_required
@require_POST
def analyze_session(request, session_id):
    """Lancer l'analyse d'une session"""
    session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
    
    try:
        # Vérifier qu'il y a des données à analyser
        if not session.collected_items.exists():
            msg = "Aucune donnée à analyser dans cette session."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('analysis:session_detail', session_id=session_id)
        
        # Initialiser l'IA
        ai = ForensicAI()
        analysis_count = 0
        
        # Analyser chaque donnée collectée
        for data in session.collected_items.all():
            try:
                content = data.get_file_content()
                if content:
                    # Appel à l'analyse
                    result = ai.analyze(content, data.data_type)
                    
                    if result:
                        # Détecter le type d'analyse basé sur le contenu
                        analysis_type = 'technical'  # Par défaut
                        is_critical = False
                        confidence = 0.8
                        
                        # Logique pour déterminer le type d'analyse
                        if 'anomalies' in result and result['anomalies']:
                            analysis_type = 'anomaly'
                            is_critical = len(result['anomalies']) > 0
                        elif 'llm_summary' in result:
                            analysis_type = 'llm'
                            # Analyser si le résumé suggère de la fraude
                            summary = result.get('llm_summary', '').lower()
                            if any(keyword in summary for keyword in ['fraud', 'suspicious', 'anomaly', 'irregular']):
                                analysis_type = 'fraud'
                                is_critical = True
                        
                        # Sauvegarder le résultat
                        analysis_result, created = AnalysisResult.objects.update_or_create(
                            data=data,
                            analysis_type=analysis_type,
                            defaults={
                                'result_json': result,  # Sauvegarder le résultat complet
                                'confidence': confidence,
                                'is_critical': is_critical
                            }
                        )
                        
                        if created:
                            analysis_count += 1
                            
                        # Optionnel : créer des résultats séparés pour différents aspects
                        if 'anomalies' in result and result['anomalies']:
                            AnalysisResult.objects.update_or_create(
                                data=data,
                                analysis_type='anomaly',
                                defaults={
                                    'result_json': {'anomalies': result['anomalies']},
                                    'confidence': 0.9,
                                    'is_critical': len(result['anomalies']) > 2
                                }
                            )
                        
                        if 'llm_summary' in result:
                            AnalysisResult.objects.update_or_create(
                                data=data,
                                analysis_type='llm',
                                defaults={
                                    'result_json': {'summary': result['llm_summary']},
                                    'confidence': 0.8,
                                    'is_critical': False
                                }
                            )
                    
                    logger.info(f"Analysé avec succès: {data.id}")
                    
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse de {data.id}: {str(e)}")
                continue
        
        # Marquer la session comme analysée
        session.is_analyzed = True
        session.save()
        
        # Message de succès
        msg = f"Analyse terminée avec succès. {analysis_count} résultats générés."
        
        # Répondre en JSON pour AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': msg,
                'redirect_url': reverse('analysis:session_detail', args=[session_id])
            })

        # Réponse classique
        messages.success(request, msg)
        return redirect('analysis:session_detail', session_id=session_id)
        
    except Exception as e:
        error_msg = f"Erreur lors de l'analyse: {str(e)}"
        logger.exception(error_msg)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_msg
            }, status=500)
        
        messages.error(request, error_msg)
        return redirect('analysis:session_detail', session_id=session_id)


# Fonction de debug améliorée
@login_required
def debug_analysis_session(request, session_id):
    """Debug détaillé de l'analyse"""
    session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
    
    debug_info = {
        'session_id': str(session_id),
        'total_items': session.collected_items.count(),
        'existing_results': AnalysisResult.objects.filter(data__session=session).count(),
        'session_is_analyzed': session.is_analyzed,
        'items_detail': []
    }
    
    for data in session.collected_items.all():
        item_info = {
            'data_id': data.id,
            'data_type': data.data_type,
            'has_results': data.results.exists(),
            'results_count': data.results.count(),
            'result_types': list(data.results.values_list('analysis_type', flat=True))
        }
        
        try:
            content = data.get_file_content()
            if content:
                ai = ForensicAI()
                result = ai.analyze(content, data.data_type)
                item_info['analysis_result'] = result
                item_info['can_analyze'] = True
            else:
                item_info['can_analyze'] = False
                item_info['error'] = 'No content'
        except Exception as e:
            item_info['can_analyze'] = False
            item_info['error'] = str(e)
        
        debug_info['items_detail'].append(item_info)
    
    return JsonResponse(debug_info, indent=2)


@login_required
def session_analysis_view(request, session_id):
    """Vue complète des résultats d'analyse"""
    session = get_object_or_404(
        ForensicSession.objects.prefetch_related('collected_items__results'),
        session_id=session_id,
        user=request.user
    )
    
    # Vérifier que l'analyse a été faite
    if not session.collected_items.filter(results__isnull=False).exists():
        messages.warning(request, "Cette session n'a pas encore été analysée.")
        return redirect('analysis:session_detail', session_id=session_id)
    
    # Préparer les résultats par type
    fraud_results = []
    technical_results = []
    sentiment_results = None
    
    for data in session.collected_items.all():
        for result in data.results.all():
            if result.analysis_type == 'fraud':
                fraud_results.append(result)
            elif result.analysis_type in ['anomaly', 'llm']:
                technical_results.append(result)
            elif result.analysis_type == 'sentiment':
                sentiment_results = result
    
    context = {
        'session': session,
        'fraud_results': fraud_results,
        'technical_results': technical_results,
        'sentiment_results': sentiment_results,
        'has_critical': any(r.is_critical for r in fraud_results + technical_results),
    }
    
    return render(request, 'analysis/session_analysis.html', context)

@login_required
def generate_report(request, session_id):
    """Générer un rapport PDF"""
    session = get_object_or_404(
        ForensicSession.objects.prefetch_related('collected_items__results'),
        session_id=session_id,
        user=request.user
    )
    
    # Vérifier que l'analyse a été faite
    if not session.collected_items.filter(results__isnull=False).exists():
        messages.error(request, "Impossible de générer un rapport sans analyse.")
        return redirect('analysis:session_detail', session_id=session_id)
    
    try:
        # Préparer les données pour le PDF en récupérant tous les résultats d'analyse
        all_results = {}
        
        # Parcourir toutes les données collectées et leurs résultats
        for data in session.collected_items.all():
            for result in data.results.all():
                if result.analysis_type not in all_results:
                    all_results[result.analysis_type] = []
                
                # Ajouter le résultat avec des informations contextuelles
                result_data = result.result_json.copy() if result.result_json else {}
                result_data.update({
                    'data_id': data.id,
                    'data_type': data.data_type,
                    'confidence': result.confidence,
                    'is_critical': result.is_critical,
                    'created_at': result.created_at.isoformat() if result.created_at else None
                })
                all_results[result.analysis_type].append(result_data)
        
        # Regrouper tous les résultats par type pour le PDF
        report_data = {
            'fraud': all_results.get('fraud', []),
            'anomalies': all_results.get('anomaly', []),
            'sentiment': all_results.get('sentiment', []),
            'llm_summary': all_results.get('llm', []),
            'technical': all_results.get('technical', [])
        }
        
        # Ajouter des métadonnées de session
        report_data['session_info'] = {
            'session_id': str(session.session_id),
            'user': str(session.user),
            'start_time': session.start_time.isoformat() if session.start_time else None,
            'device_info': session.device_info or {},
            'total_items': session.collected_items.count(),
            'analyzed_items': session.collected_items.filter(results__isnull=False).count(),
            'has_critical': any(
                any(r.get('is_critical', False) for r in results_list) 
                for results_list in report_data.values() 
                if isinstance(results_list, list)
            )
        }
        
        # Générer le PDF
        pdf_path = PDFGenerator.generate(session, report_data)
        
        # Vérifier que le fichier a été créé
        if not os.path.exists(pdf_path):
            raise Exception("Le fichier PDF n'a pas été créé correctement")
        
        # Optionnel : Créer l'enregistrement du rapport en base
        try:
            report = ForensicReport.objects.create(
                session=session,
                generated_at=timezone.now()
            )
            logger.info(f"Rapport enregistré en base: {report.id}")
        except Exception as e:
            logger.warning(f"Impossible d'enregistrer le rapport en base: {str(e)}")
        
        # Retourner le fichier PDF
        response = FileResponse(
            open(pdf_path, 'rb'),
            filename=f'rapport_forensic_{session.session_id}.pdf',
            content_type='application/pdf'
        )
        
        # Ajouter un message de succès
        messages.success(request, "Rapport PDF généré avec succès!")
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur génération rapport pour session {session_id}: {str(e)}")
        logger.exception("Détails de l'erreur:")
        messages.error(request, f"Erreur lors de la génération du rapport: {str(e)}")
        return redirect('analysis:session_detail', session_id=session_id)
# API Views pour les rapports
class ReportListView(LoginRequiredMixin, ListView):
    """Liste des rapports générés"""
    template_name = 'analysis/report_list.html'
    context_object_name = 'reports'
    
    def get_queryset(self):
        return ForensicReport.objects.filter(
            session__user=self.request.user,
            pdf_file__isnull=False  # Ne récupère que les rapports avec PDF
        ).exclude(pdf_file='').select_related('session').order_by('-generated_at')

class ReportDetailView(LoginRequiredMixin, DetailView):
    """Détail d'un rapport avec template HTML"""
    template_name = 'analysis/report_detail.html'
    context_object_name = 'report'
    
    def get_queryset(self):
        return ForensicReport.objects.filter(
            session__user=self.request.user
        ).select_related('session')

class ReportDetailAPIView(RetrieveDestroyAPIView):
    """API REST pour détail d'un rapport"""
    serializer_class = ForensicReportSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ForensicReport.objects.filter(
            session__user=self.request.user
        )

# API Views REST pour l'analyse
class AnalyzeDataView(APIView):
    """API pour lancer l'analyse"""
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
        data_items = CollectedData.objects.filter(session=session)
        
        ai = ForensicAI()
        all_results = []
        
        for data in data_items:
            try:
                content = data.get_file_content()
                if content:
                    results = ai.analyze(content, data.data_type)
                    
                    # Sauvegarde en base
                    for res_type, res_data in results.items():
                        AnalysisResult.objects.update_or_create(
                            data=data,
                            analysis_type=res_type,
                            defaults={
                                'result_json': res_data,
                                'confidence': res_data.get('confidence', 0.8),
                                'is_critical': res_type == 'fraud' and res_data.get('is_critical', False)
                            }
                        )
                    all_results.append(results)
            except Exception as e:
                logger.error(f"Erreur analyse API {data.id}: {str(e)}")
                continue
        
        return Response({
            'status': 'success',
            'results': all_results,
            'analyzed_count': len(all_results)
        })

# Vue de test pour le debug
@login_required
def test_analysis_pipeline(request, session_id):
    """Vue de test pour vérifier le pipeline d'analyse"""
    try:
        session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
        test_results = []
        
        for data in session.collected_items.all()[:3]:  # Limiter à 3 pour le test
            entry = {
                'data_id': data.id,
                'data_type': data.data_type,
                'file_path': data.get_absolute_file_path() if hasattr(data, 'get_absolute_file_path') else 'non disponible',

                'file_exists': os.path.exists(data.get_absolute_file_path()) if hasattr(data, 'get_absolute_file_path') else False,
            }
            
            try:
                content = data.get_file_content()
                entry['content_loaded'] = content is not None
                entry['content_type'] = type(content).__name__
                
                if content:
                    ai = ForensicAI()
                    result = ai.analyze(content, data.data_type)
                    entry['analysis_success'] = bool(result)
                    entry['result_keys'] = list(result.keys()) if result else []
                    
            except Exception as e:
                entry['error'] = str(e)
                
            test_results.append(entry)
        
        return JsonResponse({
            'session_id': str(session_id),
            'test_results': test_results,
            'total_items': session.collected_items.count()
        })
        
    except Exception as e:
        logger.exception("Erreur dans test_analysis_pipeline")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def analyze_and_redirect(request, session_id):
    """Exécuter l'analyse et rediriger"""
    session = get_object_or_404(ForensicSession, session_id=session_id, user=request.user)
    
    try:
        # 1. Exécuter l'analyse
        ai = ForensicAI()
        data_items = session.collected_items.all()
        
        for data in data_items:
            content = data.get_file_content()
            if content:
                results = ai.analyze(content, data.data_type)
                # Sauvegarder les résultats
                for res_type, res_data in results.items():
                    AnalysisResult.objects.update_or_create(
                        data=data,
                        analysis_type=res_type,
                        defaults={
                            'result_json': res_data,
                            'confidence': res_data.get('confidence', 0.8),
                            'is_critical': res_type == 'fraud'
                        }
                    )
        
        # Marquer la session comme analysée
        session.is_analyzed = True
        session.save()
        
        # 2. Rediriger vers les résultats seulement après analyse
        return redirect('analysis:session_analysis', session_id=session_id)
    
    except Exception as e:
        messages.error(request, f"Erreur lors de l'analyse: {str(e)}")
        return redirect('analysis:analysis_dashboard')