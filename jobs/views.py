from rest_framework import generics, filters, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema  # <--- New Import for Documentation
from .models import Job
from .serializers import JobSerializer
from .tasks import run_scrapers


class JobListAPI(generics.ListAPIView):
    queryset = Job.objects.all().order_by('-posted_at')
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['company', 'source', 'location', 'currency', 'salary_min']
    search_fields = ['title', 'company', 'location', 'skills']


# --- New: Define what the User should send ---
class ScrapeRequestSerializer(serializers.Serializer):
    keyword = serializers.CharField(default="Python", help_text="Job title or skill (e.g. 'Java')")
    location = serializers.CharField(default="Europe", help_text="Region or City (e.g. 'Berlin')")


class ScrapeTriggerAPI(APIView):

    # This decorator tells Swagger: "This endpoint uses this Serializer for inputs"
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