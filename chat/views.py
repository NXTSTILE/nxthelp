from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from .models import ChatMessage
from work.models import HelpRequest, Notification


@login_required
def chat_room(request, pk):
    """Chat between poster and selected helper."""
    help_req = get_object_or_404(HelpRequest, pk=pk)

    # Only poster and selected helper can access
    if request.user not in [help_req.posted_by, help_req.selected_helper]:
        messages.error(request, 'You do not have access to this chat.')
        return redirect('dashboard')

    # Mark messages as read
    ChatMessage.objects.filter(
        help_request=help_req, is_read=False
    ).exclude(sender=request.user).update(is_read=True)

    chat_messages = help_req.chat_messages.all().select_related('sender', 'sender__profile')

    # Determine the other person
    if request.user == help_req.posted_by:
        other_user = help_req.selected_helper
    else:
        other_user = help_req.posted_by

    context = {
        'help_request': help_req,
        'chat_messages': chat_messages,
        'other_user': other_user,
    }
    return render(request, 'chat/chat.html', context)


@login_required
def send_message(request, pk):
    """Send a chat message."""
    help_req = get_object_or_404(HelpRequest, pk=pk)

    if request.user not in [help_req.posted_by, help_req.selected_helper]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if not content:
            if is_ajax:
                return JsonResponse({'error': 'Message cannot be empty.'}, status=400)
            return redirect('chat_room', pk=pk)

        msg = ChatMessage.objects.create(
            help_request=help_req,
            sender=request.user,
            content=content,
        )

        # Notify the other user
        recipient = help_req.selected_helper if request.user == help_req.posted_by else help_req.posted_by
        Notification.objects.create(
            recipient=recipient,
            notification_type='new_message',
            title='New message',
            message=f'{request.user.profile.display_name} sent you a message about "{help_req.title}"',
            link=f'/request/{help_req.pk}/chat/',
        )

        if is_ajax:
            return JsonResponse({
                'id': msg.id,
                'content': msg.content,
                'sender': msg.sender.profile.display_name,
                'sender_initials': msg.sender.profile.initials,
                'sender_color': msg.sender.profile.avatar_color,
                'is_mine': True,
                'time': msg.created_at.strftime('%I:%M %p'),
            })

    return redirect('chat_room', pk=pk)


@login_required
def fetch_messages(request, pk):
    """AJAX endpoint to fetch new messages."""
    help_req = get_object_or_404(HelpRequest, pk=pk)

    if request.user not in [help_req.posted_by, help_req.selected_helper]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    last_id = request.GET.get('last_id', 0)
    new_msgs = help_req.chat_messages.filter(id__gt=last_id).select_related('sender', 'sender__profile')

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
            'time': msg.created_at.strftime('%I:%M %p'),
        })

    return JsonResponse({'messages': data})


@login_required
def my_chats(request):
    """List all active chats for the current user."""
    active_requests = HelpRequest.objects.filter(
        Q(posted_by=request.user) | Q(selected_helper=request.user),
        status='in_progress',
        selected_helper__isnull=False,
    ).select_related(
        'posted_by', 'posted_by__profile',
        'selected_helper', 'selected_helper__profile',
        'category'
    ).order_by('-updated_at')

    chats = []
    for hr in active_requests:
        other_user = hr.selected_helper if request.user == hr.posted_by else hr.posted_by
        last_msg = hr.chat_messages.last()
        unread = hr.chat_messages.filter(is_read=False).exclude(sender=request.user).count()
        chats.append({
            'help_request': hr,
            'other_user': other_user,
            'last_message': last_msg,
            'unread_count': unread,
        })

    return render(request, 'chat/my_chats.html', {'chats': chats})
