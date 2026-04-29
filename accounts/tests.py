from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AccountSmokeTests(TestCase):
    def test_public_auth_pages_render(self):
        for name in ['landing', 'login', 'register', 'verify_otp', 'resend_verification']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_profile_renders_for_authenticated_user(self):
        user = User.objects.create_user(username='demo', password='pass12345')
        self.client.force_login(user)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
