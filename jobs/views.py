from rest_framework import generics
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Job
from .serializers import JobSerializer


class JobListAPI(generics.ListAPIView):
    queryset = Job.objects.all().order_by('-posted_at')
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    # Add salary_min and currency here
    filterset_fields = ['company', 'source', 'location', 'currency', 'salary_min']
    search_fields = ['title', 'company', 'location']