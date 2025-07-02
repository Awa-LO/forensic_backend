from django.contrib import admin
from .models import ForensicSession, CollectedData

@admin.register(ForensicSession)
class ForensicSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'status', 'start_time', 'total_items')
    list_filter = ('status', 'start_time')
    search_fields = ('session_id', 'user__username')
    readonly_fields = ('session_id', 'start_time', 'device_info')
    date_hierarchy = 'start_time'


from django.contrib import admin
from .models import CollectedData
from django.utils.html import format_html
import os
import json
class CollectedDataAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'data_type', 'file_link', 'item_count', 'created_at', 'is_analyzed')
    list_filter = ('data_type', 'is_analyzed', 'created_at')
    search_fields = ('session__session_id', 'original_filename')
    readonly_fields = ('file_preview', 'file_details')
    
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{0}">{1}</a>', 
                            obj.file.url, 
                            os.path.basename(obj.file.name))
        return "-"
    file_link.short_description = "Fichier"
    
    def file_preview(self, obj):
        preview = obj.get_preview()
        if not preview:
            return "Aucun aperçu disponible"
        
        if isinstance(preview, list):
            return format_html("<pre>{}</pre>", json.dumps(preview, indent=2))
        return format_html("<pre>{}</pre>", str(preview))
    file_preview.short_description = "Aperçu des données"
    
    def file_details(self, obj):
        return f"""
        Chemin: {obj.get_absolute_file_path()}<br>
        Existe: {'Oui' if obj.file_exists() else 'Non'}<br>
        Taille: {obj.file_size} octets
        """
    file_details.short_description = "Détails du fichier"
    file_details.allow_tags = True

admin.site.register(CollectedData, CollectedDataAdmin)