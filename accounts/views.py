from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db import IntegrityError
from .models import Profile
from .forms import UserRegisterForm, ProfileUpdateForm


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
    """User registration — no role selection."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, f'Welcome to NxtHelp, {user.first_name}! Your account has been created.')
                return redirect('dashboard')
            except IntegrityError:
                form.add_error('username', 'This username is already taken. Please choose a different one.')
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """User login."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """User logout."""
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
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile, user=request.user)
    return render(request, 'accounts/edit_profile.html', {'form': form})
