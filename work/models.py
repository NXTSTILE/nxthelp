from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from cloudinary.models import CloudinaryField


class Category(models.Model):
    """Category for help requests."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, default='fas fa-question-circle')
    color = models.CharField(max_length=7, default='#6C63FF')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class HelpRequest(models.Model):
    """A help request posted by any university member."""

    URGENCY_CHOICES = [
        ('low', 'Low — No rush'),
        ('medium', 'Medium — Within a few days'),
        ('high', 'High — Urgent, need help soon'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Work Completed'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    REQUEST_TYPE_CHOICES = [
        ('personal', 'Personal'),
        ('academic', 'Academic'),
        ('non_academic', 'Non-Academic'),
    ]

    TARGET_YEAR_CHOICES = [
        ('all', 'All Years'),
        ('1', '1st Year'),
        ('2', '2nd Year'),
        ('3', '3rd Year'),
        ('4', '4th Year'),
        ('5', '5th Year / Postgrad'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_requests')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='help_requests')
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open')
    request_type = models.CharField(max_length=15, choices=REQUEST_TYPE_CHOICES, default='personal')
    target_year = models.CharField(max_length=5, choices=TARGET_YEAR_CHOICES, default='all', help_text='Which year is this request for?')
    budget = models.CharField(
        max_length=100, blank=True,
        help_text='e.g. ₹500, Negotiable, Free, etc.'
    )
    deadline = models.DateField(null=True, blank=True, help_text='When do you need help by?')
    image = CloudinaryField('image', folder='request_images', blank=True, null=True)
    selected_helper = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='helping_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def application_count(self):
        return self.applications.count()

    @property
    def is_open(self):
        return self.status == 'open'

    @property
    def is_overdue(self):
        if self.deadline and self.status in ('open', 'in_progress'):
            return self.deadline < timezone.now().date()
        return False

    @property
    def days_until_deadline(self):
        if self.deadline:
            delta = self.deadline - timezone.now().date()
            return delta.days
        return None

    @property
    def time_since_posted(self):
        delta = timezone.now() - self.created_at
        if delta.days > 0:
            return f'{delta.days}d ago'
        hours = delta.seconds // 3600
        if hours > 0:
            return f'{hours}h ago'
        minutes = delta.seconds // 60
        return f'{minutes}m ago' if minutes > 0 else 'Just now'

    @property
    def status_css_class(self):
        return self.status.replace('_', '-')


class Application(models.Model):
    """Any user's application to help with a request."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('completed', 'Completed'),
    ]

    help_request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_applications')
    message = models.TextField(help_text='Explain how you can help')
    proposed_budget = models.CharField(
        max_length=100, blank=True,
        help_text='Your proposed price (optional)'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['help_request', 'applicant']

    def __str__(self):
        return f'{self.applicant.username} → {self.help_request.title}'


class Notification(models.Model):
    """In-app notification system."""

    TYPES = [
        ('new_application', 'New application on your request'),
        ('application_accepted', 'Your application was accepted'),
        ('application_rejected', 'Your application was rejected'),
        ('request_resolved', 'Help request resolved'),
        ('new_message', 'New chat message'),
        ('work_completed', 'Work marked as completed'),
        ('payment_initiated', 'Payment initiated'),
        ('payment_received', 'Payment received'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=25, choices=TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} → {self.recipient.username}'


class Payment(models.Model):
    """Payment transaction between poster and helper via Razorpay."""

    PAYMENT_METHOD_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('upi', 'UPI (Manual)'),
        ('phone', 'Phone Number (Manual)'),
    ]

    STATUS_CHOICES = [
        ('created', 'Order Created'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    help_request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, related_name='payments')
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_sent')
    payee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_received')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='razorpay')
    payment_address = models.CharField(
        max_length=100, blank=True,
        help_text='UPI ID or phone number used for payment'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='created')
    note = models.TextField(blank=True, help_text='Optional note for the payment')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=100, blank=True, help_text='Razorpay Order ID')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, help_text='Razorpay Payment ID')
    razorpay_signature = models.CharField(max_length=255, blank=True, help_text='Razorpay Payment Signature')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'₹{self.amount} — {self.payer.username} → {self.payee.username}'

    @property
    def masked_address(self):
        """Return partially masked payment address for privacy."""
        addr = self.payment_address
        if not addr:
            return 'Razorpay'
        if self.payment_method == 'upi' and '@' in addr:
            parts = addr.split('@')
            name = parts[0]
            if len(name) > 3:
                name = name[:3] + '***'
            return f'{name}@{parts[1]}'
        elif self.payment_method == 'phone' and len(addr) >= 6:
            return addr[:2] + '****' + addr[-4:]
        return addr

