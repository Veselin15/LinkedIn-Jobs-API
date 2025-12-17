import scrapy
from datetime import date


class LinkedInSpider(scrapy.Spider):
    name = "linkedin"

    # 1. The Entry Point
    def start_requests(self):
        # We search for "Python" in "Europe" (GeoID 91000000 for Europe-wide)
        # We use the 'seeMoreJobPostings' internal API which is easier to scrape
        base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Python&location=Europe&start={}"

        # Scrape the first 5 pages (0, 25, 50, 75, 100)
        for i in range(0, 101, 25):
            yield scrapy.Request(url=base_url.format(i), callback=self.parse_list)

    # 2. Parse the List of Jobs
    def parse_list(self, response):
        # The API returns a list of <li> elements. We loop through them.
        for job in response.css("li"):

            # Extract the simplified data
            title = job.css("h3.base-search-card__title::text").get()
            company = job.css("h4.base-search-card__subtitle a::text").get()
            location = job.css("span.job-search-card__location::text").get()

            # We need the direct URL to get the full description (and to save it)
            # The 'href' usually includes tracking garbage, we clean it.
            raw_url = job.css("a.base-card__full-link::attr(href)").get()

            if title and raw_url:
                clean_title = title.strip()
                clean_company = company.strip() if company else "Unknown"
                clean_location = location.strip() if location else "Remote"
                clean_url = raw_url.split('?')[0]  # Remove tracking params

                # 3. Save the Data
                # Note: LinkedIn doesn't give "posted_at" easily in this view,
                # so we use today's date.
                yield {
                    'title': clean_title,
                    'company': clean_company,
                    'location': clean_location,
                    'url': clean_url,
                    'source': "LinkedIn",
                    'posted_at': date.today()
                }