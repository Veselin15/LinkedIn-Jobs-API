from rest_framework import generics
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend  # <--- FIXED IMPORT

from .models import Job
from .serializers import JobSerializer
from .tasks import run_scrapers
from .throttles import FreeTierThrottle, PremiumTierThrottle
from .filters import JobFilter  # Imports the file you created in Step 1


class JobListAPI(generics.ListAPIView):
    queryset = Job.objects.all().order_by('-posted_at')
    serializer_class = JobSerializer

    # Use the fixed import here
    filter_backends = [DjangoFilterBackend]
    filterset_class = JobFilter

    # 1. Allow both JSON (for API) and HTML (for Browser)
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    # 2. Apply Limits
    throttle_classes = [PremiumTierThrottle, FreeTierThrottle]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # Handle Pagination
        current_results = response.data['results'] if isinstance(response.data, dict) else response.data

        # --- LOGIC: ZERO RESULTS AUTOMATIC SCRAPER ---
        if len(current_results) == 0:
            search_term = request.query_params.get('search')
            # Fix: Check 'skills' filter too since your filter uses that name
            skills_term = request.query_params.get('skills')
            term_to_scrape = search_term or skills_term

            if term_to_scrape:
                lock_key = f"scrape_lock_{term_to_scrape.lower()}_Europe"
                is_already_scraping = cache.get(lock_key)

                if not is_already_scraping:
                    print(f"Triggering NEW scrape for '{term_to_scrape}'...")
                    cache.set(lock_key, "active", timeout=900)
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