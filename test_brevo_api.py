import os
import json
import urllib.request
import re

api_key = os.environ.get('EMAIL_HOST_PASSWORD', '')

data = {
    "sender": {"name": "Test Script", "email": "marthisashikant35@gmail.com"},
    "to": [{"email": "marthisashikant35@gmail.com"}],
    "subject": "Brevo API Test",
    "htmlContent": "<p>Testing the REST API method inside Railway</p>"
}

url = "https://api.brevo.com/v3/smtp/email"
req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'))
req.add_header('api-key', api_key)
req.add_header('Content-Type', 'application/json')
req.add_header('Accept', 'application/json')

try:
    response = urllib.request.urlopen(req)
    print("Success:", response.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
