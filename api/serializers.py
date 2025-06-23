from rest_framework import serializers
from .models import CollectedData

class DataUploadSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255)
    data_type = serializers.CharField(max_length=20)
    data_file = serializers.FileField()
    item_count = serializers.IntegerField(default=0)
    device_model = serializers.CharField(required=False)
    android_version = serializers.CharField(required=False)

    def validate_data_type(self, value):
        valid_types = [choice[0] for choice in CollectedData.DATA_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError("Invalid data type")
        return value