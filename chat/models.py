from django.db import models
from django.contrib.auth.models import User


class ChatMessage(models.Model):
    """Chat messages between a poster and their selected helper."""
    help_request = models.ForeignKey(
        'work.HelpRequest', on_delete=models.CASCADE, related_name='chat_messages'
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender.username}: {self.content[:50]}'
