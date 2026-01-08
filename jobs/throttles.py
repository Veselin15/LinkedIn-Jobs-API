from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle
from rest_framework_api_key.models import APIKey


class FreeTierThrottle(AnonRateThrottle):
    """
    Limits unauthenticated users (by IP) to 100/day.
    If a valid API Key is found, this rule is SKIPPED.
    """
    rate = '100/day'

    def allow_request(self, request, view):
        # 1. Check for API Key header
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header and auth_header.startswith("Api-Key "):
            try:
                # 2. If Key is Valid, skip this limit (return True)
                key_value = auth_header.split()[1]
                if APIKey.objects.get_from_key(key_value):
                    return True
            except:
                pass  # Malformed key? Fall back to IP limit.

        # 3. No key found? Apply the IP limit.
        return super().allow_request(request, view)


class PremiumTierThrottle(SimpleRateThrottle):
    """
    Limits API Key users to 1000/day.
    If no key is found, this rule is IGNORED.
    """
    scope = 'api_key'
    rate = '1000/day'

    def get_cache_key(self, request, view):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if not auth_header or not auth_header.startswith("Api-Key "):
            return None  # Not a premium request, ignore.

        try:
            # Throttle based on the unique API Key ID
            key_value = auth_header.split()[1]
            api_key = APIKey.objects.get_from_key(key_value)
            return self.cache_format % {
                'scope': self.scope,
                'ident': api_key.id
            }
        except:
            return None  # Invalid key, ignore.