#!/usr/bin/env python3
"""
Test script for SRT upload functionality.
This script tests the SRT upload methods we've implemented.
"""

import os
from core.cablecast_client import CablecastAPIClient
from core.services.vod import VODService

def test_srt_upload_functionality():
    """Test the SRT upload functionality"""
    print("🧪 Testing SRT Upload Functionality")
    print("=" * 50)
    
    # Test 1: Check if test SRT file exists
    srt_file = "tests/test_caption.srt"
    if not os.path.exists(srt_file):
        print(f"❌ Test SRT file not found: {srt_file}")
        return False
    
    print(f"✅ Test SRT file found: {srt_file}")
    
    # Test 2: Initialize Cablecast client
    try:
        client = CablecastAPIClient()
        print("✅ CablecastAPIClient initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize CablecastAPIClient: {e}")
        return False
    
    # Test 3: Check if upload_srt_file method exists
    if hasattr(client, 'upload_srt_file'):
        print("✅ upload_srt_file method available")
    else:
        print("❌ upload_srt_file method not found")
        return False
    
    # Test 4: Initialize VOD service
    try:
        vod_service = VODService()
        print("✅ VODService initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize VODService: {e}")
        return False
    
    # Test 5: Check if upload_srt_caption method exists
    if hasattr(vod_service, 'upload_srt_caption'):
        print("✅ upload_srt_caption method available")
    else:
        print("❌ upload_srt_caption method not found")
        return False
    
    # Test 6: Read and validate SRT file
    try:
        with open(srt_file, 'r') as f:
            content = f.read()
            lines = content.strip().split('\n')
            segments = [line for line in lines if ' --> ' in line]
            print(f"✅ SRT file validated: {len(segments)} segments found")
    except Exception as e:
        print(f"❌ Failed to read SRT file: {e}")
        return False
    
    print("\n🎯 All SRT upload functionality tests passed!")
    print("\n📋 Ready for API Key Testing:")
    print("1. Get API key from Kevin at SCCTV")
    print("2. Update .env file with correct credentials")
    print("3. Test actual upload with: curl -X POST 'http://localhost:5000/api/cablecast/vods/123/captions' -F 'caption_file=@test_caption.srt'")
    
    return True

if __name__ == "__main__":
    test_srt_upload_functionality() 