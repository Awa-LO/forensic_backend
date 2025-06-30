from rest_framework import serializers
from .models import AnalysisResult, ForensicReport  # Import manquant ajouté
from api.models import ForensicSession  # Import pour la relation

class AnalysisResultSerializer(serializers.ModelSerializer):
    data_type = serializers.CharField(source='data.get_data_type_display', read_only=True)
    
    class Meta:
        model = AnalysisResult
        fields = [
            'id',
            'analysis_type',
            'data_type',
            'confidence',
            'is_critical',
            'created_at',
            'result_json'  # Inclure les résultats bruts
        ]

class ForensicReportSerializer(serializers.ModelSerializer):
    session_id = serializers.CharField(source='session.session_id', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ForensicReport
        fields = [
            'id',
            'session_id',
            'generated_at',
            'download_url',
            'pdf_file'
        ]
    
    def get_download_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_file and hasattr(obj.pdf_file, 'url'):
            return request.build_absolute_uri(obj.pdf_file.url)
        return None