from rest_framework import generics
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Job
from .serializers import JobSerializer


class JobListAPI(generics.ListAPIView):
    queryset = Job.objects.all().order_by('-posted_at')
    serializer_class = JobSerializer

    # 1. Activate the tools
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    # 2. Define what fields can be filtered exactly (e.g., ?company=Google)
    filterset_fields = ['company', 'source', 'location', 'salary_min']

    # 3. Define what fields can be searched textually (e.g., ?search=machine learning)
    search_fields = ['title', 'company', 'location', 'salary_min']