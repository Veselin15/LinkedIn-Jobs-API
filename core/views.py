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


def job_list(request):
    """
    Public Job Board with Metered Access.
    - Logged In: Unlimited Views
    - Anonymous: 5 Pages Limit -> Then Upsell
    """

    # --- METERED PAYWALL LOGIC ---
    if not request.user.is_authenticated:
        # Get current view count from session (default is 0)
        anon_views = request.session.get('anon_job_views', 0)
        limit = 7

        if anon_views >= limit:
            # LIMIT REACHED: Show Upsell

            # If they clicked "Next" (HTMX), replace the job list with the signup card
            if request.headers.get('HX-Request'):
                return render(request, 'core/partials/upsell.html')

            # If they refreshed the page, show the upsell on the main page
            return render(request, 'core/job_list.html', {
                'limit_reached': True,
                'page_obj': None  # No jobs for you!
            })

        # Increment count
        request.session['anon_job_views'] = anon_views + 1

    # --- STANDARD JOB FETCHING (Keep your existing code) ---
    query = request.GET.get('q', '')
    location = request.GET.get('loc', '')

    jobs = Job.objects.all().order_by('-posted_at')

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) |
            Q(skills__icontains=query) |
            Q(company__icontains=query)
        )

    if location:
        jobs = jobs.filter(location__icontains=location)

    paginator = Paginator(jobs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'location': location
    }

    if request.headers.get('HX-Request'):
        return render(request, 'core/partials/job_results.html', context)

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


@login_required
def developer_guide(request):
    """
    The 'Developer Portal' page.
    Shows code examples personalized with the user's API Key.
    """
    # 1. Get the API Key (if it exists) to pre-fill the code snippets
    api_key = APIKey.objects.filter(name=request.user.email).first()

    context = {
        'has_key': bool(api_key),
        'key_prefix': api_key.prefix if api_key else "YOUR_API_KEY",
        'api_url': 'http://localhost:8000/api/jobs/',  # Change to real domain in Prod
    }
    return render(request, 'core/developer_guide.html', context)