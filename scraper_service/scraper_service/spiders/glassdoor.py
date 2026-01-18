import scrapy
import json
import re
import random
from datetime import datetime
from ..items import JobItem
from ..utils import parse_relative_date  # Uses your new utility


class GlassdoorSpider(scrapy.Spider):
    name = "glassdoor"
    allowed_domains = ["glassdoor.com"]

    # Map common locations to Glassdoor 'locId' (Country IDs)
    # 1=US, 2=UK, 3=Canada, 4=India, 5=Australia, 96=Germany, etc.
    LOCATION_MAP = {
        'US': '1', 'USA': '1', 'United States': '1',
        'UK': '2', 'United Kingdom': '2',
        'CA': '3', 'Canada': '3',
        'IN': '4', 'India': '4',
        'AU': '5', 'Australia': '5',
        'DE': '96', 'Germany': '96',
        'Remote': '0'  # Generic fallback
    }

    def __init__(self, keyword='Software Engineer', location='US', *args, **kwargs):
        super(GlassdoorSpider, self).__init__(*args, **kwargs)
        self.keyword = keyword
        self.location_name = location

        # Determine Location ID
        loc_id = self.LOCATION_MAP.get(location, '1')  # Default to US

        # Build URL dynamically
        # locT=N means "National" (Country level), locT=C means "City"
        self.start_urls = [
            f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={keyword}&locT=N&locId={loc_id}"
        ]

    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        },
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',

        # Resilience Settings
        'DOWNLOAD_DELAY': 5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,  # Random wait between 0.5 * DELAY and 1.5 * DELAY
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 2,
        'RETRY_HTTP_CODES': [403, 429, 500, 503],  # Retry on blocks/bans
        'COOKIES_ENABLED': False
    }

    def parse(self, response):
        # 1. Parse Job Cards
        job_listings = response.css('li[data-test="jobListing"]')

        if not job_listings:
            self.logger.warning(f"⚠️ No jobs found or blocked by Glassdoor (Status: {response.status})")

        for job in job_listings:
            url = job.css('a[data-test="job-link"]::attr(href)').get()

            # Extract basic "posted date" text from the card (e.g. "3d", "24h")
            # We pass this to detail page as a fallback if JSON-LD is missing
            date_text = job.css('[data-test="job-age"]::text').get()

            if url:
                url = response.urljoin(url)
                yield scrapy.Request(
                    url,
                    callback=self.parse_detail,
                    meta={
                        'listing_url': url,
                        'card_date_text': date_text  # Pass this forward
                    }
                )

        # 2. Pagination
        next_page = response.css('a[data-test="pagination-next"]::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_detail(self, response):
        job_item = JobItem()
        job_item['url'] = response.meta['listing_url']
        job_item['source'] = "Glassdoor"

        # --- STRATEGY A: JSON-LD (Primary) ---
        json_success = False
        json_ld_script = response.xpath('//script[@type="application/ld+json"]/text()').get()

        if json_ld_script:
            try:
                data = json.loads(json_ld_script)
                if isinstance(data, list):
                    data = next((item for item in data if item.get('@type') == 'JobPosting'), {})

                if data:
                    job_item['title'] = data.get('title')
                    job_item['description'] = data.get('description')

                    # Company
                    org = data.get('hiringOrganization', {})
                    if isinstance(org, dict):
                        job_item['company'] = org.get('name')
                    else:
                        job_item['company'] = org

                    # Location
                    loc = data.get('jobLocation', {})
                    if isinstance(loc, dict):
                        address = loc.get('address', {})
                        if isinstance(address, dict):
                            city = address.get('addressLocality', '')
                            region = address.get('addressRegion', '')
                            job_item['location'] = f"{city}, {region}".strip(', ')

                    # Date
                    date_str = data.get('datePosted')
                    if date_str:
                        try:
                            job_item['posted_at'] = datetime.strptime(date_str.split('T')[0], "%Y-%m-%d").date()
                        except ValueError:
                            pass  # Fallback to method B later

                    # Salary
                    salary = data.get('baseSalary', {})
                    if isinstance(salary, dict):
                        value = salary.get('value', {})
                        job_item['salary_min'] = value.get('minValue')
                        job_item['salary_max'] = value.get('maxValue')
                        job_item['currency'] = salary.get('currency', 'USD')

                    json_success = True
            except json.JSONDecodeError:
                pass

        # --- STRATEGY B: HTML Fallback (Secondary) ---
        # If JSON failed or fields are missing, try CSS selectors

        if not job_item.get('title'):
            # Try multiple common title classes
            job_item['title'] = (
                    response.css('div.css-17x2pwl::text').get() or
                    response.css('h1::text').get() or
                    response.css('[data-test="job-title"]::text').get()
            )

        if not job_item.get('company'):
            # Remove "4.5 ★" ratings from company name
            raw_company = (
                    response.css('div[data-test="employer-name"]::text').get() or
                    response.css('div.css-16nw49e::text').get()
            )
            if raw_company:
                job_item['company'] = raw_company.split('\n')[0].strip()
            else:
                job_item['company'] = "Unknown"

        if not job_item.get('description'):
            # Get description container
            desc_html = response.css('div#JobDescriptionContainer').get()
            if desc_html:
                # Basic cleanup: remove <script> and <style> tags
                desc_html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', desc_html, flags=re.DOTALL)
                job_item['description'] = desc_html

        # --- FALLBACKS FOR DATE & LOCATION ---

        if not job_item.get('posted_at'):
            # Try to use the text we scraped from the search card ("3d", "24h")
            card_date = response.meta.get('card_date_text')
            if card_date:
                job_item['posted_at'] = parse_relative_date(card_date)
            else:
                job_item['posted_at'] = datetime.now().date()

        if not job_item.get('location'):
            job_item['location'] = self.location_name  # Use the search argument as fallback

        job_item['skills'] = []  # Handled by pipeline

        yield job_item