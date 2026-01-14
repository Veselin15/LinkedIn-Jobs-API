from rest_framework_api_key.models import APIKey


def global_premium_status(request):
    """
    Makes 'is_premium' available in ALL templates (Navbar, Modals, etc).
    """
    if request.user.is_authenticated:
        # Check if they have an API Key (which means they are Premium)
        is_premium = APIKey.objects.filter(name=request.user.email).exists()
        return {'is_premium': is_premium}

    # Anonymous users are never premium
    return {'is_premium': False}