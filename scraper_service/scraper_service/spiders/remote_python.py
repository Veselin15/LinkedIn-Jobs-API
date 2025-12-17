import scrapy
from datetime import date


class RemotePythonSpider(scrapy.Spider):
    name = "remote_python"
    # We will start with a specific job board or search result page
    # For this example, we'll use a search query on a mock-friendly site or a real one.
    # Let's try PyJobs (it's specific to Python).
    start_urls = ["https://www.pyjobs.com/jobs"]

    def parse(self, response):
        # Loop through each job card on the page
        # Note: Selectors (.css) depend on the website's HTML structure.
        # These are examples and might need adjustment if PyJobs changes layout.

        for job in response.css("div.job-listing"):
            yield {
                'title': job.css("h2.job-title::text").get(),
                'company': job.css("span.company-name::text").get(),
                'location': "Remote",  # Defaulting for now
                'url': response.urljoin(job.css("a::attr(href)").get()),
                'source': "PyJobs",
                'posted_at': date.today()  # Placeholder, ideally we parse the date
            }