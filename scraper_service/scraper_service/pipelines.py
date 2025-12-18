from itemadapter import ItemAdapter
from jobs.models import Job
from asgiref.sync import sync_to_async
from .utils import parse_salary


class ScraperServicePipeline:
    async def process_item(self, item, spider):
        await sync_to_async(self.save_job)(item)
        return item

    def save_job(self, item):
        job, created = Job.objects.update_or_create(
            url=item.get('url'),
            defaults={
                'title': item.get('title'),
                'company': item.get('company'),
                # Fix: Use 'or "Remote"' to handle None values
                'location': item.get('location') or "Remote",
                'source': item.get('source'),
                'posted_at': item.get('posted_at'),
            }
        )
        min_sal, max_sal, curr = parse_salary(item.get('title'))

        job, created = Job.objects.update_or_create(
            url=item.get('url'),
            defaults={
                # ... existing fields ...
                'salary_min': min_sal,
                'salary_max': max_sal,
                'currency': curr,
            }
        )
        return job