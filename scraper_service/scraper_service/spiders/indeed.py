import scrapy
import re
from urllib.parse import urlencode
from ..items import JobItem
from datetime import datetime


class IndeedSpider(scrapy.Spider):
    name = "indeed"
    allowed_domains = ["indeed.com"]

    def __init__(self, keyword='Python', location='Remote', *args, **kwargs):
        super(IndeedSpider, self).__init__(*args, **kwargs)
        self.keyword = keyword
        self.location = location

    def start_requests(self):
        # Visit Homepage first to get cookies
        yield scrapy.Request(
            url="https://www.indeed.com/",
            callback=self.parse_home,
            # We use Safari because it has a distinct TLS fingerprint that Indeed trusts
            meta={'impersonate': 'safari15_5'},
            dont_filter=True
        )

    def parse_home(self, response):
        params = {'q': self.keyword, 'l': self.location, 'sort': 'date'}
        search_url = f"https://www.indeed.com/jobs?{urlencode(params)}"

        yield scrapy.Request(
            url=search_url,
            callback=self.parse_search,
            meta={'impersonate': 'safari15_5'},
            # Do NOT manually set User-Agent here. The library handles it.
            headers={
                'Referer': 'https://www.indeed.com/',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Dest': 'document',
            }
        )

    def parse_search(self, response):
        job_cards = response.css('td.resultContent')

        if not job_cards:
            # If this triggers, your IP might be blacklisted
            self.logger.warning(f"⚠️ No jobs found on {response.url} (Status: {response.status})")

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
                        meta={'impersonate': 'safari15_5'},
                        headers={'Referer': response.url}
                    )

        next_page = response.css('a[data-testid="pagination-page-next"]::attr(href)').get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse_search,
                meta={'impersonate': 'safari15_5'}
            )

    def parse_detail(self, response):
        job_item = JobItem()
        job_item['url'] = response.meta.get('listing_url', response.url)
        job_item['source'] = "Indeed"
        job_item['title'] = response.css('h1.jobsearch-JobInfoHeader-title span::text').get() or "Unknown"
        job_item['company'] = response.css('div[data-company-name="true"] a::text').get() or "Unknown"
        job_item['location'] = self.location
        job_item['description'] = response.css('div#jobDescriptionText').get()
        job_item['posted_at'] = datetime.now().date()
        job_item['skills'] = []

        if job_item['title'] != "Unknown":
            yield job_item