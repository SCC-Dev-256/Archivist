from __future__ import annotations

import scrapy


class PdfSpider(scrapy.Spider):
    """Simple spider that yields discovered PDF URLs.

    The spider is configured with a single start URL, a list of CSS selectors
    that point to links. Each discovered link is emitted as an item with the
    original URL and the configured city/category.
    """

    name = "pdf_spider"

    def __init__(self, start_url: str, selectors: list[str], city: str, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = [start_url]
        self.selectors = selectors
        self.city = city

    def parse(self, response):  # pragma: no cover - Scrapy runtime
        for selector in self.selectors:
            for href in response.css(selector).xpath("@href").getall():
                url = response.urljoin(href)
                yield {"url": url, "city": self.city}
