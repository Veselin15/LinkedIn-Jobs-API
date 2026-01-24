from rest_framework import generics, serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .models import Job
from .serializers import JobSerializer
from .tasks import run_scrapers
# --- UPDATED IMPORTS HERE ---
from .throttles import FreeTierThrottle, ProTierThrottle, BusinessTierThrottle
from .filters import JobFilter


# --- 1. The Job List API ---
class JobListAPI(generics.ListAPIView):
    serializer_class = JobSerializer
    # Filter Backend settings
    filter_backends = [DjangoFilterBackend]
    filterset_class = JobFilter

    # Allow both JSON (for API) and HTML (for Browser)
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    # --- UPDATED THROTTLES HERE ---
    # We list all of them; the code inside them determines which one applies
    throttle_classes = [BusinessTierThrottle, ProTierThrottle, FreeTierThrottle]

    def get_queryset(self):
        """
        Uses Postgres Full-Text Search if the 'search' parameter is present.
        Otherwise, returns the standard list.
        """
        # Start with all jobs
        queryset = Job.objects.all().order_by('-posted_at')

        # Get the 'search' parameter from the URL (e.g., ?search=python developer)
        search_term = self.request.query_params.get('search', None)

        if search_term:
            # 1. Define where to search (Vector)
            # Search in the title (weight A - most important) and company/skills (B)
            vector = SearchVector('title', weight='A') + \
                     SearchVector('company', weight='B') + \
                     SearchVector('skills', weight='B')

            # 2. Process the query (Query)
            # SearchQuery automatically removes stop words (the, a, in) and performs stemming
            query = SearchQuery(search_term)

            # 3. Filter and sort by relevance (Rank)
            queryset = queryset.annotate(
                rank=SearchRank(vector, query)
            ).filter(rank__gte=0.1).order_by('-rank', '-posted_at')

        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # Handle Pagination
        current_results = response.data['results'] if isinstance(response.data, dict) else response.data

        # --- LOGIC: ZERO RESULTS AUTOMATIC SCRAPER ---
        if len(current_results) == 0:
            search_term = request.query_params.get('search')
            # Check 'skills' filter too since your filter uses that name
            skills_term = request.query_params.get('skills')
            term_to_scrape = search_term or skills_term

            if term_to_scrape:
                # Create a lock key to prevent "Thundering Herd"
                lock_key = f"scrape_lock_{term_to_scrape.lower()}_Europe"
                is_already_scraping = cache.get(lock_key)

                if not is_already_scraping:
                    print(f"Triggering NEW scrape for '{term_to_scrape}'...")
                    cache.set(lock_key, "active", timeout=900)  # Lock for 15 mins
                    run_scrapers.delay(keyword=term_to_scrape, location="Europe")
                else:
                    print(f"Scrape ALREADY in progress for '{term_to_scrape}'. Skipping.")

        # --- LOGIC: CONTENT NEGOTIATION ---
        # If HTMX/Browser, return HTML
        if request.headers.get('HX-Request') == 'true':
            return Response(
                {'page_obj': current_results},
                template_name='core/partials/job_results.html'
            )

        return response


# --- 2. The Scraper Trigger (Manual Endpoint) ---

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
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)