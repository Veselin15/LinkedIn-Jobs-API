# scraper_service/settings.py
import os
import sys
import django

# 1. Django Integration
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

BOT_NAME = "scraper_service"
SPIDER_MODULES = ["scraper_service.spiders"]
NEWSPIDER_MODULE = "scraper_service.spiders"

# 2. Concurrency
ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 3  # Be gentle
CONCURRENT_REQUESTS = 1

# 3. Output
FEED_EXPORT_ENCODING = "utf-8"

# --- 4. MIDDLEWARES (THE FIX) ---
DOWNLOADER_MIDDLEWARES = {
    # DISABLE default UserAgent middleware (It causes the 403 conflict!)
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,

    # DISABLE RandomUserAgent if you have it installed
    'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': None,

    # ENABLE Retry
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 550,
}

# --- 5. IMPERSONATE SETTINGS ---
# This replaces the default downloader with one that mimics a real browser
DOWNLOAD_HANDLERS = {
    "http": "scrapy_impersonate.ImpersonateDownloadHandler",
    "https": "scrapy_impersonate.ImpersonateDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# 6. PIPELINES
ITEM_PIPELINES = {
    "scraper_service.pipelines.ScraperServicePipeline": 300,
}