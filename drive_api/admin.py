from django.contrib import admin
from .models import DriveFile

@admin.register(DriveFile)
class DriveFileAdmin(admin.ModelAdmin):
    list_display = ('name', 'mime_type', 'created_time', 'modified_time', 'size')
    list_filter = ('mime_type', 'created_time', 'modified_time')
    search_fields = ('name', 'drive_id')
    readonly_fields = ('drive_id', 'web_view_link', 'web_content_link')
    date_hierarchy = 'created_time'
