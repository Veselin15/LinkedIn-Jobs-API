from celery import shared_task
import subprocess
from datetime import timedelta
from django.utils import timezone
from .models import Job


@shared_task
def run_scrapers(keyword='Python', location='Europe'):
    """
    On-Demand Task: Triggered when a user clicks 'Search' or 'Scrape'.
    Runs LinkedIn for the specific keyword AND grabs the latest WWR feed.
    """
    results = []

    # 1. Run We Work Remotely (Fast & Reliable - 2 seconds)
    print(f"🚀 [On-Demand] Starting WWR Scrape...")
    subprocess.run([
        "scrapy", "crawl", "wwr"
    ], cwd="/app/scraper_service")
    results.append("WWR")

    # 2. Run LinkedIn (Targeted Search - 20-30 seconds)
    print(f"🔎 [On-Demand] Starting LinkedIn Scrape for {keyword}...")
    subprocess.run([
        "scrapy", "crawl", "linkedin",
        "-a", f"keyword={keyword}",
        "-a", f"location={location}"
    ], cwd="/app/scraper_service")
    results.append("LinkedIn")

    return f"Scraping Finished. Sources: {', '.join(results)}"


@shared_task
def run_bulk_scrape():
    """
    Scheduled Task: Runs periodically (e.g., every 6 hours).
    Populates the database with a wide variety of jobs from ALL sources.
    """
    results = []

    # --- PART 1: We Work Remotely (The Safety Net) ---
    # This is an RSS feed, so it's very fast and safe to run often.
    print("🚀 [Bulk] Starting WeWorkRemotely Scrape...")
    subprocess.run([
        "scrapy", "crawl", "wwr"
    ], cwd="/app/scraper_service")
    results.append("WeWorkRemotely")

    # --- PART 2: LinkedIn (The Heavy Lifter) ---
    # We loop through popular keywords to build a rich database.
    # Note: Keep this list focused to avoid hitting LinkedIn rate limits.
    tech_stack = ["Python", "JavaScript", "React", "Django", "DevOps", "Data"]
    regions = ["Remote", "Europe", "United States"]

    for tech in tech_stack:
        for region in regions:
            print(f"🔎 [Bulk] LinkedIn Scrape: {tech} - {region}")

            # We wait for each process to finish before starting the next
            # This acts as a natural rate-limiter.
            subprocess.run([
                "scrapy", "crawl", "linkedin",
                "-a", f"keyword={tech}",
                "-a", f"location={region}"
            ], cwd="/app/scraper_service")

            results.append(f"LI:{tech}-{region}")

    return f"Bulk Scrape Complete. Covered: {', '.join(results)}"


@shared_task
def cleanup_old_jobs():
    """
    Janitor Task: Deletes jobs posted more than 30 days ago.
    Keeps the database fresh and fast.
    """
    cutoff_date = timezone.now().date() - timedelta(days=30)

    # The _ is strictly standard variable naming for "ignored return value"
    deleted_count, _ = Job.objects.filter(posted_at__lt=cutoff_date).delete()

    return f"Janitor Report: Deleted {deleted_count} jobs older than {cutoff_date}"