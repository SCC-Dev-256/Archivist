# PURPOSE: Main scraper script for Minnesota city websites
# DEPENDENCIES: scrapy, config, enhanced_pdf_spider
# MODIFICATION NOTES: v1.0 - Initial implementation

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from .pipelines import PdfFilesPipeline

from .config import load_config, SiteConfig
from .spiders.enhanced_pdf_spider import EnhancedPdfSpider


 


class CityScraper:
    """Main scraper class for Minnesota city websites."""
    
    def __init__(self, config_path: str | Path = "scraper/sites.json"):
        self.config_path = Path(config_path)
        self.sites = load_config(self.config_path)
        self.results: List[Dict[str, Any]] = []
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def run(self) -> List[Dict[str, Any]]:
        """Run the scraper for all configured sites."""
        self.logger.info(f"Starting scraper for {len(self.sites)} sites")
        
        # Configure Scrapy settings
        settings = get_project_settings()
        import os
        from pathlib import Path
        settings.update({
            'USER_AGENT': 'Mozilla/5.0 (compatible; CityScraper/1.0)',
            'ROBOTSTXT_OBEY': True,
            'DOWNLOAD_DELAY': 1,  # Be respectful
            'CONCURRENT_REQUESTS': 1,
            'RETRY_TIMES': int(os.getenv('SCRAPY_RETRY_TIMES', '2')),
            'RETRY_HTTP_CODES': [500, 502, 503, 504, 522, 524, 408, 429],
            'ITEM_PIPELINES': {
                'scraper.pipelines.PdfFilesPipeline': 100,
            },
            'FILES_STORE': (lambda p: str(Path(p).resolve()) if not Path(p).is_absolute() else p)(os.getenv('FILES_STORE', 'downloads')),
            'FILES_EXPIRES': 0,
            'MEDIA_ALLOW_REDIRECTS': True,
            'HTTPERROR_ALLOWED_CODES': [301, 302, 303, 307, 308],
            'DOWNLOADER_MIDDLEWARES': {
                'scraper.middlewares.EarlyGuardMiddleware': 543,
            },
            'MAX_CONTENT_LENGTH': int(os.getenv('MAX_CONTENT_LENGTH', str(50 * 1024 * 1024))),
            'HEAD_CACHE_TTL': int(os.getenv('HEAD_CACHE_TTL', '3600')),
            'FEEDS': {
                'results.json': {
                    'format': 'json',
                    'encoding': 'utf8',
                    'indent': 2,
                    'overwrite': True,
                }
            }
        })
        
        # Create crawler process
        process = CrawlerProcess(settings)
        
        # Add spiders for each site
        for site in self.sites:
            self.logger.info(f"Adding spider for {site.city}: {site.url}")
            process.crawl(
                EnhancedPdfSpider,
                start_url=site.url,
                selectors=site.selectors,
                city=site.city,
                notes=site.notes
            )
        
        # Run the crawler
        process.start()
        
        # Load results
        results_file = Path("results.json")
        if results_file.exists():
            with results_file.open('r') as f:
                self.results = json.load(f)
            self.logger.info(f"Found {len(self.results)} PDF URLs")
        
        return self.results

    def save_results(self, output_path: str | Path = "scraped_pdfs.json"):
        """Save results to a JSON file."""
        output_path = Path(output_path)
        with output_path.open('w') as f:
            json.dump(self.results, f, indent=2)
        self.logger.info(f"Results saved to {output_path}")

    def get_city_summary(self) -> Dict[str, int]:
        """Get summary of PDFs found per city."""
        summary = {}
        for result in self.results:
            city = result.get('city', 'Unknown')
            summary[city] = summary.get(city, 0) + 1
        return summary


def main():
    """Main entry point."""
    scraper = CityScraper()
    results = scraper.run()
    
    # Print summary
    summary = scraper.get_city_summary()
    print("\nScraping Summary:")
    for city, count in summary.items():
        print(f"  {city}: {count} PDFs")
    
    # Save results
    scraper.save_results()


if __name__ == "__main__":
    main() 