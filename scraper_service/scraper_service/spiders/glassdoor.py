import scrapy
from datetime import datetime
from ..items import JobItem


class GlassdoorSpider(scrapy.Spider):
    name = "glassdoor"
    allowed_domains = ["glassdoor.com"]
    # We search for "Software Engineer" jobs in the US (ID: 1)
    # You can change 'keyword' and 'locId' as needed
    start_urls = [
        "https://www.glassdoor.com/Job/jobs.htm?sc.keyword=Software%20Engineer&locT=N&locId=1"
    ]

    custom_settings = {
        # Glassdoor requires a real browser User-Agent
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'DOWNLOAD_DELAY': 5,  # Slow down to avoid bans
        'AUTOTHROTTLE_ENABLED': True,
        'COOKIES_ENABLED': False
    }

    def parse(self, response):
        # 1. Parse the Job List
        job_listings = response.css('li[data-test="jobListing"]')

        for job in job_listings:
            # Extract basic info from the card
            title = job.css('a[data-test="job-link"] span::text').get()
            company = job.css('div.employer-name::text').get()
            location = job.css('div[data-test="emp-location"]::text').get()
            detail_url = job.css('a[data-test="job-link"]::attr(href)').get()

            # Glassdoor URLs are relative
            if detail_url:
                detail_url = response.urljoin(detail_url)

            # We pass this info to the "parse_detail" method to get the description
            yield scrapy.Request(
                detail_url,
                callback=self.parse_detail,
                meta={
                    'title': title,
                    'company': company,
                    'location': location,
                    'url': detail_url
                }
            )

        # 2. Pagination (Try to find the "Next" button)
        next_page = response.css('a[data-test="pagination-next"]::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_detail(self, response):
        # 3. Parse the Full Description page
        description = response.css('div.jobDescriptionContent').get()

        # Clean Company Name (Glassdoor often adds ratings like "Google 4.5 ★")
        company = response.meta['company']
        if company:
            company = company.split('\n')[0].strip()

        yield JobItem(
            title=response.meta['title'],
            company=company,
            location=response.meta['location'] or "Remote",
            url=response.meta['url'],
            posted_at=datetime.now().date(),  # Glassdoor dates are hard (e.g. "3d" or "24h"), defaulting to today
            description=description,
            source="Glassdoor",
            skills=[],  # The pipeline will extract these from description
            salary_min=None,
            salary_max=None,
            currency=None
        )