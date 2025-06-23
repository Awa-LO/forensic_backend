from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator

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

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"Session {self.session_id} ({self.status})"

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