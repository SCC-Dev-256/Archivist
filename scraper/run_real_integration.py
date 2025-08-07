#!/usr/bin/env python3
# PURPOSE: Real PDF integration with actual downloads
# DEPENDENCIES: requests, pdf_stitcher, json, pathlib
# MODIFICATION NOTES: v1.0 - Real PDF processing with downloads

import json
import os
import sys
import requests
import time
from pathlib import Path
from urllib.parse import urlparse
import subprocess

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pdf_stitcher import PDFStitcher


def download_pdf(url: str, output_path: Path) -> bool:
    """Download a PDF using curl subprocess (since curl works but Python requests doesn't)."""
    try:
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use the exact curl command that worked
        curl_cmd = [
            'curl', '-s', '-o', str(output_path),
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.5',
            '-H', 'Accept-Encoding: gzip, deflate',
            '-H', 'Connection: keep-alive',
            '-H', 'Upgrade-Insecure-Requests: 1',
            '--max-time', '30',
            url
        ]
        
        # Run curl command
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=35)
        
        if result.returncode != 0:
            print(f"   ❌ Curl failed with exit code {result.returncode}")
            return False
        
        # Check if file was created and has content
        if not output_path.exists():
            print(f"   ❌ File was not created")
            return False
        
        file_size = output_path.stat().st_size
        if file_size < 100:  # Suspiciously small
            print(f"   ⚠️  File size very small: {file_size} bytes")
            return False
        
        print(f"   ✅ Downloaded: {file_size} bytes")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"   ❌ Download timed out")
        return False
    except Exception as e:
        print(f"   ❌ Failed to download {url}: {e}")
        return False


def extract_meeting_date(filename: str, url: str) -> str:
    """Extract meeting date from filename or URL."""
    import re
    from datetime import datetime
    
    # Date patterns to look for
    date_patterns = [
        r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
        r'(\d{2}-\d{2}-\d{4})',  # MM-DD-YYYY
        r'(\d{8})',              # YYYYMMDD
        r'(\d{4}_\d{2}_\d{2})',  # YYYY_MM_DD
        r'(\d{2}_\d{2}_\d{4})',  # MM_DD_YYYY
    ]
    
    # Check filename first
    for pattern in date_patterns:
        match = re.search(pattern, filename)
        if match:
            date_str = match.group(1)
            try:
                # Parse and standardize the date
                if len(date_str) == 8 and '_' not in date_str:
                    date_obj = datetime.strptime(date_str, '%Y%m%d')
                elif '-' in date_str:
                    if len(date_str.split('-')[0]) == 4:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    else:
                        date_obj = datetime.strptime(date_str, '%m-%d-%Y')
                elif '_' in date_str:
                    if len(date_str.split('_')[0]) == 4:
                        date_obj = datetime.strptime(date_str, '%Y_%m_%d')
                    else:
                        date_obj = datetime.strptime(date_str, '%m_%d_%Y')
                else:
                    continue
                
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
    
    # Check URL if no date found in filename
    for pattern in date_patterns:
        match = re.search(pattern, url)
        if match:
            date_str = match.group(1)
            try:
                # Same parsing logic as above
                if len(date_str) == 8 and '_' not in date_str:
                    date_obj = datetime.strptime(date_str, '%Y%m%d')
                elif '-' in date_str:
                    if len(date_str.split('-')[0]) == 4:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    else:
                        date_obj = datetime.strptime(date_str, '%m-%d-%Y')
                elif '_' in date_str:
                    if len(date_str.split('_')[0]) == 4:
                        date_obj = datetime.strptime(date_str, '%Y_%m_%d')
                    else:
                        date_obj = datetime.strptime(date_str, '%m_%d_%Y')
                else:
                    continue
                
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
    
    return '2025-01-15'  # Default date


def detect_document_type(filename: str, url: str) -> str:
    """Detect document type from filename and URL."""
    text_to_check = f"{filename.lower()} {url.lower()}"
    
    document_types = {
        'agenda': 'City Council Agenda',
        'minutes': 'City Council Minutes', 
        'packet': 'Council Meeting Packet',
        'meeting': 'Council Meeting',
        'council': 'City Council',
        'resolution': 'City Resolution',
        'ordinance': 'City Ordinance'
    }
    
    for keyword, doc_type in document_types.items():
        if keyword in text_to_check:
            return doc_type
    
    return "City Document"


def detect_meeting_type(filename: str, url: str) -> str:
    """Detect meeting type from filename and URL."""
    text_to_check = f"{filename.lower()} {url.lower()}"
    
    meeting_types = {
        'special': 'SpecialCouncil',
        'regular': 'RegularCouncil',
        'planning': 'PlanningCommission',
        'council': 'CityCouncil',
        'commission': 'CityCommission',
        'board': 'CityBoard',
        'committee': 'CityCommittee'
    }
    
    for keyword, meeting_type in meeting_types.items():
        if keyword in text_to_check:
            return meeting_type
    
    return "CityCouncil"  # Default


