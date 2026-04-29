from work.models import Notification


def notify_payment_received(help_request, payer, payment):
    Notification.objects.create(
        recipient=help_request.selected_helper,
        notification_type='payment_received',
        title='Payment received! 💰',
        message=f'{payer.profile.display_name} sent you ₹{payment.amount} for "{help_request.title}" via Razorpay.',
        link=f'/request/{help_request.pk}/payment/receipt/',
    )
