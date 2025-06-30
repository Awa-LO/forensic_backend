from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
import os
import json

User = get_user_model()

class ForensicSession(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_id = models.CharField(max_length=255, unique=True)
    device_info = models.JSONField(default=dict)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    total_items = models.IntegerField(default=0)
    device_name = models.CharField(max_length=255, blank=True, null=True)
    android_version = models.CharField(max_length=50, blank=True, null=True)
    save_path = models.CharField(max_length=512, blank=True, null=True)
    def get_storage_path(self):
        return f"forensic_data/{self.start_time.strftime('%Y/%m/%d')}/{self.session_id}/"
    
    def get_absolute_path(self):
        from django.conf import settings
        return os.path.join(settings.MEDIA_ROOT, self.get_storage_path())
    
    def save(self, *args, **kwargs):
        # Extraction automatique des infos depuis device_info
        if self.device_info:
            if not self.device_name and 'model' in self.device_info:
                self.device_name = self.device_info.get('model')
            if not self.android_version and 'version' in self.device_info:
                self.android_version = self.device_info.get('version')
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"Session {self.session_id} ({self.status})"
    

    def get_device_info(self):
        """Charge les infos de l'appareil depuis le rapport ou les champs sauvegardés"""
        if self.device_info and self.device_info.get('model'):
            return self.device_info
        
        # Cherche le fichier rapport
        report_file = self.collected_items.filter(
            file__icontains='collection_report'
        ).first()
        
        if report_file:
            try:
                with open(report_file.file.path, 'r') as f:
                    report = json.load(f)
                    if isinstance(report, list) and report:
                        self.device_info = report[0].get('device_info', {})
                        self.save()
                        return self.device_info
            except Exception:
                pass
        
        return {
            'model': self.device_name or 'Inconnu',
            'manufacturer': 'Inconnu',
            'android_version': self.android_version or 'Inconnu',
            'api_level': 0
        }

class CollectedData(models.Model):
    DATA_TYPES = [
        ('sms', 'SMS'),
        ('calls', 'Appels'),
        ('contacts', 'Contacts'),
        ('images', 'Images'),
        ('videos', 'Vidéos'),
        ('audio', 'Audio'),
    ]

    session = models.ForeignKey(ForensicSession, on_delete=models.CASCADE, related_name='collected_items')
    data_type = models.CharField(max_length=20, choices=DATA_TYPES)
    file = models.FileField(
        upload_to='forensic_data/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['json', 'csv'])],
        default='collected_data/default.json' 
    )
    file_size = models.BigIntegerField()
    item_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)
    is_analyzed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_data_type_display()} ({self.item_count} items)"
    

    def get_file_content(self):
        """Retourne le contenu analysable du fichier"""
        if self.file.name.endswith('.json'):
            with self.file.open('r') as f:
                return json.load(f)
        elif self.file.name.endswith('.csv'):
            import pandas as pd
            return pd.read_csv(self.file.path).to_dict('records')
        return None

        