from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from work.models import Application, Category, HelpRequest


class ChatAccessTests(TestCase):
    def setUp(self):
        self.poster = User.objects.create_user(username='poster', password='pass12345')
        self.helper = User.objects.create_user(username='helper', password='pass12345')
        self.intruder = User.objects.create_user(username='intruder', password='pass12345')
        self.category = Category.objects.create(name='Academic', slug='academic')
        self.help_request = HelpRequest.objects.create(
            title='Need notes',
            description='Share class notes',
            posted_by=self.poster,
            category=self.category,
        )
        self.application = Application.objects.create(
            help_request=self.help_request,
            applicant=self.helper,
            message='I can share',
        )

    def test_chat_room_allows_participants(self):
        self.client.force_login(self.poster)
        response = self.client.get(
            reverse('chat_room', kwargs={'pk': self.help_request.pk, 'app_pk': self.application.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_chat_room_blocks_unrelated_user(self):
        self.client.force_login(self.intruder)
        response = self.client.get(
            reverse('chat_room', kwargs={'pk': self.help_request.pk, 'app_pk': self.application.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_send_message_blocks_unrelated_user(self):
        self.client.force_login(self.intruder)
        response = self.client.post(
            reverse('send_message', kwargs={'pk': self.help_request.pk, 'app_pk': self.application.pk}),
            data={'content': 'hello'},
        )
        self.assertEqual(response.status_code, 403)
