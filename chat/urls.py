from django.urls import path
from . import views

urlpatterns = [
    path('request/<int:pk>/chat/', views.chat_room, name='chat_room'),
    path('request/<int:pk>/chat/send/', views.send_message, name='send_message'),
    path('request/<int:pk>/chat/fetch/', views.fetch_messages, name='fetch_messages'),
    path('my-chats/', views.my_chats, name='my_chats'),
]
