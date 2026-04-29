from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, OuterRef, Subquery
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from django_ratelimit.decorators import ratelimit
import razorpay
import json
import re
from .models import HelpRequest, Application, Notification, Category, Payment
from .forms import HelpRequestForm, ApplicationForm
from chat.models import ChatMessage

# ─── Razorpay lazy client ────────────────────────────────────────
# Initialized on first use so the server doesn't crash at startup
# if keys are missing (e.g. in local dev without payment setup).
_razorpay_client = None


def get_razorpay_client():
    """Return a lazily initialized Razorpay client. Raises clearly if keys are missing."""
    global _razorpay_client
    if _razorpay_client is None:
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise ValueError(
                "Razorpay API keys are not configured. "
                "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in your .env file."
            )
        _razorpay_client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    return _razorpay_client


# ─── Dashboard ───────────────────────────────────────────────────

@login_required
def dashboard(request):
    """Unified dashboard — everyone sees the same structure."""
    profile = request.user.profile
    today = timezone.now().date()

    # My posted requests
    my_requests = HelpRequest.objects.filter(
        posted_by=request.user
    ).select_related('category').annotate(
        app_count=Count('applications')
    )

    # My sent applications
    my_applications = Application.objects.filter(
        applicant=request.user
    ).select_related('help_request', 'help_request__posted_by', 'help_request__posted_by__profile', 'help_request__category')

    # Open requests I can help with (not my own, not already applied)
    available_requests = HelpRequest.objects.filter(
        status='open'
    ).exclude(
        posted_by=request.user
    ).exclude(
        applications__applicant=request.user
    ).select_related(
        'posted_by', 'posted_by__profile', 'category'
    ).annotate(app_count=Count('applications'))[:6]

    # Unread chat count
    unread_chats = ChatMessage.objects.filter(
        Q(help_request__posted_by=request.user) | Q(application__applicant=request.user),
        is_read=False
    ).exclude(sender=request.user).count()

    context = {
        'profile': profile,
        # My requests stats
        'my_requests': my_requests[:5],
        'total_posted': my_requests.count(),
        'open_count': my_requests.filter(status='open').count(),
        'in_progress_count': my_requests.filter(status='in_progress').count(),
        'resolved_count': my_requests.filter(status='resolved').count(),
        # My applications stats
        'my_applications': my_applications[:5],
        'total_applied': my_applications.count(),
        'pending_apps': my_applications.filter(status='pending').count(),
        'accepted_apps': my_applications.filter(status='accepted').count(),
        # Pending applications on my requests
        'pending_on_my_requests': Application.objects.filter(
            help_request__posted_by=request.user,
            status='pending'
        ).count(),
        # Available to help
        'available_requests': available_requests,
        # Upcoming deadlines
        'upcoming_deadlines': my_requests.filter(
            deadline__isnull=False,
            deadline__gte=today,
            status__in=['open', 'in_progress']
        ).order_by('deadline')[:5],
        # Notifications
        'recent_notifications': Notification.objects.filter(
            recipient=request.user, is_read=False
        )[:5],
        # Chats
        'unread_chats': unread_chats,
    }

    return render(request, 'work/dashboard.html', context)


# ─── Help Requests ───────────────────────────────────────────────

@login_required
def create_help_request(request):
    """Any user can create a help request."""
    if request.method == 'POST':
        form = HelpRequestForm(request.POST, request.FILES)
        if form.is_valid():
            help_req = form.save(commit=False)
            help_req.posted_by = request.user
            help_req.save()
            messages.success(request, 'Your request has been posted!')
            return redirect('help_request_detail', pk=help_req.pk)
    else:
        form = HelpRequestForm()
    return render(request, 'work/create_request.html', {'form': form})


@login_required
def help_request_detail(request, pk):
    """View a specific help request with applicants and chat threads."""
    help_req = get_object_or_404(HelpRequest, pk=pk)
    context = {
        'help_request': help_req,
    }

    if request.user == help_req.posted_by:
        # Poster sees all applicants with chat thread info
        last_chat_content = ChatMessage.objects.filter(
            application=OuterRef('pk')
        ).order_by('-created_at').values('content')[:1]
        
        last_chat_sender = ChatMessage.objects.filter(
            application=OuterRef('pk')
        ).order_by('-created_at').values('sender__profile__display_name')[:1]

        applications = help_req.applications.all().select_related(
            'applicant', 'applicant__profile'
        ).annotate(
            unread_count=Count(
                'chat_messages',
                filter=Q(chat_messages__is_read=False) & ~Q(chat_messages__sender=request.user)
            ),
            last_chat_content=Subquery(last_chat_content),
            last_chat_sender_name=Subquery(last_chat_sender)
        )
        context['applications'] = applications
        context['is_owner'] = True
    else:
        context['is_owner'] = False
        existing = help_req.applications.filter(applicant=request.user).first()
        context['existing_application'] = existing
        if not existing and help_req.is_open and request.user != help_req.posted_by:
            context['application_form'] = ApplicationForm()

    return render(request, 'work/request_detail.html', context)


