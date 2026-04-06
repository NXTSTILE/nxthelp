import os
import django
from django.core.mail import send_mail

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nxthelp.settings')
django.setup()

try:
    print(f"Attempting to send test email using {os.environ.get('EMAIL_HOST_USER')}...")
    send_mail(
        'Test Subject',
        'Test Message',
        os.environ.get('DEFAULT_FROM_EMAIL', 'test@example.com'),
        ['marthisashikant35@gmail.com'],
        fail_silently=False,
    )
    print("Email sent successfully!")
except Exception as e:
    print(f"Failed to send email: {e}")
