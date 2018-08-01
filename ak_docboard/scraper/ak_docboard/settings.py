
BOT_NAME = 'ak_docboard'

SPIDER_MODULES = ['ak_docboard.spiders']
NEWSPIDER_MODULE = 'ak_docboard.spiders'

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:15.0) Gecko/20100101 Firefox/15.0.1'

RANDOMIZE_DOWNLOAD_DELAY = False
DOWNLOAD_DELAY = 2
ROBOTSTXT_OBEY = True

from datetime import datetime
LOG_FILE = "scrapy_%s.log" % datetime.now().strftime("%Y%m%d_%H%M%S")

HTTPCACHE_ENABLED = True
HTTPCACHE_IGNORE_HTTP_CODES = range(500,599)
HTTPCACHE_EXPIRATION_SECS = 0 # Keep indefinitely
HTTPCACHE_STORAGE = 'scrapy.contrib.downloadermiddleware.httpcache.FilesystemCacheStorage'

DOWNLOADER_MIDDLEWARES = {
    'scrapy.contrib.downloadermiddleware.httpcompression.HttpCompressionMiddleware': None,
	# Disable compression middleware, so the actual HTML pages are cached
}

ITEM_PIPELINES = [
    'kyruus.scraper.cleansingpipeline.CleansingPipeline',
]

FEED_EXPORTERS = {
     'jsonlines': 'scrapy.contrib.exporter.JsonLinesItemExporter',
}
FEED_FORMAT = 'jsonlines'
FEED_URI = "output/%(name)s/%(time)s.json"

EXTENSIONS = {
    'scrapy.contrib.statsmailer.StatsMailer': 500
    }
STATSMAILER_RCPTS = ['crawler-errors@kyru.us', 'ajmal.ismail@arbisoft.com']
PREFIX = "http://docboard.madriveraccess.com/ak/"