from django.db import models
from django.contrib.auth import get_user_model
from jobs.models import Job

User = get_user_model()
# Create your models here.
class SavedJob(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'job')  # Prevent saving the same job twice

    def __str__(self):
        return f"{self.user.email} saved {self.job.title}"