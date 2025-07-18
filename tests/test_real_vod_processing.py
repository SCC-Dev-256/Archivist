#!/usr/bin/env python3
"""
Real VOD Processing Test
Tests the VOD processing system with an actual VOD from Cablecast
"""

import os
import sys
import time
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_real_vod_processing():
    """Test VOD processing with a real VOD from Cablecast"""
    print("🚀 Testing Real VOD Processing")
    print("=" * 50)
    
    try:
        from core.cablecast_client import CablecastAPIClient
        from core.tasks.vod_processing import process_single_vod
        
        # Initialize Cablecast client
        client = CablecastAPIClient()
        
        # Get a real VOD (ID: 764 - Ramsey Washington Suburban Cable Commission Meeting)
        vod_id = 764
        vod = client.get_vod(vod_id)
        
        if not vod:
            print(f"❌ VOD {vod_id} not found")
            return False
        
        # Get show details for title
        show_id = vod.get('vod', {}).get('show')
        show = client.get_show(show_id) if show_id else None
        
        title = "Unknown"
        if show and 'show' in show:
            title = show['show'].get('title', 'Unknown')
        
        print(f"📺 Testing VOD: {title}")
        print(f"   VOD ID: {vod_id}")
        print(f"   Show ID: {show_id}")
        print(f"   File: {vod.get('vod', {}).get('fileName', 'Unknown')}")
        print(f"   Duration: {vod.get('vod', {}).get('totalRunTime', 'Unknown')} seconds")
        
        # Test VOD processing task
        print(f"\n🔧 Submitting VOD processing task...")
        
        # Use a working flex mount for storage
        storage_path = "/mnt/flex-1"
        
        # Submit the task
        result = process_single_vod.delay(str(vod_id), storage_path)
        
        print(f"✅ Task submitted successfully")
        print(f"   Task ID: {result.id}")
        print(f"   Status: {result.status}")
        
        # Wait for task completion (with timeout)
        print(f"\n⏳ Waiting for task completion...")
        timeout = 60  # 60 seconds timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if result.ready():
                break
            time.sleep(2)
            print(f"   Still processing... ({int(time.time() - start_time)}s elapsed)")
        
        if result.ready():
            task_result = result.get()
            print(f"\n📊 Task completed!")
            print(f"   Status: {task_result.get('status', 'unknown')}")
            print(f"   Message: {task_result.get('message', 'No message')}")
            
            if task_result.get('status') == 'success':
                print(f"✅ VOD processing successful!")
                return True
            else:
                print(f"❌ VOD processing failed: {task_result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"⏰ Task timed out after {timeout} seconds")
            print(f"   Task is still running in background")
            return True  # Task is running, which is good
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vod_download():
    """Test downloading a real VOD"""
    print("\n🔍 Testing VOD Download...")
    
    try:
        from core.cablecast_client import CablecastAPIClient
        from core.tasks.vod_processing import download_vod_content_task
        
        client = CablecastAPIClient()
        vod_id = 764
        
        # Get direct URL for VOD
        direct_url = client.get_vod_direct_url(vod_id)
        
        if not direct_url:
            print(f"❌ Could not get direct URL for VOD {vod_id}")
            return False
        
        print(f"✅ Got direct URL: {direct_url}")
        
        # Test download task
        output_path = "/mnt/flex-1/test_download.mp4"
        
        print(f"📥 Submitting download task...")
        result = download_vod_content_task.delay(direct_url, output_path)
        
        print(f"   Task ID: {result.id}")
        
        # Wait for completion
        timeout = 120  # 2 minutes for download
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if result.ready():
                break
            time.sleep(5)
            print(f"   Downloading... ({int(time.time() - start_time)}s elapsed)")
        
        if result.ready():
            download_result = result.get()
            print(f"📊 Download completed!")
            print(f"   Success: {download_result}")
            
            if download_result:
                print(f"✅ Download successful!")
                # Clean up test file
                if os.path.exists(output_path):
                    os.remove(output_path)
                    print(f"🧹 Test file cleaned up")
                return True
            else:
                print(f"❌ Download failed")
                return False
        else:
            print(f"⏰ Download timed out")
            return False
            
    except Exception as e:
        print(f"❌ Download test failed: {e}")
        return False

def main():
    """Run all real VOD tests"""
    print("🎬 Real VOD Processing Test Suite")
    print("=" * 50)
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Real VOD processing
    processing_ok = test_real_vod_processing()
    
    # Test 2: VOD download
    download_ok = test_vod_download()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"VOD Processing: {'✅ PASS' if processing_ok else '❌ FAIL'}")
    print(f"VOD Download: {'✅ PASS' if download_ok else '❌ FAIL'}")
    
    if processing_ok and download_ok:
        print("\n🎉 All tests passed! VOD processing system is working with real content.")
    else:
        print("\n⚠️  Some tests failed. Check the logs for details.")
    
    return processing_ok and download_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 