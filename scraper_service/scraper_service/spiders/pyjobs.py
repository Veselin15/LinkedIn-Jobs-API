import scrapy
from datetime import date


class RemotePythonSpider(scrapy.Spider):
    name = "remote_python"
    # We are switching to python.org because it is very stable for learning
    start_urls = ["https://www.python.org/jobs/"]

    def parse(self, response):
        # Python.org lists jobs in an <ol> with class 'list-recent-jobs'
        for job in response.css("ol.list-recent-jobs li"):
            # Extracting the 'a' tag which contains the title and link
            title_tag = job.css("h2.listing-company a")

            # Extract company name (it's often inside a span with class 'listing-company-name')
            # We strip() to remove extra whitespace/newlines
            company_text = job.css("span.listing-company-name::text").getall()
            # join helps if the text is split across multiple lines
            company = "".join(company_text).strip().split('\n')[-1].strip()

            yield {
                'title': title_tag.css("::text").get(),
                'company': company,
                'location': job.css("span.listing-location::text").get(),
                'url': response.urljoin(title_tag.css("::attr(href)").get()),
                'source': "Python.org",
                'posted_at': date.today()
            }