#!/usr/bin/env python3
# PURPOSE: Focused test for CivicEngage sites only
# DEPENDENCIES: scrapy, config, enhanced_pdf_spider
# MODIFICATION NOTES: v1.0 - CivicEngage-specific testing

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

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_civicengage_sites():
    """Test only CivicEngage sites with enhanced features."""
    
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
            'civicengage_enhanced_results.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
                'overwrite': True,
            }
        },
        'LOG_LEVEL': 'INFO',
        'DOWNLOAD_DELAY': 3,  # Be more respectful
        'RANDOMIZE_DOWNLOAD_DELAY': 2,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'ROBOTSTXT_OBEY': False,
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DEPTH_LIMIT': 5,  # Allow deeper crawling
        'DEPTH_PRIORITY': 1,
    })
    
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Add spiders for each CivicEngage site
    for site in civicengage_sites:
        print(f"\nSetting up spider for {site.city}...")
        
        # Create a custom spider class for this site
        class CivicEngageSpider(EnhancedPdfSpider):
            def __init__(self, **kwargs):
                super().__init__(
                    start_url=site.url,
                    selectors=site.selectors,
                    city=site.city,
                    notes=site.notes,
                    **kwargs
                )
        
        process.crawl(CivicEngageSpider)
    
    # Run all spiders
    print(f"\nStarting focused CivicEngage test...")
    start_time = time.time()
    process.start()
    end_time = time.time()
    
    print(f"\nTest completed in {end_time - start_time:.2f} seconds")
    
    # Analyze results
    try:
        with open('civicengage_enhanced_results.json', 'r') as f:
            results = json.load(f)
        
        print(f"\nCivicEngage Results: {len(results)} PDFs found")
        
        # Group by city
        by_city = {}
        for item in results:
            city = item.get('city', 'unknown')
            by_city[city] = by_city.get(city, 0) + 1
        
        print("\nResults by City:")
        for city, count in sorted(by_city.items(), key=lambda x: x[1], reverse=True):
            print(f"  {city}: {count} PDFs")
            
        # Show sample URLs
        print("\nSample PDFs found:")
        for i, item in enumerate(results[:10]):
            print(f"  {i+1}. {item['url']}")
            
    except FileNotFoundError:
        print("No results file found")
    except json.JSONDecodeError as e:
        print(f"JSON error: {e}")
        # Try to fix the JSON
        import subprocess
        subprocess.run(['python3', 'fix_results.py', 'civicengage_enhanced_results.json'])

if __name__ == "__main__":
    test_civicengage_sites() 