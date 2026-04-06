import os
import smtplib
from email.mime.text import MIMEText

host = os.environ.get('EMAIL_HOST', 'smtp-relay.brevo.com')
port = int(os.environ.get('EMAIL_PORT', 587))
user = os.environ.get('EMAIL_HOST_USER')
password = os.environ.get('EMAIL_HOST_PASSWORD')
from_email = os.environ.get('DEFAULT_FROM_EMAIL', 'test@example.com')

print(f"Connecting to {host}:{port}...")
try:
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        print(f"Logging in as {user}...")
        server.login(user, password)
        
        msg = MIMEText('This is a test email.')
        msg['Subject'] = 'Test Email From Railway Shell'
        msg['From'] = from_email
        msg['To'] = 'marthisashikant35@gmail.com'
        
        print("Sending mail...")
        server.send_message(msg)
        print("Done!")
except Exception as e:
    print(f"Failed: {e}")
