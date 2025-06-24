from rest_framework import serializers
from .models import ForensicSession, CollectedData

class DataUploadSerializer(serializers.Serializer):
    """Sérialiseur pour l'upload de données individuelles"""
    session_id = serializers.CharField(max_length=255)
    data_type = serializers.ChoiceField(choices=CollectedData.DATA_TYPES)
    data_file = serializers.FileField()
    item_count = serializers.IntegerField(default=0)
    device_model = serializers.CharField(required=False, allow_blank=True)
    android_version = serializers.CharField(required=False, allow_blank=True)

class ZipUploadSerializer(serializers.Serializer):
    """Sérialiseur pour l'upload de fichiers ZIP"""
    data_file = serializers.FileField()
    
    def validate_data_file(self, value):
        """Valide que le fichier est un ZIP"""
        if not value.name.endswith('.zip'):
            raise serializers.ValidationError("Le fichier doit être un ZIP")
        
        # Limite de taille (ex: 100MB)
        if value.size > 100 * 1024 * 1024:
            raise serializers.ValidationError("Fichier trop volumineux (max 100MB)")
            
        return value

class ForensicSessionSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les sessions forensiques"""
    collected_items = serializers.SerializerMethodField()
    
    class Meta:
        model = ForensicSession
        fields = [
            'session_id', 'device_info', 'start_time', 'end_time',
            'status', 'total_items', 'collected_items'
        ]
        read_only_fields = ['session_id', 'start_time']
    
    def get_collected_items(self, obj):
        """Retourne les éléments collectés pour cette session"""
        items = obj.collected_items.all()
        return CollectedDataSerializer(items, many=True).data

class CollectedDataSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les données collectées"""
    data_type_display = serializers.CharField(source='get_data_type_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CollectedData
        fields = [
            'id', 'data_type', 'data_type_display', 'file_url',
            'file_size', 'item_count', 'created_at', 'metadata', 'is_analyzed'
        ]
    
    def get_file_url(self, obj):
        """Retourne l'URL du fichier"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None