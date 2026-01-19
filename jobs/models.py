from django.db import models

class Job(models.Model):
    title = models.CharField(max_length=500)
    company = models.CharField(max_length=500)
    location = models.CharField(max_length=500, default="Remote")
    url = models.URLField(unique=True, max_length=2048)
    source = models.CharField(max_length=50) # e.g., "PyJobs", "RemoteOK"
    posted_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    seniority = models.CharField(max_length=50, default="Not Specified")
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f"{self.title} at {self.company}"