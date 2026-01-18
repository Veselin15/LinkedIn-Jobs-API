import logging
import subprocess
from celery import shared_task
from datetime import timedelta
from django.utils import timezone
from .models import Job

# Get an instance of a logger
logger = logging.getLogger(__name__)


@shared_task
def run_scrapers(keyword='Python', location='Europe'):
    """
    On-Demand Task: Triggered when a user clicks 'Search' or 'Scrape'.
    Runs LinkedIn for the specific keyword AND grabs the latest WWR feed.
    """
    results = []

    # 1. We Work Remotely (Fast & Reliable)
    try:
        logger.info(f"🚀 [On-Demand] Starting WWR Scrape...")
        subprocess.run(
            ["scrapy", "crawl", "wwr"],
            cwd="/app/scraper_service",
            check=True,
            timeout=60
        )
        results.append("WWR")
    except subprocess.CalledProcessError:
        logger.error("❌ [On-Demand] WWR Scraper Failed")
    except subprocess.TimeoutExpired:
        logger.error("⚠️ [On-Demand] WWR Scraper Timed Out")

    # 2. LinkedIn (Targeted Search)
    try:
        logger.info(f"🔍 [On-Demand] Starting LinkedIn Scrape for {keyword}...")
        subprocess.run(
            [
                "scrapy", "crawl", "linkedin",
                "-a", f"keyword={keyword}",
                "-a", f"location={location}"
            ],
            cwd="/app/scraper_service",
            timeout=180,  # 3 minutes hard limit
            check=True
        )
        results.append("LinkedIn")
    except subprocess.TimeoutExpired:
        logger.warning(f"⚠️ Scrape for {keyword} timed out! Process killed.")
        return "LinkedIn Scrape Timed Out"
    except Exception as e:
        logger.error(f"❌ LinkedIn Scrape Failed: {str(e)}")

    return f"Scraping Finished. Sources: {', '.join(results)}"


@shared_task
def run_bulk_scrape():
    """
    Scheduled Task: Runs periodically (e.g., every 6 hours).
    Populates the database with a wide variety of jobs from ALL sources.
    """
    results = []

    # Define a helper to run scrapers safely
    def run_spider(spider_name, timeout=120):
        try:
            logger.info(f"🚀 [Bulk] Starting {spider_name}...")
            subprocess.run(
                ["scrapy", "crawl", spider_name],
                cwd="/app/scraper_service",
                timeout=timeout,
                check=True,
                stdout=subprocess.PIPE,  # Capture output to avoid log spam
                stderr=subprocess.PIPE
            )
            results.append(spider_name)
            logger.info(f"✅ [Bulk] {spider_name} Finished")
        except subprocess.TimeoutExpired:
            logger.error(f"⚠️ [Bulk] {spider_name} Timed Out")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ [Bulk] {spider_name} Failed: {e.stderr.decode()}")

    # --- PART 1: The Fast/API Scrapers ---
    run_spider("wwr")
    run_spider("remoteok")
    run_spider("pyjobs")  # Added this since it exists in your project

    # --- PART 2: The "Hard" Scrapers ---
    # Glassdoor often blocks IPs, so we treat it carefully
    run_spider("glassdoor", timeout=180)
    run_spider("indeed", timeout=180)

    # --- PART 3: LinkedIn (The Heavy Lifter) ---
    tech_stack = ["Python", "JavaScript", "React", "DevOps", "Data", "C#", "Java"]
    regions = ["Remote", "Europe", "United States"]

    for tech in tech_stack:
        for region in regions:
            task_name = f"LI:{tech}-{region}"
            try:
                logger.info(f"🔎 [Bulk] LinkedIn: {tech} in {region}")
                subprocess.run(
                    [
                        "scrapy", "crawl", "linkedin",
                        "-a", f"keyword={tech}",
                        "-a", f"location={region}"
                    ],
                    cwd="/app/scraper_service",
                    timeout=120,
                    check=True,
                    stdout=subprocess.DEVNULL,  # Silence standard output
                    stderr=subprocess.PIPE  # Capture errors only
                )
                results.append(task_name)
            except Exception as e:
                logger.error(f"❌ Failed {task_name}: {e}")

    final_report = f"Bulk Scrape Complete. Covered: {', '.join(results)}"
    logger.info(final_report)
    return final_report


@shared_task
def cleanup_old_jobs():
    """
    Janitor Task: Deletes jobs posted more than 30 days ago.
    """
    cutoff_date = timezone.now().date() - timedelta(days=30)
    deleted_count, _ = Job.objects.filter(posted_at__lt=cutoff_date).delete()

    msg = f"🧹 Janitor: Deleted {deleted_count} jobs older than {cutoff_date}"
    logger.info(msg)
    return msg