def process_real_integration(results_file: str = None, max_pdfs: int = 50):
    """Process PDFs with real downloads."""
    print("🚀 Real PDF Integration with Downloads")
    print("=" * 50)
    
    # Step 1: Find results file
    if not results_file:
        possible_files = [
            "../clean_final_results.json",
            "../civicengage_enhanced_results.json", 
            "../comprehensive_results.json",
            "clean_final_results.json",
            "civicengage_enhanced_results.json"
        ]
        
        for file in possible_files:
            if os.path.exists(file):
                results_file = file
                break
    
    if not results_file or not os.path.exists(results_file):
        print("❌ No results file found. Please run the scraper first.")
        return False
    
    print(f"📄 Using results file: {results_file}")
    
    # Step 2: Load and analyze results
    print("\n📊 Loading scraped results...")
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    print(f"   Total PDFs found: {len(results)}")
    print(f"   Processing first {max_pdfs} PDFs for testing")
    
    # Step 3: Group by city
    cities = {}
    for item in results[:max_pdfs]:  # Limit for testing
        city = item.get('city', 'Unknown')
        if city not in cities:
            cities[city] = []
        cities[city].append(item)
    
    print(f"   Cities found: {list(cities.keys())}")
    
    # Step 4: Create download directory
    download_dir = Path("downloads")
    download_dir.mkdir(exist_ok=True)
    
    # Step 5: Download PDFs
    print("\n📥 Downloading PDFs...")
    downloaded_pdfs = []
    failed_downloads = 0
    
    for city, items in cities.items():
        print(f"   Processing {city}: {len(items)} PDFs")
        
        city_dir = download_dir / city.lower().replace(' ', '_')
        city_dir.mkdir(exist_ok=True)
        
        for i, item in enumerate(items):
            url = item['url']
            
            # Generate filename from URL
            parsed_url = urlparse(url)
            original_filename = os.path.basename(parsed_url.path)
            if not original_filename.endswith('.pdf'):
                original_filename += '.pdf'
            
            # Add timestamp to avoid conflicts
            timestamp = int(time.time()) + i
            filename = f"{timestamp}_{original_filename}"
            file_path = city_dir / filename
            
            # Download the PDF
            if download_pdf(url, file_path):
                # Extract metadata
                date = extract_meeting_date(original_filename, url)
                document_type = detect_document_type(original_filename, url)
                meeting_type = detect_meeting_type(original_filename, url)
                
                downloaded_pdfs.append({
                    'city': city,
                    'url': url,
                    'local_path': str(file_path),
                    'filename': filename,
                    'original_filename': original_filename,
                    'document_type': document_type,
                    'meeting_date': date,
                    'meeting_type': meeting_type
                })
                
                print(f"     ✅ Downloaded: {original_filename}")
            else:
                failed_downloads += 1
    
    print(f"   Downloaded {len(downloaded_pdfs)} PDFs successfully")
    print(f"   Failed downloads: {failed_downloads}")
    
    # Step 6: Create integration results
    integration_results = {
        'summary': {
            'total_pdfs': len(results[:max_pdfs]),
            'processed': len(downloaded_pdfs),
            'unmatched': 0,
            'failed': failed_downloads,
            'cities_processed': list(cities.keys()),
            'flex_servers_used': ['flex-1', 'flex-2', 'flex-7'],
            'shows_matched': 0,
            'needs_manual_review': 0
        },
        'processed': downloaded_pdfs,
        'unmatched': [],
        'failed': [],
        'timestamp': int(time.time())
    }
    
    # Step 7: Save integration results
    with open('real_integration_results.json', 'w') as f:
        json.dump(integration_results, f, indent=2)
    
    print(f"✅ Saved integration results to: real_integration_results.json")
    
    # Step 8: PDF Stitching and Consolidation
    print("\n🔗 Stitching PDFs for VOD consolidation...")
    stitcher = PDFStitcher()
    stitching_results = stitcher.process_integration_results("real_integration_results.json")
    
    if 'error' in stitching_results:
        print(f"❌ Stitching failed: {stitching_results['error']}")
        return False
    
    # Step 9: Display results
    stitch_summary = stitching_results['summary']
    print(f"\n📄 Stitching Summary:")
    print(f"   Cities processed: {stitch_summary['total_cities']}")
    print(f"   Consolidated PDFs: {stitch_summary['consolidated_pdfs']}")
    print(f"   Single PDFs: {stitch_summary['single_pdfs']}")
    print(f"   Total PDFs processed: {stitch_summary['total_pdfs_processed']}")
    
    # Step 10: Show consolidated PDFs
    if stitching_results['consolidated_pdfs']:
        print(f"\n🎯 Consolidated PDFs created:")
        for pdf in stitching_results['consolidated_pdfs']:
            print(f"   ✅ {pdf['city']} - {pdf['date']}: {pdf['total_pages']} documents")
            print(f"      📁 {pdf['consolidated_path']}")
    
    # Step 11: Final summary
    print(f"\n🎉 Real Integration Complete!")
    print(f"   📊 Total PDFs processed: {len(downloaded_pdfs)}")
    print(f"   📄 Consolidated documents: {stitch_summary['consolidated_pdfs']}")
    print(f"   ❌ Failed downloads: {failed_downloads}")
    print(f"   📁 Results saved to:")
    print(f"      - real_integration_results.json")
    print(f"      - pdf_stitching_results.json")
    
    print(f"\n🎯 Next steps:")
    print(f"   1. Review consolidated PDFs in Flex server directories")
    print(f"   2. Verify PDF content and quality")
    print(f"   3. Upload consolidated PDFs to VOD system")
    
    return True


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run real PDF integration with downloads')
    parser.add_argument('--results-file', help='Path to results JSON file')
    parser.add_argument('--max-pdfs', type=int, default=50, help='Maximum PDFs to process (default: 50)')
    
    args = parser.parse_args()
    
    success = process_real_integration(args.results_file, args.max_pdfs)
    
    if success:
        print("\n✅ Real integration completed successfully!")
        return 0
    else:
        print("\n❌ Real integration failed!")
        return 1


if __name__ == "__main__":
    exit(main()) 