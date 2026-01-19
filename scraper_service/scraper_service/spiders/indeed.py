import scrapy
import json
import re
import random
from datetime import datetime
from urllib.parse import urlencode
from ..items import JobItem
from ..utils import parse_relative_date


class IndeedSpider(scrapy.Spider):
    name = "indeed"
    allowed_domains = ["indeed.com"]

    def __init__(self, keyword='Python', location='Remote', *args, **kwargs):
        super(IndeedSpider, self).__init__(*args, **kwargs)
        self.keyword = keyword
        self.location = location

    def start_requests(self):
        params = {
            'q': self.keyword,
            'l': self.location,
            'sort': 'date'
        }
        url = f"https://www.indeed.com/jobs?{urlencode(params)}"

        # Use 'chrome110' which is often more stable for this library
        yield scrapy.Request(
            url=url,
            callback=self.parse,
            meta={'impersonate': 'chrome110'}
        )

    custom_settings = {
        # REMOVED: DEFAULT_REQUEST_HEADERS (Let impersonate handle it!)
        # We only keep essential Scrapy settings
        'DOWNLOAD_DELAY': 5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'COOKIES_ENABLED': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [403, 429, 500, 503],
    }

    def parse(self, response):
        job_cards = response.css('td.resultContent')

        if not job_cards:
            self.logger.warning(f"⚠️ No jobs found or blocked (Status: {response.status})")

        for card in job_cards:
            href = card.css('h2.jobTitle a::attr(href)').get()
            if href:
                jk_match = re.search(r'jk=([a-zA-Z0-9]+)', href)
                if jk_match:
                    jk = jk_match.group(1)
                    job_url = f"https://www.indeed.com/viewjob?jk={jk}"

                    yield scrapy.Request(
                        job_url,
                        callback=self.parse_detail,
                        meta={
                            'listing_url': job_url,
                            'impersonate': 'chrome110'  # Consistent fingerprint
                        }
                    )

        next_page = response.css('a[data-testid="pagination-page-next"]::attr(href)').get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse,
                meta={'impersonate': 'chrome110'}
            )

    def parse_detail(self, response):
        """
        Parse the Job Detail Page.
        Strategy: Use JSON-LD (Structured Data) for reliability.
        """
        job_item = JobItem()
        job_item['url'] = response.meta['listing_url']
        job_item['source'] = "Indeed"

        # --- METHOD A: JSON-LD (Most Reliable) ---
        json_ld_script = response.xpath('//script[@type="application/ld+json"]/text()').get()
        data = {}

        if json_ld_script:
            try:
                data = json.loads(json_ld_script)
                # Indeed sometimes puts the schema inside a list
                if isinstance(data, list):
                    # We want the 'JobPosting' schema
                    data = next((item for item in data if item.get('@type') == 'JobPosting'), {})
            except json.JSONDecodeError:
                pass

        # Extract data if we found the schema
        if data:
            job_item['title'] = data.get('title')
            job_item['description'] = data.get('description')

            # Company
            org = data.get('hiringOrganization', {})
            if isinstance(org, dict):
                job_item['company'] = org.get('name')
            else:
                job_item['company'] = "Unknown"

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
                    job_item['posted_at'] = datetime.now().date()

            # Salary (Indeed is good at providing this in JSON)
            salary = data.get('baseSalary', {})
            if isinstance(salary, dict):
                val = salary.get('value', {})
                # It might be a range (minValue/maxValue) or a specific value
                job_item['salary_min'] = val.get('minValue') or val.get('value')
                job_item['salary_max'] = val.get('maxValue')
                job_item['currency'] = salary.get('currency', 'USD')

        # --- METHOD B: HTML Fallback (If JSON is missing) ---
        if not job_item.get('title'):
            job_item['title'] = response.css('h1.jobsearch-JobInfoHeader-title span::text').get()

        if not job_item.get('company'):
            job_item['company'] = response.css('div[data-company-name="true"] a::text').get()

        if not job_item.get('description'):
            job_item['description'] = response.css('div#jobDescriptionText').get()

        # Defaults
        if not job_item.get('posted_at'):
            job_item['posted_at'] = datetime.now().date()

        if not job_item.get('location'):
            job_item['location'] = self.location

        job_item['skills'] = []  # Handled by pipeline

        yield job_item