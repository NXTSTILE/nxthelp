from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal, InvalidOperation
import razorpay
import json
from .models import HelpRequest, Application, Notification, Category, Payment
from .forms import HelpRequestForm, ApplicationForm
from chat.models import ChatMessage

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


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
        help_request__in=HelpRequest.objects.filter(
            Q(posted_by=request.user) | Q(selected_helper=request.user),
            status='in_progress'
        ),
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
        form = HelpRequestForm(request.POST)
        if form.is_valid():
            help_req = form.save(commit=False)
            help_req.posted_by = request.user
            help_req.save()
            messages.success(request, 'Your request has been posted! Others can now apply to help you.')
            return redirect('help_request_detail', pk=help_req.pk)
    else:
        form = HelpRequestForm()
    return render(request, 'work/create_request.html', {'form': form})


@login_required
def help_request_detail(request, pk):
    """View a specific help request with applications."""
    help_req = get_object_or_404(HelpRequest, pk=pk)
    context = {
        'help_request': help_req,
    }

    if request.user == help_req.posted_by:
        context['applications'] = help_req.applications.all().select_related('applicant', 'applicant__profile')
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
    search = request.GET.get('q')

    if category_slug:
        requests_qs = requests_qs.filter(category__slug=category_slug)
    if urgency:
        requests_qs = requests_qs.filter(urgency=urgency)
    if search:
        requests_qs = requests_qs.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    categories = Category.objects.all()
    context = {
        'help_requests': requests_qs,
        'categories': categories,
        'current_category': category_slug,
        'current_urgency': urgency,
        'search_query': search or '',
    }
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
    return render(request, 'work/my_requests.html', {
        'help_requests': requests_qs,
        'status_filter': status_filter,
    })


# ─── Applications ────────────────────────────────────────────────

@login_required
def apply_to_help(request, pk):
    """Any user applies to help with a request (except the poster)."""
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

            messages.success(request, 'Your application has been submitted! The poster will review it.')
            return redirect('help_request_detail', pk=pk)
    else:
        form = ApplicationForm()

    return render(request, 'work/apply.html', {'form': form, 'help_request': help_req})


@login_required
def accept_application(request, pk):
    """Poster accepts an application."""
    application = get_object_or_404(Application, pk=pk)

    if request.user != application.help_request.posted_by:
        messages.error(request, 'You can only manage your own requests.')
        return redirect('dashboard')

    if request.method == 'POST':
        application.status = 'accepted'
        application.save()

        help_req = application.help_request
        help_req.selected_helper = application.applicant
        help_req.status = 'in_progress'
        help_req.save()

        # Reject all other pending applications
        other_apps = help_req.applications.filter(status='pending').exclude(pk=application.pk)
        other_app_users = list(other_apps.values_list('applicant', flat=True))
        other_apps.update(status='rejected')

        # Notify accepted applicant
        Notification.objects.create(
            recipient=application.applicant,
            notification_type='application_accepted',
            title='Application accepted!',
            message=f'Your application to help with "{help_req.title}" has been accepted! You can now chat.',
            link=f'/request/{help_req.pk}/chat/',
        )

        # Notify rejected applicants
        for user_id in other_app_users:
            Notification.objects.create(
                recipient_id=user_id,
                notification_type='application_rejected',
                title='Application update',
                message=f'Someone else was selected for "{help_req.title}". Thanks for offering!',
                link=f'/request/{help_req.pk}/',
            )

        messages.success(request, f'{application.applicant.profile.display_name} has been selected! You can now chat with them.')
        return redirect('chat_room', pk=help_req.pk)

    return redirect('help_request_detail', pk=application.help_request.pk)


@login_required
def reject_application(request, pk):
    """Poster rejects an application."""
    application = get_object_or_404(Application, pk=pk)

    if request.user != application.help_request.posted_by:
        messages.error(request, 'You can only manage your own requests.')
        return redirect('dashboard')

    if request.method == 'POST':
        application.status = 'rejected'
        application.save()

        Notification.objects.create(
            recipient=application.applicant,
            notification_type='application_rejected',
            title='Application update',
            message=f'Your application for "{application.help_request.title}" was not selected.',
            link=f'/request/{application.help_request.pk}/',
        )

        messages.info(request, 'Application has been declined.')
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

        if help_req.selected_helper:
            Notification.objects.create(
                recipient=help_req.selected_helper,
                notification_type='request_resolved',
                title='Request resolved',
                message=f'"{help_req.title}" has been marked as resolved. Thank you for helping!',
                link=f'/request/{help_req.pk}/',
            )

        messages.success(request, 'Your help request has been marked as resolved!')
    return redirect('help_request_detail', pk=pk)


@login_required
def mark_completed(request, pk):
    """Poster marks the work as completed and is redirected to payment page."""
    help_req = get_object_or_404(HelpRequest, pk=pk)

    if request.user != help_req.posted_by:
        messages.error(request, 'Only the request author can mark work as completed.')
        return redirect('help_request_detail', pk=pk)

    if help_req.status != 'in_progress':
        messages.warning(request, 'This request is not currently in progress.')
        return redirect('help_request_detail', pk=pk)

    if not help_req.selected_helper:
        messages.error(request, 'No helper assigned to this request.')
        return redirect('help_request_detail', pk=pk)

    if request.method == 'POST':
        help_req.status = 'completed'
        help_req.save()

        # Notify the helper that work is marked completed
        Notification.objects.create(
            recipient=help_req.selected_helper,
            notification_type='work_completed',
            title='Work marked as completed! 🎉',
            message=f'{request.user.profile.display_name} has marked "{help_req.title}" as completed. Payment is being processed.',
            link=f'/request/{help_req.pk}/',
        )

        messages.success(request, 'Work marked as completed! Now proceed to send payment.')
        return redirect('payment_page', pk=help_req.pk)

    return redirect('help_request_detail', pk=pk)


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
        import re
        numbers = re.findall(r'[\d]+\.?[\d]*', budget_str.replace(',', ''))
        if numbers:
            default_amount = float(numbers[0])

    if not default_amount and help_req.budget:
        import re
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
        amount = Decimal(str(data.get('amount', 0)))
        note = data.get('note', '').strip()

        if amount <= 0:
            return JsonResponse({'error': 'Invalid amount'}, status=400)
    except (json.JSONDecodeError, InvalidOperation, ValueError):
        return JsonResponse({'error': 'Invalid request data'}, status=400)

    # Amount in paise (Razorpay requires smallest currency unit)
    amount_paise = int(amount * 100)

    # Create Razorpay order
    try:
        razorpay_order = razorpay_client.order.create({
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
        razorpay_client.utility.verify_payment_signature({
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

    return render(request, 'work/my_applications.html', {
        'applications': applications,
        'status_filter': status_filter,
    })


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
    if notif.link:
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
