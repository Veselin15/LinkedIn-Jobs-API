import scrapy
import json
from datetime import datetime
from ..items import JobItem


class TheMuseSpider(scrapy.Spider):
    name = "themuse"
    allowed_domains = ["themuse.com"]

    # API Endpoint for "Software Engineering" jobs
    # We ask for page 0, descending order (newest first)
    start_urls = [
        "https://www.themuse.com/api/public/jobs?category=Software%20Engineering&page=0&descending=true"
    ]

    def parse(self, response):
        data = json.loads(response.text)

        # 1. Loop through the results
        for job in data.get('results', []):
            # Parse Date (Format: "2023-10-25T14:30:00Z")
            try:
                date_str = job.get('publication_date', '').split('T')[0]
                posted_at = datetime.strptime(date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                posted_at = datetime.now().date()

            # Parse Location (It's a list of objects)
            locations = [loc.get('name') for loc in job.get('locations', [])]
            location_str = ", ".join(locations) if locations else "Remote"

            # Create the Job Item
            yield JobItem(
                title=job.get('name'),
                company=job.get('company', {}).get('name'),
                location=location_str,
                # The landing page is the application URL
                url=job.get('refs', {}).get('landing_page'),
                posted_at=posted_at,
                # The 'contents' field has the full HTML description
                description=job.get('contents'),
                source="TheMuse",
                skills=[],  # Our pipeline will extract skills from the description automatically
                salary_min=None,  # The Muse API rarely includes salary data in the public feed
                salary_max=None,
                currency="USD"
            )

        # 2. Pagination (Check if there is a next page)
        # The API returns 'page_count' and current 'page'
        current_page = data.get('page', 0)
        page_count = data.get('page_count', 0)

        if current_page < page_count - 1:
            next_page = current_page + 1
            next_url = f"https://www.themuse.com/api/public/jobs?category=Software%20Engineering&page={next_page}&descending=true"
            yield scrapy.Request(next_url, callback=self.parse)