from django.contrib import admin
from .models import ForensicSession, CollectedData

@admin.register(ForensicSession)
class ForensicSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'status', 'start_time', 'total_items')
    list_filter = ('status', 'start_time')
    search_fields = ('session_id', 'user__username')
    readonly_fields = ('session_id', 'start_time', 'device_info')
    date_hierarchy = 'start_time'

@admin.register(CollectedData)
class CollectedDataAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'data_type', 'item_count', 'created_at', 'is_analyzed')
    list_filter = ('data_type', 'is_analyzed', 'created_at')
    search_fields = ('session__session_id', 'data_type')
    readonly_fields = ('file_size', 'item_count', 'created_at')
    date_hierarchy = 'created_at'