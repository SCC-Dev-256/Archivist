# PURPOSE: Enhanced PDF spider that handles different city website platforms
# DEPENDENCIES: scrapy, SiteConfig
# MODIFICATION NOTES: v1.0 - Initial implementation for Minnesota city websites

from __future__ import annotations

import scrapy
from urllib.parse import urljoin, urlparse
import re


class EnhancedPdfSpider(scrapy.Spider):
    """Enhanced spider that handles different city website platforms.

    Supports:
    - CivicEngage platforms (Oakdale, Lake Elmo, Mahtomedi, White Bear Township)
    - WordPress sites (Birchwood)
    - Drupal sites (Grant)
    - Sites with Cloudflare protection (White Bear Lake)
    """

    name = "enhanced_pdf_spider"

    def __init__(self, start_url: str, selectors: list[str], city: str, notes: str = "", **kwargs):
        super().__init__(**kwargs)
        self.start_urls = [start_url]
        self.selectors = selectors
        self.city = city
        self.notes = notes
        self.platform = self._detect_platform(notes)
        
        # Set custom headers for better compatibility
        self.custom_settings = {
            'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'DOWNLOAD_DELAY': 2,
            'RANDOMIZE_DOWNLOAD_DELAY': 1,
            'COOKIES_ENABLED': True,
            'DOWNLOAD_TIMEOUT': 30,
        }

    def _detect_platform(self, notes: str) -> str:
        """Detect the platform type from notes."""
        notes_lower = notes.lower()
        if "civicengage" in notes_lower:
            return "civicengage"
        elif "wordpress" in notes_lower:
            return "wordpress"
        elif "drupal" in notes_lower:
            return "drupal"
        elif "cloudflare" in notes_lower:
            return "cloudflare"
        return "unknown"

    def parse(self, response):  # pragma: no cover - Scrapy runtime
        """Parse the main page and extract PDF links."""
        
        if self.platform == "civicengage":
            yield from self._parse_civicengage(response)
        elif self.platform == "wordpress":
            yield from self._parse_wordpress(response)
        elif self.platform == "drupal":
            yield from self._parse_drupal(response)
        elif self.platform == "cloudflare":
            yield from self._parse_cloudflare(response)
        else:
            yield from self._parse_generic(response)
    
    def errback_httpbin(self, failure):
        """Handle HTTP errors."""
        from scrapy.spidermiddlewares.httperror import HttpError
        if failure.check(HttpError):
            response = failure.value.response
            self.logger.error(f"HTTP Error {response.status} for {response.url}")
        else:
            self.logger.error(f"Request failed: {failure.value}")

    def _parse_civicengage(self, response):
        """Parse CivicEngage platform pages with pagination and date range support."""
        # First, extract PDF links from current page
        for selector in self.selectors:
            for href in response.css(selector).xpath("@href").getall():
                url = response.urljoin(href)
                # Follow the ViewFile link to get the actual PDF
                yield scrapy.Request(
                    url,
                    callback=self._extract_civicengage_pdf,
                    meta={"city": self.city, "original_url": url}
                )
        
        # Handle pagination - look for "View More" or "Next" links
        pagination_selectors = [
            "a:contains('View More')",
            "a:contains('Next')", 
            "a:contains('More')",
            ".pagination a[href*='page']",
            "a[href*='page=']",
            "a[href*='offset=']"
        ]
        
        for selector in pagination_selectors:
            for href in response.css(selector).xpath("@href").getall():
                url = response.urljoin(href)
                self.logger.info(f"Following pagination link: {url}")
                yield scrapy.Request(
                    url,
                    callback=self._parse_civicengage,
                    meta={"city": self.city}
                )
        
        # Handle date-based navigation - look for year/month links
        date_selectors = [
            "a[href*='year=']",
            "a[href*='month=']", 
            "a[href*='date=']",
            "select[name*='year'] option",
            "select[name*='month'] option"
        ]
        
        for selector in date_selectors:
            for href in response.css(selector).xpath("@href").getall():
                url = response.urljoin(href)
                self.logger.info(f"Following date link: {url}")
                yield scrapy.Request(
                    url,
                    callback=self._parse_civicengage,
                    meta={"city": self.city}
                )
        
        # Look for meeting type filters (agendas, minutes, packets)
        meeting_types = ["agenda", "minutes", "packet", "meeting"]
        for meeting_type in meeting_types:
            type_selectors = [
                f"a[href*='{meeting_type}']",
                f"a:contains('{meeting_type.title()}')",
                f"a[href*='{meeting_type.upper()}']"
            ]
            for selector in type_selectors:
                for href in response.css(selector).xpath("@href").getall():
                    url = response.urljoin(href)
                    self.logger.info(f"Following {meeting_type} link: {url}")
                    yield scrapy.Request(
                        url,
                        callback=self._parse_civicengage,
                        meta={"city": self.city}
                    )

    def _extract_civicengage_pdf(self, response):
        """Extract actual PDF URL from CivicEngage ViewFile page."""
        # CivicEngage ViewFile endpoints return either:
        # 1. Direct PDF binary content
        # 2. HTML page with PDF viewer/iframe
        # 3. Redirect to actual PDF
        
        # Check if response is a PDF file (binary content)
        content_type = response.headers.get('Content-Type', b'').decode('utf-8', errors='ignore')
        
        if 'application/pdf' in content_type or response.url.endswith('.pdf'):
            # This is already a PDF file, yield it directly
            self.logger.info(f"Found direct PDF: {response.url}")
            yield {"url": response.url, "city": self.city, "source": response.meta["original_url"]}
            return
        
        # Check if response is binary (PDF content)
        if len(response.body) > 1000 and not response.text.startswith('<!DOCTYPE') and not response.text.startswith('<html'):
            # Likely binary PDF content, yield the URL
            self.logger.info(f"Found binary PDF content: {response.url}")
            yield {"url": response.url, "city": self.city, "source": response.meta["original_url"]}
            return
        
        # Try to find PDF links in HTML content
        try:
            # Look for direct PDF links
            pdf_links = response.css("a[href$='.pdf']::attr(href)").getall()
            for pdf_link in pdf_links:
                url = response.urljoin(pdf_link)
                yield {"url": url, "city": self.city, "source": response.meta["original_url"]}
            
            # Look for iframe sources that might contain PDFs
            iframe_src = response.css("iframe::attr(src)").getall()
            for iframe in iframe_src:
                if ".pdf" in iframe or "ViewFile" in iframe:
                    url = response.urljoin(iframe)
                    yield {"url": url, "city": self.city, "source": response.meta["original_url"]}
            
            # Look for embed tags
            embed_src = response.css("embed::attr(src)").getall()
            for embed in embed_src:
                if ".pdf" in embed:
                    url = response.urljoin(embed)
                    yield {"url": url, "city": self.city, "source": response.meta["original_url"]}
            
            # Look for object tags
            object_data = response.css("object::attr(data)").getall()
            for obj_data in object_data:
                if ".pdf" in obj_data:
                    url = response.urljoin(obj_data)
                    yield {"url": url, "city": self.city, "source": response.meta["original_url"]}
                    
        except Exception as e:
            # If CSS parsing fails, the response might be binary
            # In this case, assume the URL itself is the PDF
            yield {"url": response.url, "city": self.city, "source": response.meta["original_url"]}

    def _parse_wordpress(self, response):
        """Parse WordPress site pages."""
        # WordPress sites typically have direct PDF links
        for selector in self.selectors:
            for href in response.css(selector).xpath("@href").getall():
                url = response.urljoin(href)
                if self._is_pdf_url(url):
                    yield {"url": url, "city": self.city, "source": response.url}
                elif self._is_agenda_page(url):
                    # Follow links to agenda pages
                    yield scrapy.Request(
                        url,
                        callback=self._parse_agenda_page,
                        meta={"city": self.city}
                    )

    def _parse_drupal(self, response):
        """Parse Drupal platform pages with comprehensive crawling."""
        # First, extract PDF links from current page
        pdf_links = response.css("a[href$='.pdf']::attr(href)").getall()
        for pdf_link in pdf_links:
            url = response.urljoin(pdf_link)
            yield {"url": url, "city": self.city, "source": response.url}
        
        # Follow agenda/minutes links to find PDFs
        agenda_selectors = [
            "a[href*='agenda']",
            "a[href*='Agenda']", 
            "a[href*='meeting']",
            "a[href*='Meeting']",
            "a[href*='minutes']",
            "a[href*='Minutes']"
        ]
        
        for selector in agenda_selectors:
            for href in response.css(selector).xpath("@href").getall():
                url = response.urljoin(href)
                # Only follow if it's not already a PDF
                if not url.endswith('.pdf'):
                    self.logger.info(f"Following Drupal agenda link: {url}")
                    yield scrapy.Request(
                        url,
                        callback=self._parse_drupal,
                        meta={"city": self.city}
                    )
        
        # Look for year/month subdirectories
        year_pattern = r'\b(20[12]\d)\b'  # 2010-2029
        month_pattern = r'\b(0[1-9]|1[0-2])\b'  # 01-12
        
        # Extract potential date-based links
        all_links = response.css("a::attr(href)").getall()
        for link in all_links:
            if any(year in link for year in ['2025', '2024', '2023', '2022', '2021', '2020']):
                url = response.urljoin(link)
                self.logger.info(f"Following Drupal date link: {url}")
                yield scrapy.Request(
                    url,
                    callback=self._parse_drupal,
                    meta={"city": self.city}
                )

    def _parse_cloudflare(self, response):
        """Parse sites with Cloudflare protection."""
        # These sites may require JavaScript rendering
        # For now, try basic PDF extraction
        for selector in self.selectors:
            for href in response.css(selector).xpath("@href").getall():
                url = response.urljoin(href)
                if self._is_pdf_url(url):
                    yield {"url": url, "city": self.city, "source": response.url}

    def _parse_generic(self, response):
        """Generic parsing for unknown platforms."""
        for selector in self.selectors:
            for href in response.css(selector).xpath("@href").getall():
                url = response.urljoin(href)
                if self._is_pdf_url(url):
                    yield {"url": url, "city": self.city, "source": response.url}

    def _parse_agenda_page(self, response):
        """Parse individual agenda/meeting pages."""
        # Look for PDF links on agenda pages
        pdf_links = response.css("a[href$='.pdf']::attr(href)").getall()
        for pdf_link in pdf_links:
            url = response.urljoin(pdf_link)
            yield {"url": url, "city": response.meta["city"], "source": response.url}

    def _is_pdf_url(self, url: str) -> bool:
        """Check if URL points to a PDF file."""
        return url.lower().endswith('.pdf')

    def _is_agenda_page(self, url: str) -> bool:
        """Check if URL is likely an agenda or meeting page."""
        agenda_keywords = ['agenda', 'meeting', 'council', 'minutes']
        url_lower = url.lower()
        return any(keyword in url_lower for keyword in agenda_keywords) 