from itemadapter import ItemAdapter
from jobs.models import Job
from asgiref.sync import sync_to_async
from .utils import parse_salary, extract_skills, extract_seniority


class ScraperServicePipeline:
    async def process_item(self, item, spider):
        # Run the synchronous Django ORM code in a separate thread
        await sync_to_async(self.save_job)(item)
        return item

    def save_job(self, item):
        # 1. Safe Extraction with Defaults
        # We ensure no field is None (except nullable ones) to prevent crashes
        url = item.get('url')
        if not url:
            return None  # Skip items without a URL

        title = item.get('title') or "Unknown Title"
        company = item.get('company') or "Unknown Company"
        description = item.get('description') or ""
        location = item.get('location') or "Remote"
        source = item.get('source') or "Unknown"

        # 2. Analysis (Skills, Salary, Seniority)
        # We analyze the FULL text before truncating it
        text_to_scan = f"{title} {company} {description}"

        min_sal, max_sal, curr = parse_salary(text_to_scan)
        skills_found = extract_skills(text_to_scan)
        seniority_level = extract_seniority(title, description)

        # 3. Database Save with Safety Truncation
        # We slice strings [:Limit] to match your Database Model limits.
        # URL -> 2000 chars
        # Title/Company/Location -> 500 chars
        # Source/Seniority -> 50 chars

        job, created = Job.objects.update_or_create(
            url=url[:2000],  # Critical fix for long Glassdoor URLs
            defaults={
                'title': title[:500],
                'company': company[:500],
                'location': location[:500],
                'source': source[:50],
                'posted_at': item.get('posted_at'),
                'description': description,  # TextField usually handles unlimited text
                'skills': skills_found,
                'seniority': seniority_level[:50],
                'salary_min': min_sal,
                'salary_max': max_sal,
                'currency': curr,
            }
        )
        return job