@login_required
def browse_requests(request):
    """Browse all open help requests."""
    requests_qs = HelpRequest.objects.filter(status='open').select_related(
        'posted_by', 'posted_by__profile', 'category'
    ).annotate(app_count=Count('applications'))

    # Filtering
    category_slug = request.GET.get('category')
    urgency = request.GET.get('urgency')
    request_type = request.GET.get('request_type')
    target_year = request.GET.get('target_year')
    search = request.GET.get('q')

    if category_slug:
        requests_qs = requests_qs.filter(category__slug=category_slug)
    if urgency:
        requests_qs = requests_qs.filter(urgency=urgency)
    if request_type:
        requests_qs = requests_qs.filter(request_type=request_type)
    if target_year:
        requests_qs = requests_qs.filter(Q(target_year=target_year) | Q(target_year='all'))
    if search:
        requests_qs = requests_qs.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    categories = Category.objects.all()
    
    # Check if AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax') == '1'

    paginator = Paginator(requests_qs, 12) # 12 requests per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'help_requests': page_obj,
        'categories': categories,
        'current_category': category_slug,
        'current_urgency': urgency,
        'current_request_type': request_type,
        'current_target_year': target_year,
        'search_query': search or '',
    }
    
    if is_ajax:
        return render(request, 'work/partials/requests_list.html', context)
        
    return render(request, 'work/browse_requests.html', context)


@login_required
def my_requests(request):
    """View my own posted help requests."""
    requests_qs = HelpRequest.objects.filter(
        posted_by=request.user
    ).select_related('category').annotate(
        app_count=Count('applications')
    )
    status_filter = request.GET.get('status')
    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)
        
    paginator = Paginator(requests_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'work/my_requests.html', {
        'help_requests': page_obj,
        'status_filter': status_filter,
    })


# ─── Applications ────────────────────────────────────────────────

@login_required
@ratelimit(key='user', rate='10/d', block=True)
def apply_to_help(request, pk):
    """User applies to help — redirected to chat thread after applying."""
    help_req = get_object_or_404(HelpRequest, pk=pk)

    if request.user == help_req.posted_by:
        messages.error(request, "You can't apply to your own request.")
        return redirect('help_request_detail', pk=pk)

    if not help_req.is_open:
        messages.warning(request, 'This request is no longer accepting applications.')
        return redirect('help_request_detail', pk=pk)

    if help_req.applications.filter(applicant=request.user).exists():
        messages.warning(request, 'You have already applied to this request.')
        return redirect('help_request_detail', pk=pk)

    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.help_request = help_req
            application.applicant = request.user
            application.save()

            # Notify the poster
            Notification.objects.create(
                recipient=help_req.posted_by,
                notification_type='new_application',
                title='New application received',
                message=f'{request.user.profile.display_name} wants to help with "{help_req.title}"',
                link=f'/request/{help_req.pk}/',
            )

            messages.success(request, 'Application submitted! You can now chat with the poster.')
            return redirect('chat_room', pk=help_req.pk, app_pk=application.pk)
    else:
        form = ApplicationForm()

    return render(request, 'work/apply.html', {'form': form, 'help_request': help_req})


@login_required
def withdraw_application(request, pk):
    """Applicant withdraws their application."""
    application = get_object_or_404(Application, pk=pk)

    if request.user != application.applicant:
        messages.error(request, 'You can only manage your own applications.')
        return redirect('dashboard')

    if request.method == 'POST':
        application.status = 'withdrawn'
        application.save()

        Notification.objects.create(
            recipient=application.help_request.posted_by,
            notification_type='application_rejected',
            title='Applicant withdrew',
            message=f'{request.user.profile.display_name} withdrew from "{application.help_request.title}".',
            link=f'/request/{application.help_request.pk}/',
        )

        messages.success(request, 'You have withdrawn your application.')

    return redirect('help_request_detail', pk=application.help_request.pk)


@login_required
def resolve_request(request, pk):
    """Mark a help request as resolved."""
    help_req = get_object_or_404(HelpRequest, pk=pk)

    if request.user != help_req.posted_by:
        messages.error(request, 'Only the request author can resolve it.')
        return redirect('help_request_detail', pk=pk)

    if request.method == 'POST':
        help_req.status = 'resolved'
        help_req.save()

        # Notify all active applicants
        for app in help_req.applications.exclude(status='withdrawn'):
            Notification.objects.create(
                recipient=app.applicant,
                notification_type='request_resolved',
                title='Request resolved',
                message=f'"{help_req.title}" has been marked as resolved.',
                link=f'/request/{help_req.pk}/',
            )

        messages.success(request, 'Your help request has been marked as resolved!')
    return redirect('help_request_detail', pk=pk)


