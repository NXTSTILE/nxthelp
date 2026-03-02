"""
URL configuration for nxthelp project.
Routes split across three apps: accounts, work, chat.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('work.urls')),
    path('', include('chat.urls')),
]
