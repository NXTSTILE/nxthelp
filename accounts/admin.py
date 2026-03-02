from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'profession', 'department', 'year', 'created_at')
    list_filter = ('year', 'department')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'profession')
