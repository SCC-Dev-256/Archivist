from __future__ import annotations

import scrapy
from urllib.parse import urlparse


class PdfSpider(scrapy.Spider):
    """Simple spider that yields discovered PDF URLs.

    The spider is configured with a single start URL, a list of CSS selectors
    that point to links. Each discovered link is emitted as an item with the
    original URL and the configured city/category.
    """

    name = "pdf_spider"

    def __init__(self, start_url: str, selectors: list[str], city: str, allowed_domains: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = [start_url]
        self.selectors = selectors
        self.city = city
        parsed = urlparse(start_url)
        inferred = [parsed.hostname] if parsed.hostname else []
        self.allowed_domains = allowed_domains or inferred
        self.custom_settings = {
            'ROBOTSTXT_OBEY': True,
        }

    def parse(self, response):  # pragma: no cover - Scrapy runtime
        for selector in self.selectors:
            for href in response.css(selector).xpath("@href").getall():
                url = response.urljoin(href)
                # Only emit PDFs, keep on-site
                if not url.lower().endswith('.pdf'):
                    continue
                if self.allowed_domains and urlparse(url).hostname not in self.allowed_domains:
                    continue
                yield {"file_urls": [url], "city": self.city}
