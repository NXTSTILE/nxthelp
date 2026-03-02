from django.contrib import admin
from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'help_request', 'content', 'is_read', 'created_at')
    list_filter = ('is_read',)
    raw_id_fields = ('sender', 'help_request')
