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
from .models import Profile, EmailVerificationToken
from .forms import UserRegisterForm, ProfileUpdateForm


# ─── Helpers ─────────────────────────────────────────────────────

def _send_verification_email(request, user):
    """Create a token and send a verification email to the user."""
    # Delete any existing stale token
    EmailVerificationToken.objects.filter(user=user).delete()
    token_obj = EmailVerificationToken.objects.create(user=user)

    verify_url = request.build_absolute_uri(
        f'/accounts/verify-email/{token_obj.token}/'
    )

    subject = 'Verify your NxtHelp email address'
    html_body = render_to_string('accounts/email_verification.html', {
        'user': user,
        'verify_url': verify_url,
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
    except Exception:
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
    """User registration — sends verification email after signup."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                # Mark as inactive until email is verified
                user.is_active = False
                user.save()
                # Save profile extras
                user.profile.profession = form.cleaned_data.get('profession', '')
                user.profile.save()

                sent = _send_verification_email(request, user)
                if sent:
                    messages.success(
                        request,
                        f'Account created! We\'ve sent a verification link to {user.email}. '
                        'Please check your inbox (and spam folder) to activate your account.'
                    )
                else:
                    # Email failed — still activate account and warn
                    user.is_active = True
                    user.save()
                    login(request, user)
                    messages.warning(
                        request,
                        'Account created, but we couldn\'t send the verification email. '
                        'You can resend it from your profile.'
                    )
                    return redirect('dashboard')

                return redirect('login')
            except IntegrityError:
                form.add_error('username', 'This username is already taken. Please choose a different one.')
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def verify_email(request, token):
    """Verify user's email address via the link sent to their inbox."""
    token_obj = EmailVerificationToken.objects.filter(token=token).first()

    if not token_obj:
        messages.error(request, 'Invalid verification link. Please register again or request a new link.')
        return redirect('register')

    if token_obj.is_expired():
        user = token_obj.user
        token_obj.delete()
        # Resend a fresh link
        _send_verification_email(request, user)
        messages.warning(
            request,
            'Your verification link has expired. We\'ve sent a new one to your email.'
        )
        return redirect('login')

    # Activate the user
    user = token_obj.user
    user.is_active = True
    user.save()
    token_obj.delete()

    login(request, user)
    messages.success(
        request,
        f'🎉 Welcome to NxtHelp, {user.first_name or user.username}! Your email has been verified.'
    )
    return redirect('dashboard')


def resend_verification(request):
    """Resend the verification email for the currently logged‑in (inactive) user."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        from django.contrib.auth.models import User
        user = User.objects.filter(email=email, is_active=False).first()
        if user:
            _send_verification_email(request, user)
        # Always return the same message to prevent email enumeration
        messages.info(request, 'If that email is registered and unverified, a new link has been sent.')
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
                messages.warning(
                    request,
                    'Please verify your email before logging in. '
                    '<a href="#resend-form" style="color:inherit;text-decoration:underline;">Resend link</a>'
                )
                return render(request, 'accounts/login.html', {
                    'form': form,
                    'show_resend': True,
                    'unverified_email': user.email,
                })
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
                return render(request, 'accounts/login.html', {
                    'form': form,
                    'show_resend': True,
                    'unverified_email': user.email,
                })
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
                _send_verification_email(request, request.user)
                logout(request)
                messages.warning(request, 'Your email has been changed. You must verify your new email address to log in again.')
                return redirect('login')

            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile, user=request.user)
    return render(request, 'accounts/edit_profile.html', {'form': form})
