#!/usr/bin/env python3
# PURPOSE: Test PDF download function with fixed headers
# DEPENDENCIES: requests, pathlib
# MODIFICATION NOTES: v1.0 - Test download function only

import requests
from pathlib import Path
import time

def test_download_pdf(url: str, output_path: Path) -> bool:
    """Test download a PDF from URL with proper headers."""
    try:
        print(f"🔍 Testing download: {url}")
        
        # Use the exact headers that worked with curl
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        print(f"📤 Sending request with headers: {headers}")
        
        response = requests.get(url, stream=True, timeout=30, headers=headers)
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response headers: {dict(response.headers)}")
        
        response.raise_for_status()
        
        # Check if it's actually a PDF
        content_type = response.headers.get('content-type', '').lower()
        print(f"📄 Content-Type: {content_type}")
        
        if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
            print(f"   ⚠️  Content-Type: {content_type} - may not be a PDF")
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Verify file size
        file_size = output_path.stat().st_size
        print(f"💾 File size: {file_size} bytes")
        
        if file_size < 100:  # Suspiciously small
            print(f"   ⚠️  File size very small: {file_size} bytes")
            return False
        
        print(f"   ✅ Downloaded: {file_size} bytes")
        return True
        
    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP {e.response.status_code}: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Failed to download {url}: {e}")
        return False

def main():
    """Test download function with a few PDFs."""
    print("🧪 Testing PDF Download Function")
    print("=" * 50)
    
    # Test URLs from our results
    test_urls = [
        "https://cityofbirchwood.com/wp-content/uploads/2025/07/July-22-2025-Special-Council-Agenda.pdf",
        "https://cityofbirchwood.com/wp-content/uploads/2025/07/20250714-Council-Agenda-1.pdf",
        "https://cityofbirchwood.com/wp-content/uploads/2025/07/July-8-City-Council-Meeting-Packet.pdf"
    ]
    
    success_count = 0
    total_count = len(test_urls)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n📄 Test {i}/{total_count}")
        output_path = Path(f"test_download_{i}.pdf")
        
        if test_download_pdf(url, output_path):
            success_count += 1
            print(f"✅ SUCCESS: Downloaded {output_path}")
        else:
            print(f"❌ FAILED: Could not download {url}")
        
        # Small delay between requests
        time.sleep(1)
    
    print(f"\n🎯 Test Results:")
    print(f"   ✅ Successful: {success_count}/{total_count}")
    print(f"   ❌ Failed: {total_count - success_count}/{total_count}")
    
    if success_count > 0:
        print(f"\n🎉 Download function is working!")
        print(f"📁 Downloaded files:")
        for i in range(1, total_count + 1):
            test_file = Path(f"test_download_{i}.pdf")
            if test_file.exists():
                size = test_file.stat().st_size
                print(f"   - {test_file.name}: {size} bytes")
    else:
        print(f"\n❌ Download function still has issues")
        print(f"💡 Need to investigate further")

if __name__ == "__main__":
    main() 