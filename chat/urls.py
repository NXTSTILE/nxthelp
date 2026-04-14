from django.urls import path
from . import views

urlpatterns = [
    path('request/<int:pk>/chat/<int:app_pk>/', views.chat_room, name='chat_room'),
    path('request/<int:pk>/chat/<int:app_pk>/send/', views.send_message, name='send_message'),
    path('request/<int:pk>/chat/<int:app_pk>/fetch/', views.fetch_messages, name='fetch_messages'),
    path('my-chats/', views.my_chats, name='my_chats'),
]
