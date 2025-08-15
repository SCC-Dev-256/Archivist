# PURPOSE: Analyze scraping results and provide summary
# DEPENDENCIES: json, collections
# MODIFICATION NOTES: v1.0 - Initial implementation

import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
import re


def analyze_results(file_path: str = "results.json") -> dict:
    """Analyze scraping results and return summary statistics."""
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error reading {file_path}: {e}")
        return {}
    
    if not data:
        return {"error": "No data found"}
    
    # Basic stats
    total_pdfs = len(data)
    cities = Counter(item['city'] for item in data)
    
    # Analyze URLs
    domains = Counter()
    years = Counter()
    document_types = Counter()
    
    for item in data:
        url = item['url']
        
        # Extract domain
        domain = urlparse(url).netloc
        domains[domain] += 1
        
        # Extract year from URL
        year_match = re.search(r'/(20\d{2})/', url)
        if year_match:
            years[year_match.group(1)] += 1
        
        # Extract document type
        if 'agenda' in url.lower():
            document_types['agenda'] += 1
        elif 'minutes' in url.lower():
            document_types['minutes'] += 1
        elif 'packet' in url.lower():
            document_types['packet'] += 1
        else:
            document_types['other'] += 1
    
    # Find unique PDFs (remove duplicates)
    unique_urls = set(item['url'] for item in data)
    unique_pdfs = len(unique_urls)
    
    return {
        "total_pdfs": total_pdfs,
        "unique_pdfs": unique_pdfs,
        "duplicates": total_pdfs - unique_pdfs,
        "cities": dict(cities),
        "domains": dict(domains),
        "years": dict(years),
        "document_types": dict(document_types),
        "sample_urls": list(unique_urls)[:5]  # First 5 unique URLs
    }


def print_summary(summary: dict):
    """Print a formatted summary of the results."""
    
    print("=" * 60)
    print("MINNESOTA CITY WEBSITE SCRAPER - RESULTS SUMMARY")
    print("=" * 60)
    
    if "error" in summary:
        print(f"❌ {summary['error']}")
        return
    
    print(f"📊 Total PDFs Found: {summary['total_pdfs']}")
    print(f"🔗 Unique PDFs: {summary['unique_pdfs']}")
    print(f"🔄 Duplicates: {summary['duplicates']}")
    print()
    
    print("🏙️  Cities:")
    for city, count in summary['cities'].items():
        print(f"   {city}: {count} PDFs")
    print()
    
    print("🌐 Domains:")
    for domain, count in summary['domains'].items():
        print(f"   {domain}: {count} PDFs")
    print()
    
    print("📅 Years:")
    for year, count in sorted(summary['years'].items()):
        print(f"   {year}: {count} PDFs")
    print()
    
    print("📄 Document Types:")
    for doc_type, count in summary['document_types'].items():
        print(f"   {doc_type.title()}: {count} PDFs")
    print()
    
    print("🔗 Sample URLs:")
    for i, url in enumerate(summary['sample_urls'], 1):
        print(f"   {i}. {url}")
    print()


def main():
    """Main analysis function."""
    print("Analyzing scraping results...")
    
    summary = analyze_results()
    print_summary(summary)
    
    # Save detailed analysis
    with open("scraping_analysis.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print("📁 Detailed analysis saved to scraping_analysis.json")


if __name__ == "__main__":
    main() 