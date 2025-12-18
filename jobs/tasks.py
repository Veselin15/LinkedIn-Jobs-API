from celery import shared_task
import subprocess

@shared_task
def run_scrapers():
    # This runs the scrapy command inside the container
    subprocess.run(["scrapy", "crawl", "linkedin"], cwd="/app/scraper_service")
    subprocess.run(["scrapy", "crawl", "remote_python"], cwd="/app/scraper_service")
    return "Scraping Finished"