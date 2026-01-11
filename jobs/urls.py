from django.urls import path
from .views import JobListAPI, ScrapeTriggerAPI

urlpatterns = [
    # Map 'api/jobs/'
    path('jobs/', JobListAPI.as_view(), name='job-list'),

    # Map 'api/scrape/'
    path('scrape/', ScrapeTriggerAPI.as_view(), name='job-scrape'),
]