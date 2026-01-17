import re
from rest_framework import generics, filters, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema
from rest_framework.pagination import PageNumberPagination
from django.core.cache import cache
# --- NEW SECURITY IMPORTS ---
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .throttles import FreeTierThrottle, PremiumTierThrottle # <--- Import your throttles

from .models import Job
from .serializers import JobSerializer
from .tasks import run_scrapers
from .throttles import FreeTierThrottle, PremiumTierThrottle

# --- 1. Define the Custom Filter (The Input Boxes) ---
class JobFilter(django_filters.FilterSet):
    # specific boxes for searching
    title = django_filters.CharFilter(lookup_expr='icontains')
    company = django_filters.CharFilter(lookup_expr='icontains')
    location = django_filters.CharFilter(lookup_expr='icontains')

    # The "Skills" box you wanted!
    # (We search the text inside the JSON list)
    skills = django_filters.CharFilter(method='filter_skills')
    seniority = django_filters.CharFilter(lookup_expr='icontains')
    # Keep salary filter
    salary_min = django_filters.NumberFilter(field_name='salary_min', lookup_expr='gte')

    class Meta:
        model = Job
        fields = ['title', 'company', 'location', 'skills', 'seniority', 'salary_min', 'source']

    def filter_skills(self, queryset, name, value):
        if not value:
            return queryset

        # We search for the value wrapped in quotes.
        # In the DB, the list looks like: ["Java", "Python"]
        # Searching for "Java" (with quotes) matches "Java" but NOT "JavaScript".
        # iregex makes it case-insensitive but quote-sensitive.
        return queryset.filter(skills__iregex=f'"{re.escape(value)}"')
class JobListAPI(generics.ListAPIView):
    queryset = Job.objects.all().order_by('-posted_at')
    serializer_class = JobSerializer
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = JobFilter

    throttle_classes = [PremiumTierThrottle, FreeTierThrottle]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # Handle Pagination (access 'results') vs No Pagination (access list directly)
        current_results = response.data['results'] if isinstance(response.data, dict) else response.data

        if len(current_results) == 0:
            search_term = request.query_params.get('search')
            skills_term = request.query_params.get('skills')
            term_to_scrape = search_term or skills_term

            if term_to_scrape:
                # --- NEW LOGIC STARTS HERE ---

                # 1. Create a unique "Lock Key" for this search
                # We normalize it to lowercase so "Python" and "python" are treated the same.
                lock_key = f"scrape_lock_{term_to_scrape.lower()}_Europe"

                # 2. Check if the lock exists
                is_already_scraping = cache.get(lock_key)

                if not is_already_scraping:
                    print(f"Triggering NEW scrape for '{term_to_scrape}'...")

                    # 3. Set the Lock!
                    # 'timeout=900' means "Don't scrape this keyword again for 15 minutes"
                    cache.set(lock_key, "active", timeout=900)

                    # 4. Trigger the task
                    run_scrapers.delay(keyword=term_to_scrape, location="Europe")
                else:
                    print(f"Scrape ALREADY in progress for '{term_to_scrape}'. Skipping trigger.")

                # --- NEW LOGIC ENDS HERE ---

                return Response({
                    "message": f"No jobs found for '{term_to_scrape}'. We are scraping the web for you now! Check back in a few minutes.",
                    "results": []
                })

        return response


# --- 3. The Scraper Trigger (No changes here) ---

class ScrapeRequestSerializer(serializers.Serializer):
    keyword = serializers.CharField(default="Python", help_text="Job title or skill")
    location = serializers.CharField(default="Europe", help_text="Region or City")


class ScrapeTriggerAPI(APIView):
    @extend_schema(request=ScrapeRequestSerializer)
    def post(self, request):
        serializer = ScrapeRequestSerializer(data=request.data)
        if serializer.is_valid():
            keyword = serializer.validated_data['keyword']
            location = serializer.validated_data['location']

            run_scrapers.delay(keyword, location)

            return Response({
                "message": "Scraper started successfully",
                "target": f"{keyword} jobs in {location}",
                "note": "Check back in 2-3 minutes for results."
            })
        return Response(serializer.errors, status=400)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size' # User can use ?page_size=50
    max_page_size = 100