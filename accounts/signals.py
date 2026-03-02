from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
import random


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        colors = ['#6C63FF', '#FF6584', '#06d6a0', '#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899']
        Profile.objects.create(user=instance, avatar_color=random.choice(colors))


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
