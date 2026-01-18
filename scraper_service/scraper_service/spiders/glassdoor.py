import scrapy
import json
import re
from datetime import datetime, timedelta
from ..items import JobItem


class GlassdoorSpider(scrapy.Spider):
    name = "glassdoor"
    allowed_domains = ["glassdoor.com"]

    # Targeting "Software Engineer" (US).
    # TIP: 'locId=1' is US. 'locId=0' is often worldwide or requires specific country codes.
    start_urls = [
        "https://www.glassdoor.com/Job/jobs.htm?sc.keyword=Software%20Engineer&locT=N&locId=1"
    ]

    custom_settings = {
        # Mimic a full browser request to avoid 403 Forbidden
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
        'DOWNLOAD_DELAY': 10,  # Glassdoor is very strict; slower is safer
        'AUTOTHROTTLE_ENABLED': True,
        'COOKIES_ENABLED': False  # Sometimes helps avoid tracking bans
    }

    def parse(self, response):
        # 1. Parse the Job Cards
        # Glassdoor often changes classes, but data-test attributes are usually stable
        job_listings = response.css('li[data-test="jobListing"]')

        for job in job_listings:
            url = job.css('a[data-test="job-link"]::attr(href)').get()

            # Glassdoor URLs are often relative
            if url:
                url = response.urljoin(url)

                # Pass partial data to the detail parser
                yield scrapy.Request(
                    url,
                    callback=self.parse_detail,
                    meta={
                        'listing_url': url
                    }
                )

        # 2. Pagination
        next_page = response.css('a[data-test="pagination-next"]::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_detail(self, response):
        """
        Strategy: Try to find the JSON-LD schema (Structured Data).
        It is much more reliable than parsing messy HTML divs.
        """
        job_item = JobItem()
        job_item['url'] = response.meta['listing_url']
        job_item['source'] = "Glassdoor"

        # Method A: JSON-LD (Best / Most Reliable)
        json_ld_script = response.xpath('//script[@type="application/ld+json"]/text()').get()

        if json_ld_script:
            try:
                data = json.loads(json_ld_script)

                # Handle case where JSON is a list of schemas
                if isinstance(data, list):
                    # Look for the 'JobPosting' schema type
                    data = next((item for item in data if item.get('@type') == 'JobPosting'), {})

                job_item['title'] = data.get('title')
                job_item['description'] = data.get('description')

                # Company
                org = data.get('hiringOrganization', {})
                if isinstance(org, dict):
                    job_item['company'] = org.get('name')
                else:
                    job_item['company'] = org  # Sometimes it's just a string

                # Location
                loc = data.get('jobLocation', {})
                if isinstance(loc, dict):
                    address = loc.get('address', {})
                    if isinstance(address, dict):
                        # Construct "City, Region"
                        city = address.get('addressLocality', '')
                        region = address.get('addressRegion', '')
                        job_item['location'] = f"{city}, {region}".strip(', ')

                # Date Posted
                date_str = data.get('datePosted')
                if date_str:
                    try:
                        job_item['posted_at'] = datetime.strptime(date_str.split('T')[0], "%Y-%m-%d").date()
                    except ValueError:
                        job_item['posted_at'] = datetime.now().date()

                # Salary (If available in JSON)
                salary = data.get('baseSalary', {})
                if isinstance(salary, dict):
                    value = salary.get('value', {})
                    job_item['salary_min'] = value.get('minValue')
                    job_item['salary_max'] = value.get('maxValue')
                    job_item['currency'] = salary.get('currency', 'USD')

            except json.JSONDecodeError:
                self.logger.warning(f"Failed to decode JSON-LD for {response.url}")

        # Method B: Fallback to HTML parsing if JSON failed or keys are missing
        if not job_item.get('title'):
            job_item['title'] = response.css('div.css-17x2pwl::text').get() or response.css('h1::text').get()

        if not job_item.get('company'):
            # Glassdoor puts rating stars in the name, e.g. "Google 4.5 ★"
            # We take the first part of the text node
            raw_company = response.css('div[data-test="employer-name"]::text').get()
            job_item['company'] = raw_company.split('\n')[0].strip() if raw_company else "Unknown"

        if not job_item.get('description'):
            job_item['description'] = response.css('div#JobDescriptionContainer').get()

        # Default missing fields
        if not job_item.get('posted_at'):
            job_item['posted_at'] = datetime.now().date()

        if not job_item.get('location'):
            job_item['location'] = "Remote"  # Fallback

        job_item['skills'] = []  # Let pipeline handle extraction

        yield job_item