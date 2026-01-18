from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Job

class JobSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8
    protocol = 'https'

    def items(self):
        # Returns all jobs ordered by newest first
        return Job.objects.all().order_by('-posted_at')

    def lastmod(self, obj):
        # Tells Google when the page was last updated
        return obj.posted_at

    def location(self, obj):
        # Returns the URL for each specific job
        return reverse('job_detail', args=[obj.pk])