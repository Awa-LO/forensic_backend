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

@require_POST
@login_required

def analyze_session(request, session_id):
    """Vue pour lancer l'analyse d'une session"""
    session = get_object_or_404(ForensicSession, session_id=session_id)
    data_items = CollectedData.objects.filter(session=session)
    
    if not data_items.exists():
        return JsonResponse({'error': 'Aucune donnée à analyser'}, status=400)
    
    try:
        ai = ForensicAI()
        for data in data_items:
            ai.analyze(data.get_file_content(), data.data_type)
        return redirect('analysis:session_analysis', session_id=session_id)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    


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