from celery import shared_task
import subprocess


@shared_task
def run_scrapers(keyword='Python', location='Europe'):
    # 1. Run LinkedIn Spider with Dynamic Arguments
    # We pass -a keyword=... -a location=... to Scrapy
    subprocess.run([
        "scrapy", "crawl", "linkedin",
        "-a", f"keyword={keyword}",
        "-a", f"location={location}"
    ], cwd="/app/scraper_service")

    # 2. Run Python.org spider ONLY if the keyword is related to Python
    # (Since python.org doesn't list C++ jobs)
    if 'python' in keyword.lower():
        subprocess.run(["scrapy", "crawl", "remote_python"], cwd="/app/scraper_service")

    return f"Scraping Finished for {keyword} in {location}"