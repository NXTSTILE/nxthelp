import logging
import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
from .models import Profile, OTPToken
from .forms import UserRegisterForm, ProfileUpdateForm, EmailOrUsernameAuthForm

logger = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────

def _send_otp_email(request, user):
    """Create a 6-digit OTP and send a verification email to the user."""
    # Delete any existing stale token
    OTPToken.objects.filter(user=user).delete()
    
    otp_code = f"{random.randint(100000, 999999)}"
    OTPToken.objects.create(user=user, otp_code=otp_code)

    subject = 'Your NxtHelp verification code'
    html_body = render_to_string('accounts/email_verification.html', {
        'user': user,
        'otp_code': otp_code,
    })
    plain_body = strip_tags(html_body)

    try:
        import os
        import json
        import urllib.request
        import re

        api_key = os.environ.get('BREVO_API_KEY')
        if not api_key:
            logger.error("BREVO_API_KEY is not set. Cannot send email.")
            return False

        url = "https://api.brevo.com/v3/smtp/email"
        from_name = "NxtHelp"
        from_email = django_settings.DEFAULT_FROM_EMAIL
        
        match = re.match(r"(.*?)\s*<(.*?)>", django_settings.DEFAULT_FROM_EMAIL)
        if match:
            from_name = match.group(1).strip()
            from_email = match.group(2).strip()

        data = {
            "sender": {"name": from_name, "email": from_email},
            "to": [{"email": user.email}],
            "subject": subject,
            "htmlContent": html_body,
            "textContent": plain_body
        }
        
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'))
        req.add_header('api-key', api_key)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Accept', 'application/json')
        
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        logger.error(f'Failed to send OTP email to {user.email}: {e}')
        # Log the detailed HTTP response if available
        if hasattr(e, "read"):
            logger.error(e.read().decode("utf-8"))
        return False


# ─── Authentication ─────────────────────────────────────────────

def landing_page(request):
    """Public landing page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    from work.models import HelpRequest
    stats = {
        'users': Profile.objects.count(),
        'requests_posted': HelpRequest.objects.count(),
        'requests_resolved': HelpRequest.objects.filter(status='resolved').count(),
    }
    return render(request, 'accounts/landing.html', {'stats': stats})


def register_view(request):
    """User registration — triggers OTP email verification."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                # Ensure account is inactive until email is verified
                user.is_active = False
                user.save()
                
                # Save profile extras
                user.profile.profession = form.cleaned_data.get('profession', '')
                user.profile.save()

                # Send OTP email
                email_sent = _send_otp_email(request, user)
                
                # Store email in session for the next step
                request.session['verification_email'] = user.email

                if not email_sent:
                    messages.warning(request, "Your account was created, but we failed to send the OTP email. Please try resending the OTP or contact support.")
                    # Log them out or send them somewhere safe
                    return redirect('login')

                return redirect('verify_otp')
            except IntegrityError:
                form.add_error(None, 'An account with this username or email already exists.')
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def verify_otp_view(request):
    """Verify user's email address via the 6-digit OTP sent to their inbox."""
    email = request.session.get('verification_email')
    
    if not email:
        return redirect('register')

    from django.contrib.auth.models import User
    user = User.objects.filter(email=email).first()

    if not user or user.is_active:
        return redirect('login')

    attempts_key = f'otp_attempts_{user.pk}'

    if request.method == 'POST':
        attempts = request.session.get(attempts_key, 0)
        if attempts >= 5:
            messages.error(request, 'Too many failed attempts. Please request a new code.')
            return redirect('verify_otp')

        submitted_otp = request.POST.get('otp', '').strip()
        otp_obj = OTPToken.objects.filter(user=user).first()

        if not otp_obj:
            messages.error(request, 'No OTP generated for this account. Please request a new one.')
            return redirect('verify_otp')

        if otp_obj.is_expired():
            otp_obj.delete()
            request.session.pop(attempts_key, None)
            _send_otp_email(request, user)
            messages.warning(
                request,
                'Your OTP has expired. We\'ve sent a new one to your email.'
            )
            return redirect('verify_otp')

        if otp_obj.otp_code == submitted_otp:
            # Activate the user
            user.is_active = True
            user.save()
            otp_obj.delete()
            
            # Clear session
            request.session.pop('verification_email', None)
            request.session.pop(attempts_key, None)

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(
                request,
                f'🎉 Welcome to NxtHelp, {user.first_name or user.username}! Your email has been verified.'
            )
            return redirect('dashboard')
        else:
            request.session[attempts_key] = attempts + 1
            remaining = 5 - (attempts + 1)
            if remaining > 0:
                messages.error(request, f'Invalid verification code. {remaining} attempt{"s" if remaining != 1 else ""} remaining.')
            else:
                messages.error(request, 'Invalid verification code. Too many failed attempts. Please request a new code.')

    return render(request, 'accounts/verify_otp.html', {'email': email})


def resend_verification(request):
    """Resend the verification OTP for the currently registered or logged‑in (inactive) user."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            email = request.session.get('verification_email')
            
        from django.contrib.auth.models import User
        user = User.objects.filter(email=email, is_active=False).first()
        if user:
            otp_obj = OTPToken.objects.filter(user=user).first()
            if otp_obj and timezone.now() - otp_obj.created_at < timedelta(seconds=60):
                messages.warning(request, 'Please wait a minute before requesting a new code.')
                return redirect('verify_otp')
            _send_otp_email(request, user)
            # Reset attempt counter on successful resend
            request.session.pop(f'otp_attempts_{user.pk}', None)
            messages.info(request, 'A new verification code has been sent to your email.')
            return redirect('verify_otp')
        # Prevent email enumeration
        messages.info(request, 'If that email is registered and unverified, a new code has been sent to it.')
        return redirect('login')


def login_view(request):
    """User login."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = EmailOrUsernameAuthForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_active:
                request.session['verification_email'] = user.email
                messages.warning(
                    request,
                    'Please verify your email before logging in.'
                )
                return redirect('verify_otp')
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.GET.get('next', 'dashboard')
            from django.utils.http import url_has_allowed_host_and_scheme
            if not url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                next_url = 'dashboard'
            return redirect(next_url)
    else:
        form = EmailOrUsernameAuthForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """User logout — POST only to prevent CSRF logout attacks."""
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
    return redirect('landing')


# ─── Profile ─────────────────────────────────────────────────────

@login_required
def profile_view(request, username=None):
    """View a user's profile."""
    if username:
        from django.contrib.auth.models import User
        user = get_object_or_404(User, username=username)
    else:
        user = request.user

    from work.models import HelpRequest, Application
    profile = user.profile
    context = {
        'profile_user': user,
        'profile': profile,
        'posted_requests': HelpRequest.objects.filter(posted_by=user).select_related('category')[:5],
        'helped_requests': Application.objects.filter(
            applicant=user, status='accepted'
        ).select_related('help_request')[:5],
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def edit_profile(request):
    """Edit own profile."""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user.profile, user=request.user)
        if form.is_valid():
            old_email = request.user.email
            new_email = form.cleaned_data.get('email')
            email_changed = old_email != new_email

            form.save()

            if email_changed:
                request.user.is_active = False
                request.user.save()
                _send_otp_email(request, request.user)
                request.session['verification_email'] = request.user.email
                logout(request)
                messages.warning(request, 'Your email has been changed. You must verify your new email address to log in again.')
                return redirect('verify_otp')

            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile, user=request.user)
    return render(request, 'accounts/edit_profile.html', {'form': form})
