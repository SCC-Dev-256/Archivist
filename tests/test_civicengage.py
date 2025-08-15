#!/usr/bin/env python3
# PURPOSE: Test CivicEngage sites with fixed spider
# DEPENDENCIES: scrapy, config
# MODIFICATION NOTES: v1.0 - Initial implementation

import json
import logging
from pathlib import Path

import pytest
pytestmark = [pytest.mark.scraper, pytest.mark.network, pytest.mark.slow]

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scraper.config import load_config, SiteConfig
from scraper.spiders.enhanced_pdf_spider import EnhancedPdfSpider

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_civicengage_sites():
    """Test only CivicEngage sites with the fixed spider."""
    
    # Load configuration
    sites = load_config("scraper/sites.json")
    
    # Filter for CivicEngage sites only
    civicengage_sites = [
        site for site in sites 
        if "CivicEngage" in site.notes
    ]
    
    print(f"Testing {len(civicengage_sites)} CivicEngage sites:")
    for site in civicengage_sites:
        print(f"  - {site.city}: {site.url}")
    
    # Set up Scrapy settings
    settings = get_project_settings()
    settings.update({
        'FEEDS': {
            'civicengage_results.json': {
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
        'COOKIES_ENABLED': True,
        'DOWNLOAD_TIMEOUT': 30,
        'HTTPERROR_ALLOWED_CODES': [404, 403, 500],  # Allow these error codes
    })
    
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Add spiders for each CivicEngage site
    for site in civicengage_sites:
        process.crawl(
            EnhancedPdfSpider,
            start_url=site.url,
            selectors=site.selectors,
            city=site.city,
            notes=site.notes
        )
    
    # Run the crawler
    process.start()
    
    # Check results
    if Path("civicengage_results.json").exists():
        with open("civicengage_results.json", "r") as f:
            results = json.load(f)
        print(f"\n✅ Found {len(results)} PDFs from CivicEngage sites")
        
        # Group by city
        by_city = {}
        for item in results:
            city = item.get('city', 'Unknown')
            if city not in by_city:
                by_city[city] = 0
            by_city[city] += 1
        
        for city, count in by_city.items():
            print(f"  {city}: {count} PDFs")
    else:
        print("\n❌ No results found")

if __name__ == "__main__":
    test_civicengage_sites() 