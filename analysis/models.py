from django.db import models
from api.models import ForensicSession, CollectedData

# Dans models.py
class AnalysisResult(models.Model):
    ANALYSIS_CHOICES = [
        ('fraud', 'Fraude'),
        ('sentiment', 'Sentiment'),
        ('anomaly', 'Anomalie'),
        ('llm', 'Analyse LLM'),
    ]
    
    data = models.ForeignKey(CollectedData, on_delete=models.CASCADE, related_name='results')
    analysis_type = models.CharField(max_length=20, choices=ANALYSIS_CHOICES)
    result_json = models.JSONField()
    confidence = models.FloatField(default=0.0)
    is_critical = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_critical', '-confidence']
        
    def __str__(self):
        return f"{self.get_analysis_type_display()} - {self.data}"

class ForensicReport(models.Model):
    session = models.ForeignKey(ForensicSession, on_delete=models.CASCADE, related_name='reports')
    pdf_file = models.FileField(upload_to='forensic_reports/%Y/%m/%d/')
    generated_at = models.DateTimeField(auto_now_add=True)
    analysis_summary = models.JSONField(default=dict)

    def delete(self, *args, **kwargs):
        self.pdf_file.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Rapport {self.session.session_id}"