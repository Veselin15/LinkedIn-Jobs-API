from rest_framework.throttling import SimpleRateThrottle
from rest_framework_api_key.models import APIKey


class FreeTierThrottle(SimpleRateThrottle):
    """
    Limits ANY request (authenticated or not) to 10/day by IP,
    UNLESS a valid API Key is provided.
    """
    scope = 'free_tier'
    rate = '10/day'

    def get_cache_key(self, request, view):
        # 1. Check for API Key Header
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header and auth_header.startswith("Api-Key "):
            try:
                key_value = auth_header.split()[1]
                if APIKey.objects.get_from_key(key_value):
                    return None  # Valid Key? Skip this throttle completely.
            except:
                pass

                # 2. No Key? Throttle by IP Address (Even if logged in!)
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class PremiumTierThrottle(SimpleRateThrottle):
    """
    Limits API Key users to 1000/day.
    If no key is found, this rule is IGNORED.
    """
    scope = 'premium_tier'
    rate = '1000/day'

    def get_cache_key(self, request, view):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header or not auth_header.startswith("Api-Key "):
            return None  # Not a premium request, ignore.

        try:
            # Throttle based on the unique API Key ID
            key_value = auth_header.split()[1]
            api_key = APIKey.objects.get_from_key(key_value)

            # If key is valid, throttle this specific key
            if api_key:
                return self.cache_format % {
                    'scope': self.scope,
                    'ident': api_key.id
                }
        except:
            pass

        return None  # Invalid key, ignore.