@login_required
def close_request(request, pk):
    """Close a help request."""
    help_req = get_object_or_404(HelpRequest, pk=pk)

    if request.user != help_req.posted_by:
        messages.error(request, 'Only the request author can close it.')
        return redirect('help_request_detail', pk=pk)

    if request.method == 'POST':
        help_req.status = 'closed'
        help_req.save()
        messages.info(request, 'Your help request has been closed.')
    return redirect('my_requests')


# ─── My Applications ────────────────────────────────────────────

@login_required
def my_applications(request):
    """View my sent applications."""
    applications = Application.objects.filter(
        applicant=request.user
    ).select_related('help_request', 'help_request__posted_by', 'help_request__category')

    status_filter = request.GET.get('status')
    if status_filter:
        applications = applications.filter(status=status_filter)

    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'work/my_applications.html', {
        'applications': page_obj,
        'status_filter': status_filter,
    })


# ─── Payment (kept for future use) ──────────────────────────────

@login_required
def payment_page(request, pk):
    """Payment page with Razorpay checkout integration."""
    help_req = get_object_or_404(HelpRequest, pk=pk)

    if request.user != help_req.posted_by:
        messages.error(request, 'Only the request poster can initiate payment.')
        return redirect('help_request_detail', pk=pk)

    if help_req.status not in ('completed', 'in_progress'):
        messages.warning(request, 'Payment is not applicable for this request.')
        return redirect('help_request_detail', pk=pk)

    if not help_req.selected_helper:
        messages.error(request, 'No helper assigned to this request.')
        return redirect('help_request_detail', pk=pk)

    helper = help_req.selected_helper
    helper_profile = helper.profile

    # Check for existing completed payment
    existing_payment = Payment.objects.filter(
        help_request=help_req,
        status='completed'
    ).first()

    # Get accepted application for proposed budget
    accepted_app = Application.objects.filter(
        help_request=help_req,
        applicant=helper,
        status='accepted'
    ).first()

    # Determine default amount (from accepted application or budget)
    default_amount = 0
    if accepted_app and accepted_app.proposed_budget:
        # Try to extract number from proposed budget
        budget_str = accepted_app.proposed_budget
        numbers = re.findall(r'[\d]+\.?[\d]*', budget_str.replace(',', ''))
        if numbers:
            default_amount = float(numbers[0])

    if not default_amount and help_req.budget:
        numbers = re.findall(r'[\d]+\.?[\d]*', help_req.budget.replace(',', ''))
        if numbers:
            default_amount = float(numbers[0])

    context = {
        'help_request': help_req,
        'helper': helper,
        'helper_profile': helper_profile,
        'existing_payment': existing_payment,
        'accepted_application': accepted_app,
        'default_amount': default_amount,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'has_upi': bool(helper_profile.upi_id),
        'has_phone': bool(helper_profile.phone_number),
    }
    return render(request, 'work/payment.html', context)


@login_required
def create_razorpay_order(request, pk):
    """Create a Razorpay order and return order details as JSON."""
    help_req = get_object_or_404(HelpRequest, pk=pk)

    if request.user != help_req.posted_by:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        note = data.get('note', '').strip()

        # Securely calculate amount on backend
        accepted_app = Application.objects.filter(
            help_request=help_req,
            applicant=help_req.selected_helper,
            status='accepted'
        ).first()

        backend_amount = 0
        if accepted_app and accepted_app.proposed_budget:
            budget_str = accepted_app.proposed_budget
            numbers = re.findall(r'[\d]+\.?[\d]*', budget_str.replace(',', ''))
            if numbers:
                backend_amount = float(numbers[0])

        if not backend_amount and help_req.budget:
            numbers = re.findall(r'[\d]+\.?[\d]*', help_req.budget.replace(',', ''))
            if numbers:
                backend_amount = float(numbers[0])

        if backend_amount <= 0:
            return JsonResponse({'error': 'Cannot determine valid payment amount from request budget.'}, status=400)

        amount = Decimal(str(backend_amount))

    except (json.JSONDecodeError, InvalidOperation, ValueError):
        return JsonResponse({'error': 'Invalid request data'}, status=400)

    # Amount in paise (Razorpay requires smallest currency unit)
    amount_paise = int(amount * 100)

    # Create Razorpay order
    try:
        razorpay_order = get_razorpay_client().order.create({
            'amount': amount_paise,
            'currency': settings.RAZORPAY_CURRENCY,
            'notes': {
                'help_request_id': str(help_req.pk),
                'payer': request.user.username,
                'payee': help_req.selected_helper.username,
                'title': help_req.title[:200],
            }
        })
    except Exception as e:
        return JsonResponse({'error': f'Failed to create order: {str(e)}'}, status=500)

    # Create Payment record in our database
    payment = Payment.objects.create(
        help_request=help_req,
        payer=request.user,
        payee=help_req.selected_helper,
        amount=amount,
        payment_method='razorpay',
        status='created',
        note=note,
        razorpay_order_id=razorpay_order['id'],
    )

    return JsonResponse({
        'order_id': razorpay_order['id'],
        'amount': amount_paise,
        'currency': settings.RAZORPAY_CURRENCY,
        'payment_pk': payment.pk,
    })


