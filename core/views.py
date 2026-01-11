from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from rest_framework_api_key.models import APIKey
from jobs.models import Job
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
def index(request):
    """The Landing Page (Public)"""
    # Show stats to impress visitors
    job_count = Job.objects.count()
    return render(request, 'core/index.html', {'job_count': job_count})

@login_required
def dashboard(request):
    """
    The Money Page.
    Users manage their subscription and keys here.
    """
    # 1. Check for API Key
    # We name the key after the user's email to link them.
    try:
        api_key = APIKey.objects.get(name=request.user.email)
        has_key = True
        key_prefix = api_key.prefix
    except APIKey.DoesNotExist:
        has_key = False
        key_prefix = None

    # 2. Logic for "Premium" status
    is_premium = has_key
    daily_limit = 1000 if is_premium else 10

    context = {
        'has_key': has_key,
        'key_prefix': key_prefix,
        'limit': daily_limit,
        'is_premium': is_premium,
        'api_url': 'http://localhost:8000/api/jobs/' # Or your real domain
    }
    return render(request, 'core/dashboard.html', context)


def register(request):
    """Handles User Registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in immediately after signing up
            auth_login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})