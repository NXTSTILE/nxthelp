from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from collections import OrderedDict
import bleach
from .models import ChatMessage
from work.models import HelpRequest, Application, Notification


@login_required
def chat_room(request, pk, app_pk):
    """Chat thread between poster and a specific applicant."""
    help_req = get_object_or_404(HelpRequest, pk=pk)
    application = get_object_or_404(Application, pk=app_pk, help_request=help_req)

    # Only poster and the applicant can access this thread
    if request.user not in [help_req.posted_by, application.applicant]:
        messages.error(request, 'You do not have access to this chat.')
        return redirect('dashboard')

    # Mark messages as read
    ChatMessage.objects.filter(
        application=application, is_read=False
    ).exclude(sender=request.user).update(is_read=True)

    chat_messages = ChatMessage.objects.filter(
        application=application
    ).select_related('sender', 'sender__profile')

    # Determine the other person
    if request.user == help_req.posted_by:
        other_user = application.applicant
    else:
        other_user = help_req.posted_by

    context = {
        'help_request': help_req,
        'application': application,
        'chat_messages': chat_messages,
        'other_user': other_user,
    }
    return render(request, 'chat/chat.html', context)


@login_required
def send_message(request, pk, app_pk):
    """Send a chat message in a specific thread."""
    help_req = get_object_or_404(HelpRequest, pk=pk)
    application = get_object_or_404(Application, pk=app_pk, help_request=help_req)

    if request.user not in [help_req.posted_by, application.applicant]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        raw_content = request.POST.get('content', '').strip()
        # Strip all HTML tags — chat is plain text only
        content = bleach.clean(raw_content, tags=[], strip=True)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if not content:
            if is_ajax:
                return JsonResponse({'error': 'Message cannot be empty.'}, status=400)
            return redirect('chat_room', pk=pk, app_pk=app_pk)

        msg = ChatMessage.objects.create(
            help_request=help_req,
            application=application,
            sender=request.user,
            content=content,
        )

        # Notify the other user ONLY if they don't already have an unread message notification for this chat
        recipient = application.applicant if request.user == help_req.posted_by else help_req.posted_by
        link = f'/request/{help_req.pk}/chat/{application.pk}/'
        
        has_unread_notif = Notification.objects.filter(
            recipient=recipient,
            notification_type='new_message',
            link=link,
            is_read=False
        ).exists()

        if not has_unread_notif:
            Notification.objects.create(
                recipient=recipient,
                notification_type='new_message',
                title='New message',
                message=f'{request.user.profile.display_name} sent a message about "{help_req.title}"',
                link=link,
            )

        if is_ajax:
            return JsonResponse({
                'id': msg.id,
                'content': msg.content,
                'sender': msg.sender.profile.display_name,
                'sender_initials': msg.sender.profile.initials,
                'sender_color': msg.sender.profile.avatar_color,
                'is_mine': True,
                'time': timezone.localtime(msg.created_at).strftime('%I:%M %p'),
            })

    return redirect('chat_room', pk=pk, app_pk=app_pk)


@login_required
def fetch_messages(request, pk, app_pk):
    """AJAX endpoint to fetch new messages for a thread."""
    help_req = get_object_or_404(HelpRequest, pk=pk)
    application = get_object_or_404(Application, pk=app_pk, help_request=help_req)

    if request.user not in [help_req.posted_by, application.applicant]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    last_id = request.GET.get('last_id', 0)
    new_msgs = ChatMessage.objects.filter(
        application=application, id__gt=last_id
    ).select_related('sender', 'sender__profile')

    # Mark incoming as read
    new_msgs.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    data = []
    for msg in new_msgs:
        data.append({
            'id': msg.id,
            'content': msg.content,
            'sender': msg.sender.profile.display_name,
            'sender_initials': msg.sender.profile.initials,
            'sender_color': msg.sender.profile.avatar_color,
            'is_mine': msg.sender == request.user,
            'time': timezone.localtime(msg.created_at).strftime('%I:%M %p'),
        })

    return JsonResponse({'messages': data})


@login_required
def my_chats(request):
    """List all chats grouped by request."""
    user = request.user

    # All applications with chat messages where user is involved
    applications_with_chats = Application.objects.filter(
        Q(help_request__posted_by=user) | Q(applicant=user),
        chat_messages__isnull=False
    ).distinct().select_related(
        'help_request', 'help_request__category',
        'help_request__posted_by', 'help_request__posted_by__profile',
        'applicant', 'applicant__profile'
    )

    # Group by help_request
    grouped = OrderedDict()
    for app in applications_with_chats:
        hr = app.help_request
        if hr.pk not in grouped:
            grouped[hr.pk] = {
                'help_request': hr,
                'is_poster': hr.posted_by == user,
                'threads': [],
            }

        other_user = app.applicant if hr.posted_by == user else hr.posted_by
        last_msg = app.chat_messages.order_by('-created_at').first()
        unread = app.chat_messages.filter(is_read=False).exclude(sender=user).count()

        grouped[hr.pk]['threads'].append({
            'application': app,
            'other_user': other_user,
            'last_message': last_msg,
            'unread_count': unread,
        })

    context = {
        'grouped_chats': list(grouped.values()),
    }
    return render(request, 'chat/my_chats.html', context)
