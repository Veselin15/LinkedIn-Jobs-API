import re
from rest_framework import generics, filters, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters import rest_framework as django_filters # <--- Rename for clarity
from drf_spectacular.utils import extend_schema
from .models import Job
from .serializers import JobSerializer
from .tasks import run_scrapers
from rest_framework.pagination import PageNumberPagination

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

    # Use our new custom filter class
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = JobFilter  # <--- Connect the class here

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        pagination_class = StandardResultsSetPagination

        # Handle Pagination (access 'results') vs No Pagination (access list directly)
        current_results = response.data['results'] if isinstance(response.data, dict) else response.data

        if len(current_results) == 0:
            # Check for ANY valid search parameter
            search_term = request.query_params.get('search')
            skills_term = request.query_params.get('skills')

            # Prefer the explicit search term, otherwise use the skill
            term_to_scrape = search_term or skills_term

            if term_to_scrape:
                print(f"No results for '{term_to_scrape}'. Triggering scraper...")
                run_scrapers.delay(keyword=term_to_scrape, location="Europe")

                return Response({
                    "message": f"No jobs found for '{term_to_scrape}'. We have started a live scrape for you. Check back in 2 minutes!",
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