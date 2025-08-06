#!/usr/bin/env python3
# PURPOSE: Test enhanced scraper on all Minnesota city sites
# DEPENDENCIES: scrapy, config, enhanced_pdf_spider
# MODIFICATION NOTES: v1.0 - Comprehensive testing with enhanced features

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scraper.config import load_config, SiteConfig
from scraper.spiders.enhanced_pdf_spider import EnhancedPdfSpider

# Set up comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_test.log'),
        logging.StreamHandler()
    ]
)

class ComprehensiveTestPipeline:
    """Pipeline to collect and analyze all scraped results."""
    
    def __init__(self):
        self.results = []
        self.stats = {
            'total_pdfs': 0,
            'by_city': {},
            'by_platform': {},
            'errors': []
        }
    
    def process_item(self, item: Dict[str, Any], spider) -> Dict[str, Any]:
        """Process scraped items and collect statistics."""
        self.results.append(item)
        self.stats['total_pdfs'] += 1
        
        # Count by city
        city = item.get('city', 'unknown')
        self.stats['by_city'][city] = self.stats['by_city'].get(city, 0) + 1
        
        # Count by platform
        platform = getattr(spider, 'platform', 'unknown')
        self.stats['by_platform'][platform] = self.stats['by_platform'].get(platform, 0) + 1
        
        logging.info(f"Found PDF: {item['url']} for {city} ({platform})")
        return item
    
    def close_spider(self, spider):
        """Save results when spider finishes."""
        # Save detailed results
        with open('comprehensive_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Save statistics
        with open('scraper_stats.json', 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("COMPREHENSIVE SCRAPER TEST RESULTS")
        print("="*60)
        print(f"Total PDFs found: {self.stats['total_pdfs']}")
        print(f"Cities with results: {len(self.stats['by_city'])}")
        print(f"Platforms tested: {len(self.stats['by_platform'])}")
        
        print("\nResults by City:")
        for city, count in sorted(self.stats['by_city'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {city}: {count} PDFs")
        
        print("\nResults by Platform:")
        for platform, count in sorted(self.stats['by_platform'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {platform}: {count} PDFs")
        
        if self.stats['errors']:
            print(f"\nErrors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"  {error}")

def test_all_sites():
    """Test the enhanced scraper on all configured sites."""
    
    # Load configuration
    sites = load_config("scraper/sites.json")
    
    # Set up Scrapy settings
    settings = get_project_settings()
    settings.update({
        'FEEDS': {
            'comprehensive_results.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
                'overwrite': True,
            }
        },
        'LOG_LEVEL': 'INFO',
        'DOWNLOAD_DELAY': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': 1,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'ROBOTSTXT_OBEY': False,
        'CONCURRENT_REQUESTS': 1,  # Be respectful
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'ITEM_PIPELINES': {
            '__main__.ComprehensiveTestPipeline': 300,
        }
    })
    
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Add spiders for each site
    for site in sites:
        print(f"\nTesting {site.city}: {site.url}")
        
        # Create a custom spider class for this site
        class SiteSpecificSpider(EnhancedPdfSpider):
            def __init__(self, **kwargs):
                super().__init__(
                    start_url=site.url,
                    selectors=site.selectors,
                    city=site.city,
                    notes=site.notes,
                    **kwargs
                )
        
        process.crawl(SiteSpecificSpider)
    
    # Run all spiders
    print(f"\nStarting comprehensive test of {len(sites)} sites...")
    start_time = time.time()
    process.start()
    end_time = time.time()
    
    print(f"\nTest completed in {end_time - start_time:.2f} seconds")
    
    # Load and display final results
    try:
        with open('comprehensive_results.json', 'r') as f:
            results = json.load(f)
        
        print(f"\nFinal Results: {len(results)} PDFs found")
        
        # Group by city
        by_city = {}
        for item in results:
            city = item.get('city', 'unknown')
            by_city[city] = by_city.get(city, 0) + 1
        
        print("\nFinal Results by City:")
        for city, count in sorted(by_city.items(), key=lambda x: x[1], reverse=True):
            print(f"  {city}: {count} PDFs")
            
    except FileNotFoundError:
        print("No results file found - check scraper_test.log for details")

if __name__ == "__main__":
    test_all_sites() 