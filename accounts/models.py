from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone
from datetime import timedelta


class Profile(models.Model):
    """Extended user profile — no role distinction, everyone is equal."""

    YEAR_CHOICES = [
        ('1', '1st Year'),
        ('2', '2nd Year'),
        ('3', '3rd Year'),
        ('4', '4th Year'),
        ('5', '5th Year / Postgrad'),
        ('alumni', 'Alumni'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profession = models.CharField(
        max_length=150, blank=True,
        help_text='e.g. Student, Faculty, Research Assistant, Lab Instructor...'
    )
    bio = models.TextField(max_length=500, blank=True)
    skills = models.CharField(max_length=300, blank=True, help_text='Comma-separated skills')
    year = models.CharField(max_length=10, choices=YEAR_CHOICES, blank=True)
    department = models.CharField(max_length=100, blank=True)
    avatar_color = models.CharField(max_length=7, default='#6C63FF')
    phone_number = models.CharField(max_length=15, blank=True, help_text='Your phone number for payments')
    upi_id = models.CharField(max_length=100, blank=True, help_text='Your UPI ID (e.g. name@upi)')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        label = self.profession or 'Member'
        return f'{self.user.username} ({label})'

    def get_skills_list(self):
        if self.skills:
            return [s.strip() for s in self.skills.split(',') if s.strip()]
        return []

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def initials(self):
        name = self.display_name
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[:2].upper()


class OTPToken(models.Model):
    """6-digit OTP sent to users to verify their email address on registration."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='otp_token')
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        expiry = self.created_at + timedelta(minutes=10)
        return timezone.now() > expiry

    def __str__(self):
        return f'OTP({self.user.username})'
