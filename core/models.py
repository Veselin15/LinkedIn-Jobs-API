from django.db import models
from django.contrib.auth import get_user_model
from jobs.models import Job

User = get_user_model()

class JobAlert(models.Model):
    """
    Stores email subscriptions for specific search keywords.
    """
    email = models.EmailField()
    keyword = models.CharField(max_length=100)
    location = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(auto_now_add=True) # Tracks when we last emailed them
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.email} -> {self.keyword}"

class SavedJob(models.Model):
    """
    A 'Bookmark' connecting a User to a Job.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'job')  # Prevent saving the same job twice

    def __str__(self):
        return f"{self.user.email} saved {self.job.title}"