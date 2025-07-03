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
    is_analyzed = models.BooleanField(default=False)
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

import os
import json
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class CollectedData(models.Model):
    DATA_TYPES = [
        ('sms', 'SMS'),
        ('calls', 'Appels'),
        ('contacts', 'Contacts'),
        ('images', 'Images'),
        ('videos', 'Vidéos'),
        ('audio', 'Audio'),
        ('device_report', 'Rapport Appareil'),
        ('other', 'Autre'),
    ]

    session = models.ForeignKey(
        'ForensicSession',
        on_delete=models.CASCADE,
        related_name='collected_items'
    )
    data_type = models.CharField(
        max_length=20,
        choices=DATA_TYPES,
        default='other'
    )
    file = models.FileField(
        upload_to='forensic_data/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['json', 'csv', 'zip'])],
        verbose_name='Fichier de données'
    )
    file_size = models.BigIntegerField(
        default=0,
        verbose_name='Taille du fichier (octets)'
    )
    item_count = models.IntegerField(
        default=0,
        verbose_name='Nombre d\'éléments'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de création'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Métadonnées'
    )
    is_analyzed = models.BooleanField(
        default=False,
        verbose_name='Analysé'
    )
    original_filename = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Nom original du fichier'
    )

    class Meta:
        verbose_name = 'Donnée Collectée'
        verbose_name_plural = 'Données Collectées'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['data_type']),
            models.Index(fields=['is_analyzed']),
            models.Index(fields=['session']),
        ]

    def __str__(self):
        return f"{self.get_data_type_display()} - {self.original_filename or self.file.name}"

    def save(self, *args, **kwargs):
        """Surcharge de la méthode save pour calculer automatiquement la taille et le nombre d'items"""
        if self.file and not self.file_size:
            self.file_size = self.file.size
        
        if not self.original_filename and hasattr(self.file, 'name'):
            self.original_filename = os.path.basename(self.file.name)
        
        super().save(*args, **kwargs)

    def get_absolute_file_path(self):
        """Retourne le chemin absolu du fichier"""
        return os.path.join(settings.MEDIA_ROOT, self.file.name)

    def file_exists(self):
        """Vérifie si le fichier physique existe"""
        return os.path.exists(self.get_absolute_file_path())

    def get_file_content(self):
        """
        Retourne le contenu analysable du fichier
        Gère les JSON, CSV et fichiers ZIP automatiquement
        """
        if not self.file_exists():
            logger.error(f"Fichier {self.get_absolute_file_path()} n'existe pas")
            return None

        try:
            file_path = self.get_absolute_file_path()
            
            # Fichiers JSON
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        self.item_count = len(content)
                    return content
            
            # Fichiers CSV
            elif file_path.endswith('.csv'):
                import pandas as pd
                df = pd.read_csv(file_path)
                self.item_count = len(df)
                return df.to_dict('records')
            
            # Fichiers ZIP
            elif file_path.endswith('.zip'):
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    self.item_count = len(file_list)
                    return {
                        'zip_contents': file_list,
                        'main_file': self._extract_main_file(zip_ref)
                    }
            
            else:
                logger.warning(f"Format de fichier non supporté: {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"Erreur lecture fichier {file_path}: {str(e)}", exc_info=True)
            return None

    def _extract_main_file(self, zip_ref):
        """Extrait le fichier principal d'une archive ZIP"""
        for file in zip_ref.namelist():
            if file.endswith('.json') and 'report' in file.lower():
                with zip_ref.open(file) as f:
                    return json.load(f)
        return None

    def get_preview(self, max_items=5):
        """Retourne un aperçu des données"""
        content = self.get_file_content()
        if not content:
            return None
        
        if isinstance(content, list):
            return content[:max_items]
        elif isinstance(content, dict):
            return {k: content[k] for k in list(content.keys())[:max_items]}
        return content

        