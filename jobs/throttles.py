from rest_framework.throttling import SimpleRateThrottle
from rest_framework_api_key.models import APIKey
from django.contrib.auth import get_user_model
from payments.models import UserSubscription

User = get_user_model()


class FreeTierThrottle(SimpleRateThrottle):
    """
    Limits:
    1. Scripts/Postman -> 20/day (Upgraded from 10)
    2. Web Browsers -> Unlimited (Bypass for HTMX/HTML)
    """
    scope = 'free_tier'
    rate = '20/day'  # <--- UPGRADED LIMIT

    def allow_request(self, request, view):
        # --- BYPASS FOR BROWSERS ---
        # If the user is asking for HTML (Web Page) or using HTMX, let them in!
        if request.accepts('text/html') or request.headers.get('HX-Request') == 'true':
            return True  # Skip throttling completely

        # If the user is an Admin, also skip
        if request.user.is_staff:
            return True

        # Otherwise, run the standard check
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        # 1. Check for ANY valid API Key
        # If they have a key, we return None here so this throttle is skipped.
        # The Pro/Business throttles will pick them up instead.
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header and auth_header.startswith("Api-Key "):
            try:
                key_value = auth_header.split()[1]
                if APIKey.objects.get_from_key(key_value):
                    return None
            except:
                pass

        # 2. No Key? Throttle by IP Address (The Free User)
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class ProTierThrottle(SimpleRateThrottle):
    """
    Limits: 1,000/day
    Applies ONLY if the user's Subscription is 'pro'
    """
    scope = 'pro_tier'
    rate = '1000/day'

    def get_cache_key(self, request, view):
        return self.check_plan_limit(request, 'pro')

    def check_plan_limit(self, request, required_plan):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header or not auth_header.startswith("Api-Key "):
            return None  # Not an API request, ignore.

        try:
            key_value = auth_header.split()[1]
            api_key = APIKey.objects.get_from_key(key_value)

            if api_key:
                # Find the user by email (stored in api_key.name)
                email = api_key.name
                user = User.objects.filter(email=email).first()

                if user:
                    # Check their subscription plan
                    sub = getattr(user, 'subscription', None)
                    # If they match the plan, apply this throttle
                    if sub and sub.plan_type == required_plan:
                        return self.cache_format % {
                            'scope': self.scope,
                            'ident': api_key.id
                        }
        except:
            pass
        return None


class BusinessTierThrottle(SimpleRateThrottle):
    """
    Limits: 10,000/day
    Applies ONLY if the user's Subscription is 'business'
    """
    scope = 'business_tier'
    rate = '10000/day'

    def get_cache_key(self, request, view):
        # Reuse logic but look for 'business' plan
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header or not auth_header.startswith("Api-Key "):
            return None

        try:
            key_value = auth_header.split()[1]
            api_key = APIKey.objects.get_from_key(key_value)

            if api_key:
                email = api_key.name
                user = User.objects.filter(email=email).first()

                if user:
                    sub = getattr(user, 'subscription', None)
                    if sub and sub.plan_type == 'business':
                        return self.cache_format % {
                            'scope': self.scope,
                            'ident': api_key.id
                        }
        except:
            pass
        return None