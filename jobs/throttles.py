from rest_framework.throttling import SimpleRateThrottle
from rest_framework_api_key.models import APIKey


class FreeTierThrottle(SimpleRateThrottle):
    """
    Limits:
    1. Scripts/Postman -> 10/day (Strict)
    2. Web Browsers -> Unlimited (Bypass)
    """
    scope = 'free_tier'
    rate = '10/day'

    def allow_request(self, request, view):
        # --- NEW: BYPASS FOR BROWSERS ---
        # If the user is asking for HTML (Web Page) or using HTMX, let them in!
        if request.accepts('text/html') or request.headers.get('HX-Request') == 'true':
            return True  # Skip throttling completely

        # If the user is an Admin, also skip
        if request.user.is_staff:
            return True

        # Otherwise, run the standard check (Limits API scripts)
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        # 1. Check for API Key Header (Premium Bypass)
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header and auth_header.startswith("Api-Key "):
            try:
                key_value = auth_header.split()[1]
                if APIKey.objects.get_from_key(key_value):
                    return None  # Valid Key? Skip throttle.
            except:
                pass

        # 2. No Key? Throttle by IP Address
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


# PremiumThrottle remains the same...
class PremiumTierThrottle(SimpleRateThrottle):
    scope = 'premium_tier'
    rate = '1000/day'

    def get_cache_key(self, request, view):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header or not auth_header.startswith("Api-Key "):
            return None  # Not a premium request, ignore.

        try:
            key_value = auth_header.split()[1]
            api_key = APIKey.objects.get_from_key(key_value)
            if api_key:
                return self.cache_format % {
                    'scope': self.scope,
                    'ident': api_key.id
                }
        except:
            pass
        return None