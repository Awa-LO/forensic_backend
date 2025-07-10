from django.db import models
from api.models import ForensicSession, CollectedData
from analysis.models import AnalysisResult

class SearchResult(models.Model):
    session = models.ForeignKey(ForensicSession, on_delete=models.CASCADE, related_name='search_results')
    search_term = models.CharField(max_length=255)
    results_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recherche: {self.search_term} (Session: {self.session.session_id})"