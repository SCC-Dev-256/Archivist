# PURPOSE: Test script to validate site configuration and connectivity
# DEPENDENCIES: config, requests
# MODIFICATION NOTES: v1.0 - Initial implementation

from __future__ import annotations

import requests
import json
from pathlib import Path
from typing import List, Dict, Any

from .config import load_config, SiteConfig


def test_site_connectivity(site: SiteConfig) -> Dict[str, Any]:
    """Test connectivity and basic structure of a site."""
    result = {
        "city": site.city,
        "url": site.url,
        "status": "unknown",
        "status_code": None,
        "content_length": 0,
        "pdf_links_found": 0,
        "errors": []
    }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; CityScraper/1.0)'
        }
        
        response = requests.get(site.url, headers=headers, timeout=10)
        result["status_code"] = response.status_code
        result["content_length"] = len(response.content)
        
        if response.status_code == 200:
            result["status"] = "success"
            
            # Check for PDF links
            content = response.text.lower()
            pdf_count = content.count('.pdf')
            result["pdf_links_found"] = pdf_count
            
            # Check for platform indicators
            if "civicengage" in content:
                result["platform_detected"] = "CivicEngage"
            elif "wordpress" in content:
                result["platform_detected"] = "WordPress"
            elif "drupal" in content:
                result["platform_detected"] = "Drupal"
            else:
                result["platform_detected"] = "Unknown"
                
        else:
            result["status"] = "error"
            result["errors"].append(f"HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["errors"].append("Request timeout")
    except requests.exceptions.ConnectionError:
        result["status"] = "connection_error"
        result["errors"].append("Connection error")
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
    
    return result


def test_all_sites(config_path: str | Path = "sites.json") -> List[Dict[str, Any]]:
    """Test all configured sites."""
    sites = load_config(config_path)
    results = []
    
    print(f"Testing {len(sites)} sites...")
    print("-" * 80)
    
    for site in sites:
        print(f"Testing {site.city}: {site.url}")
        result = test_site_connectivity(site)
        results.append(result)
        
        # Print result
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"  {status_icon} Status: {result['status']}")
        if result["status_code"]:
            print(f"    HTTP: {result['status_code']}")
        if result["pdf_links_found"] > 0:
            print(f"    PDF links found: {result['pdf_links_found']}")
        if result.get("platform_detected"):
            print(f"    Platform: {result['platform_detected']}")
        if result["errors"]:
            print(f"    Errors: {', '.join(result['errors'])}")
        print()
    
    return results


def generate_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a summary of test results."""
    summary = {
        "total_sites": len(results),
        "successful": 0,
        "failed": 0,
        "total_pdfs_found": 0,
        "platforms": {},
        "cities_by_status": {"success": [], "failed": []}
    }
    
    for result in results:
        if result["status"] == "success":
            summary["successful"] += 1
            summary["cities_by_status"]["success"].append(result["city"])
        else:
            summary["failed"] += 1
            summary["cities_by_status"]["failed"].append(result["city"])
        
        summary["total_pdfs_found"] += result["pdf_links_found"]
        
        platform = result.get("platform_detected", "Unknown")
        summary["platforms"][platform] = summary["platforms"].get(platform, 0) + 1
    
    return summary


def main():
    """Main test function."""
    print("Minnesota City Website Scraper - Configuration Test")
    print("=" * 60)
    
    # Test all sites
    results = test_all_sites()
    
    # Generate and print summary
    summary = generate_summary(results)
    
    print("SUMMARY")
    print("-" * 40)
    print(f"Total sites: {summary['total_sites']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Total PDF links found: {summary['total_pdfs_found']}")
    print()
    
    print("Platforms detected:")
    for platform, count in summary["platforms"].items():
        print(f"  {platform}: {count}")
    print()
    
    if summary["cities_by_status"]["failed"]:
        print("Failed cities:")
        for city in summary["cities_by_status"]["failed"]:
            print(f"  - {city}")
    
    # Save detailed results
    with open("test_results.json", "w") as f:
        json.dump({
            "results": results,
            "summary": summary
        }, f, indent=2)
    
    print(f"\nDetailed results saved to test_results.json")


if __name__ == "__main__":
    main() 