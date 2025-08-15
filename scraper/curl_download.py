#!/usr/bin/env python3
# PURPOSE: Download PDFs using curl subprocess (since curl works)
# DEPENDENCIES: subprocess, pathlib
# MODIFICATION NOTES: v1.0 - Use curl instead of requests

import subprocess
import json
from pathlib import Path
import time

def download_pdf_with_curl(url: str, output_path: Path) -> bool:
    """Download a PDF using curl subprocess (since curl works)."""
    try:
        print(f"🔍 Downloading: {url}")
        
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
        
        print(f"📤 Running: {' '.join(curl_cmd)}")
        
        # Run curl command
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=35)
        
        print(f"📥 Exit code: {result.returncode}")
        if result.stderr:
            print(f"📥 Stderr: {result.stderr}")
        
        if result.returncode != 0:
            print(f"   ❌ Curl failed with exit code {result.returncode}")
            return False
        
        # Check if file was created and has content
        if not output_path.exists():
            print(f"   ❌ File was not created")
            return False
        
        file_size = output_path.stat().st_size
        print(f"💾 File size: {file_size} bytes")
        
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

def test_curl_download():
    """Test curl-based download with a few PDFs."""
    print("🧪 Testing Curl-Based PDF Download")
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
        output_path = Path(f"curl_test_{i}.pdf")
        
        if download_pdf_with_curl(url, output_path):
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
        print(f"\n🎉 Curl download is working!")
        print(f"📁 Downloaded files:")
        for i in range(1, total_count + 1):
            test_file = Path(f"curl_test_{i}.pdf")
            if test_file.exists():
                size = test_file.stat().st_size
                print(f"   - {test_file.name}: {size} bytes")
        return True
    else:
        print(f"\n❌ Curl download also failed")
        return False

if __name__ == "__main__":
    test_curl_download() 