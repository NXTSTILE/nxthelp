import logging
import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db import IntegrityError
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Profile, OTPToken
from .forms import UserRegisterForm, ProfileUpdateForm

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
        send_mail(
            subject,
            plain_body,
            django_settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_body,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f'Failed to send OTP email to {user.email}: {e}')
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
                if not email_sent:
                    logger.warning(
                        'OTP email could not be sent during registration for user %s (%s). '
                        'Proceeding with registration; user will need to request a new code.',
                        user.username, user.email,
                    )
                    messages.warning(
                        request,
                        'Your account was created but we could not send the verification email. '
                        'Please use the "Resend code" option on the next page to try again.'
                    )

                # Store email in session for the next step
                request.session['verification_email'] = user.email

                return redirect('verify_otp')
            except IntegrityError:
                form.add_error('username', 'This username is already taken. Please choose a different one.')
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

    if request.method == 'POST':
        submitted_otp = request.POST.get('otp', '').strip()
        otp_obj = OTPToken.objects.filter(user=user).first()

        if not otp_obj:
            messages.error(request, 'No OTP generated for this account. Please request a new one.')
            return redirect('verify_otp')

        if otp_obj.is_expired():
            otp_obj.delete()
            email_sent = _send_otp_email(request, user)
            if email_sent:
                messages.warning(
                    request,
                    'Your OTP has expired. We\'ve sent a new one to your email.'
                )
            else:
                logger.warning(
                    'OTP email could not be sent on expiry resend for user %s (%s).',
                    user.username, user.email,
                )
                messages.error(
                    request,
                    'Your OTP has expired but we could not send a new code. '
                    'Please use the "Resend code" option below.'
                )
            return redirect('verify_otp')

        if otp_obj.otp_code == submitted_otp:
            # Activate the user
            user.is_active = True
            user.save()
            otp_obj.delete()
            
            # Clear session
            if 'verification_email' in request.session:
                del request.session['verification_email']

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(
                request,
                f'🎉 Welcome to NxtHelp, {user.first_name or user.username}! Your email has been verified.'
            )
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid verification code. Please try again.')

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
            email_sent = _send_otp_email(request, user)
            if email_sent:
                messages.info(request, 'A new verification code has been sent to your email.')
            else:
                logger.warning(
                    'OTP email could not be sent on manual resend for user %s (%s).',
                    user.username, user.email,
                )
                messages.error(
                    request,
                    'We were unable to send the verification email. '
                    'Please try again in a few minutes or contact support.'
                )
            return redirect('verify_otp')
        # Prevent email enumeration
        messages.info(request, 'If that email is registered and unverified, a new code has been sent to it.')
        return redirect('login')


def login_view(request):
    """User login."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
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
        # Check if the failure is due to an inactive account
        username = request.POST.get('username', '')
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(username=username)
            if not user.is_active:
                request.session['verification_email'] = user.email
                messages.warning(
                    request,
                    'Please verify your email before logging in.'
                )
                return redirect('verify_otp')
        except User.DoesNotExist:
            pass
    else:
        form = AuthenticationForm()
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
                email_sent = _send_otp_email(request, request.user)
                if not email_sent:
                    logger.warning(
                        'OTP email could not be sent after email change for user %s (%s).',
                        request.user.username, request.user.email,
                    )
                request.session['verification_email'] = request.user.email
                logout(request)
                messages.warning(
                    request,
                    'Your email has been changed. You must verify your new email address to log in again.'
                    + ('' if email_sent else
                       ' We could not send the verification email — please use the "Resend code" option.')
                )
                return redirect('verify_otp')

            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile, user=request.user)
    return render(request, 'accounts/edit_profile.html', {'form': form})