@login_required
def confirm_payment(request, pk):
    """Verify Razorpay payment signature and mark payment as completed."""
    help_req = get_object_or_404(HelpRequest, pk=pk)

    if request.user != help_req.posted_by:
        messages.error(request, 'Only the request poster can confirm payment.')
        return redirect('help_request_detail', pk=pk)

    if request.method != 'POST':
        return redirect('payment_page', pk=pk)

    razorpay_payment_id = request.POST.get('razorpay_payment_id', '')
    razorpay_order_id = request.POST.get('razorpay_order_id', '')
    razorpay_signature = request.POST.get('razorpay_signature', '')

    # Find the payment record
    payment = Payment.objects.filter(
        help_request=help_req,
        razorpay_order_id=razorpay_order_id,
        payer=request.user,
    ).first()

    if not payment:
        messages.error(request, 'Payment record not found.')
        return redirect('payment_page', pk=pk)

    # Verify signature with Razorpay
    try:
        get_razorpay_client().utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        payment.status = 'failed'
        payment.save()
        messages.error(request, 'Payment verification failed. Please try again or contact support.')
        return redirect('payment_page', pk=pk)

    # Payment verified — update records
    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = 'completed'
    payment.completed_at = timezone.now()
    payment.save()

    # Update help request status to resolved
    help_req.status = 'resolved'
    help_req.save()

    # Notify helper about payment
    Notification.objects.create(
        recipient=help_req.selected_helper,
        notification_type='payment_received',
        title='Payment received! 💰',
        message=f'{request.user.profile.display_name} sent you ₹{payment.amount} for "{help_req.title}" via Razorpay.',
        link=f'/request/{help_req.pk}/payment/receipt/',
    )

    messages.success(request, f'Payment of ₹{payment.amount} confirmed! The request has been marked as resolved.')
    return redirect('payment_receipt', pk=help_req.pk)


@login_required
def payment_receipt(request, pk):
    """Display payment receipt."""
    help_req = get_object_or_404(HelpRequest, pk=pk)

    # Only payer and payee can see the receipt
    if request.user not in [help_req.posted_by, help_req.selected_helper]:
        messages.error(request, 'You do not have access to this receipt.')
        return redirect('dashboard')

    payment = Payment.objects.filter(
        help_request=help_req,
        status='completed'
    ).order_by('-created_at').first()

    if not payment:
        messages.warning(request, 'No completed payment found for this request.')
        return redirect('help_request_detail', pk=pk)

    context = {
        'help_request': help_req,
        'payment': payment,
    }
    return render(request, 'work/payment_receipt.html', context)



# ─── Notifications ───────────────────────────────────────────────

@login_required
def notifications_view(request):
    """View all notifications."""
    notifs = Notification.objects.filter(recipient=request.user)
    return render(request, 'work/notifications.html', {'notifications': notifs})


@login_required
def mark_notification_read(request, pk):
    """Mark a notification as read."""
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.link and url_has_allowed_host_and_scheme(notif.link, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(notif.link)
    return redirect('notifications')


@login_required
def mark_all_read(request):
    """Mark all notifications as read."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.info(request, 'All notifications marked as read.')
    return redirect('notifications')


# ─── Context Processor ───────────────────────────────────────────

def notification_count(request):
    """Context processor to provide unread notification count."""
    if request.user.is_authenticated:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_notification_count': count}
    return {'unread_notification_count': 0}

@login_required
def api_unread_counts(request):
    """API endpoint to get real-time counts for unread chats and notifications."""
    unread_chats = ChatMessage.objects.filter(
        Q(help_request__posted_by=request.user) | Q(application__applicant=request.user),
        is_read=False
    ).exclude(sender=request.user).count()
    
    unread_notifs = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    return JsonResponse({
        'unread_chats': unread_chats,
        'unread_notifications': unread_notifs,
    })
