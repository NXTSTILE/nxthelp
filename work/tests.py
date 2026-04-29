import json
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from work.models import Application, Category, HelpRequest, Notification, Payment


class WorkFlowSafetyTests(TestCase):
    def setUp(self):
        self.poster = User.objects.create_user(username='poster', password='pass12345')
        self.helper = User.objects.create_user(username='helper', password='pass12345')
        self.other = User.objects.create_user(username='other', password='pass12345')

        self.category = Category.objects.create(name='Academic', slug='academic')
        self.help_request = HelpRequest.objects.create(
            title='Need assignment help',
            description='Need help by tomorrow',
            posted_by=self.poster,
            category=self.category,
            status='in_progress',
            budget='600',
            selected_helper=self.helper,
        )
        self.application = Application.objects.create(
            help_request=self.help_request,
            applicant=self.helper,
            message='I can help',
            proposed_budget='450',
            status='accepted',
        )

    def test_key_pages_render_for_authenticated_user(self):
        self.client.force_login(self.poster)
        urls = [
            reverse('dashboard'),
            reverse('my_requests'),
            reverse('browse_requests'),
            reverse('help_request_detail', kwargs={'pk': self.help_request.pk}),
            reverse('payment_page', kwargs={'pk': self.help_request.pk}),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_create_razorpay_order_rejects_non_owner(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse('create_razorpay_order', kwargs={'pk': self.help_request.pk}),
            data=json.dumps({'note': 'thanks'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    @patch('work.views.get_razorpay_client')
    def test_create_razorpay_order_uses_backend_amount(self, mock_get_client):
        client = Mock()
        client.order.create.return_value = {'id': 'order_123'}
        mock_get_client.return_value = client

        self.client.force_login(self.poster)
        response = self.client.post(
            reverse('create_razorpay_order', kwargs={'pk': self.help_request.pk}),
            data=json.dumps({'amount': 1, 'note': 'attempt override'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['amount'], 45000)
        self.assertEqual(payload['order_id'], 'order_123')

        payment = Payment.objects.get(help_request=self.help_request, razorpay_order_id='order_123')
        self.assertEqual(float(payment.amount), 450.0)
        self.assertEqual(payment.payer, self.poster)
        self.assertEqual(payment.payee, self.helper)

    @patch('work.views.get_razorpay_client')
    def test_confirm_payment_success_marks_resolved_and_notifies_helper(self, mock_get_client):
        client = Mock()
        client.utility.verify_payment_signature.return_value = True
        mock_get_client.return_value = client

        Payment.objects.create(
            help_request=self.help_request,
            payer=self.poster,
            payee=self.helper,
            amount='450.00',
            payment_method='razorpay',
            status='created',
            razorpay_order_id='order_123',
        )

        self.client.force_login(self.poster)
        response = self.client.post(
            reverse('confirm_payment', kwargs={'pk': self.help_request.pk}),
            data={
                'razorpay_payment_id': 'pay_123',
                'razorpay_order_id': 'order_123',
                'razorpay_signature': 'sig_123',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.help_request.refresh_from_db()
        self.assertEqual(self.help_request.status, 'resolved')

        payment = Payment.objects.get(razorpay_order_id='order_123')
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.razorpay_payment_id, 'pay_123')

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.helper,
                notification_type='payment_received',
                link=reverse('payment_receipt', kwargs={'pk': self.help_request.pk}),
            ).exists()
        )

    def test_payment_receipt_rejects_unrelated_user(self):
        Payment.objects.create(
            help_request=self.help_request,
            payer=self.poster,
            payee=self.helper,
            amount='450.00',
            payment_method='razorpay',
            status='completed',
            razorpay_order_id='order_abc',
        )
        self.client.force_login(self.other)
        response = self.client.get(reverse('payment_receipt', kwargs={'pk': self.help_request.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
