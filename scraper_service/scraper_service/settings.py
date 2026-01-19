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

# 2. Concurrency & Politeness
ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 3
CONCURRENT_REQUESTS = 1

# 3. Output
FEED_EXPORT_ENCODING = "utf-8"

# 4. Disable Scrapy's Default Headers (CRITICAL FOR IMPERSONATE)
# We let the impersonate library handle ALL headers.
DEFAULT_REQUEST_HEADERS = {}

# 5. Middlewares
DOWNLOADER_MIDDLEWARES = {
    # Disable Scrapy's UserAgent middleware (conflicts with impersonate)
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,

    # Disable RandomUserAgent (conflicts with impersonate)
    'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': None,

    # Enable Retry
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 550,
}

# 6. Impersonate Settings
DOWNLOAD_HANDLERS = {
    "http": "scrapy_impersonate.ImpersonateDownloadHandler",
    "https": "scrapy_impersonate.ImpersonateDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# 7. Pipelines
ITEM_PIPELINES = {
    "scraper_service.pipelines.ScraperServicePipeline": 300,
}