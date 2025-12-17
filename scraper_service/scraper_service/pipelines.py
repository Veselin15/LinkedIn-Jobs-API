from itemadapter import ItemAdapter
from jobs.models import Job


class ScraperServicePipeline:
    def process_item(self, item, spider):
        # We use update_or_create to avoid duplicates.
        # If a job with this URL already exists, it updates it.
        # If not, it creates a new one.

        job, created = Job.objects.update_or_create(
            url=item.get('url'),
            defaults={
                'title': item.get('title'),
                'company': item.get('company'),
                'location': item.get('location'),
                'source': item.get('source'),
                'posted_at': item.get('posted_at'),
            }
        )

        if created:
            spider.logger.info(f"New Job saved: {job.title}")
        else:
            spider.logger.info(f"Job updated: {job.title}")

        return item