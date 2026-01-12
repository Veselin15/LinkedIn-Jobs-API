from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from rest_framework_api_key.models import APIKey
from jobs.models import Job
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from .forms import EmailRequiredSignupForm

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
    # Use .filter().first() instead of .get()
    api_key = APIKey.objects.filter(name=request.user.email).first()

    if api_key:
        has_key = True
        key_prefix = api_key.prefix
    else:
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
    """Handles User Registration with Email"""
    if request.method == 'POST':
        # Use the new form here
        form = EmailRequiredSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('dashboard')
    else:
        # And here
        form = EmailRequiredSignupForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def job_list(request):
    """
    The Main Job Board Interface.
    Replaces the old React App.jsx.
    """
    query = request.GET.get('q', '')
    location = request.GET.get('loc', '')

    # 1. Filter Jobs
    jobs = Job.objects.all().order_by('-posted_at')

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(skills__icontains=query) |
            Q(company__icontains=query)
        )

    if location:
        jobs = jobs.filter(location__icontains=location)

    # 2. Pagination (20 jobs per page)
    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'location': location
    }
    return render(request, 'core/job_list.html', context)


@login_required
def regenerate_api_key(request):
    """
    Allows a Premium user to revoke their old key and get a new one.
    This is the ONLY time they will see the full key on screen.
    """
    if request.method == 'POST':
        # 1. Check if they are actually premium (have an existing key or paid)
        # For simplicity, we assume if they have a key object, they are allowed.
        try:
            old_key = APIKey.objects.get(name=request.user.email)
            old_key.delete()  # Revoke old access
        except APIKey.DoesNotExist:
            # Optional: Check if they paid via Stripe if no key exists
            # For now, we only let them regenerate if they had one.
            messages.error(request, "No active subscription found.")
            return redirect('dashboard')

        # 2. Create New Key
        api_key, key_string = APIKey.objects.create_key(name=request.user.email)

        # 3. Flash the key to the user (One time only!)
        messages.success(request, f"Your new API Key is: {key_string}")
        messages.warning(request, "Please copy this key now. You will not be able to see it again!")

        return redirect('dashboard')

    return redirect('dashboard')