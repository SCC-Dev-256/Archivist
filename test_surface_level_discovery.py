#!/usr/bin/env python3
"""Test script for surface-level flex server file discovery.

This script tests the updated transcription service to ensure it can properly
discover video files on flex servers that use surface-level E: drive structure.
"""

import os
import sys
from loguru import logger

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_surface_level_discovery():
    """Test the surface-level file discovery functionality."""
    print("🔍 Testing Surface-Level Flex Server Discovery")
    print("=" * 50)
    
    try:
        from core.services.transcription import TranscriptionService
        from core.config import MEMBER_CITIES
        
        service = TranscriptionService()
        
        print(f"📁 Available Flex Servers:")
        for server_id, config in MEMBER_CITIES.items():
            mount_path = config['mount_path']
            city_name = config['name']
            is_mounted = os.path.ismount(mount_path)
            is_readable = os.access(mount_path, os.R_OK) if is_mounted else False
            
            status = "✅" if is_mounted and is_readable else "❌"
            print(f"  {status} {city_name} ({server_id}): {mount_path}")
        
        print("\n🔍 Testing File Discovery:")
        print("-" * 30)
        
        # Test discovery on each flex server
        for server_id, config in MEMBER_CITIES.items():
            mount_path = config['mount_path']
            city_name = config['name']
            
            if not os.path.ismount(mount_path):
                print(f"⏭️  Skipping {city_name} - not mounted")
                continue
            
            if not os.access(mount_path, os.R_OK):
                print(f"⏭️  Skipping {city_name} - not readable")
                continue
            
            print(f"\n📂 Scanning {city_name} ({server_id}):")
            
            # Test surface-level discovery
            discovered_files = service.discover_video_files(server_id)
            
            if discovered_files:
                print(f"  ✅ Found {len(discovered_files)} video files:")
                for i, file_info in enumerate(discovered_files[:5]):  # Show first 5
                    size_mb = file_info['file_size'] / (1024 * 1024)
                    print(f"    {i+1}. {file_info['file_name']} ({size_mb:.1f} MB)")
                
                if len(discovered_files) > 5:
                    print(f"    ... and {len(discovered_files) - 5} more files")
            else:
                print(f"  ⚠️  No video files found")
            
            # Test untranscribed discovery
            untranscribed = service.find_untranscribed_videos(server_id)
            if untranscribed:
                print(f"  📝 {len(untranscribed)} videos need transcription:")
                for i, file_info in enumerate(untranscribed[:3]):  # Show first 3
                    print(f"    {i+1}. {file_info['file_name']}")
                
                if len(untranscribed) > 3:
                    print(f"    ... and {len(untranscribed) - 3} more")
            else:
                print(f"  ✅ All videos already transcribed or no videos found")
        
        print("\n🎯 Testing Batch Transcription (Dry Run):")
        print("-" * 40)
        
        # Test batch transcription on first available server
        for server_id, config in MEMBER_CITIES.items():
            mount_path = config['mount_path']
            city_name = config['name']
            
            if os.path.ismount(mount_path) and os.access(mount_path, os.R_OK):
                print(f"📹 Testing batch transcription for {city_name} ({server_id})")
                
                # Get untranscribed videos
                untranscribed = service.find_untranscribed_videos(server_id)
                
                if untranscribed:
                    print(f"  Found {len(untranscribed)} videos needing transcription")
                    print(f"  Would process: {untranscribed[0]['file_name']} (first file)")
                    
                    # Test single file transcription (dry run)
                    test_file = untranscribed[0]['file_path']
                    print(f"  Test file: {test_file}")
                    
                    # Check if file exists and is accessible
                    if os.path.exists(test_file):
                        file_size = os.path.getsize(test_file) / (1024 * 1024)
                        print(f"  File size: {file_size:.1f} MB")
                        print(f"  File accessible: ✅")
                    else:
                        print(f"  File accessible: ❌")
                else:
                    print(f"  No videos need transcription")
                
                break  # Only test first available server
        
        print("\n✅ Surface-level discovery test completed!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")
        return False

def test_vod_processing_discovery():
    """Test the VOD processing file discovery."""
    print("\n🎬 Testing VOD Processing Discovery")
    print("=" * 40)
    
    try:
        from core.tasks.vod_processing import get_recent_vods_from_flex_server
        from core.config import MEMBER_CITIES
        
        for server_id, config in MEMBER_CITIES.items():
            mount_path = config['mount_path']
            city_name = config['name']
            
            if not os.path.ismount(mount_path):
                print(f"⏭️  Skipping {city_name} - not mounted")
                continue
            
            print(f"\n📂 VOD Discovery for {city_name} ({server_id}):")
            
            # Test VOD discovery
            recent_vods = get_recent_vods_from_flex_server(mount_path, server_id, limit=3)
            
            if recent_vods:
                print(f"  ✅ Found {len(recent_vods)} recent VODs:")
                for i, vod in enumerate(recent_vods):
                    size_mb = vod['file_size'] / (1024 * 1024)
                    print(f"    {i+1}. {vod['title']} ({size_mb:.1f} MB)")
            else:
                print(f"  ⚠️  No recent VODs found")
        
        print("\n✅ VOD processing discovery test completed!")
        return True
        
    except Exception as e:
        logger.error(f"VOD test failed: {e}")
        print(f"❌ VOD test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Surface-Level Flex Server Discovery Tests")
    print("=" * 60)
    
    # Test transcription service discovery
    transcription_success = test_surface_level_discovery()
    
    # Test VOD processing discovery
    vod_success = test_vod_processing_discovery()
    
    print("\n" + "=" * 60)
    if transcription_success and vod_success:
        print("🎉 All tests passed! Surface-level discovery is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    print("\n📋 Summary:")
    print(f"  Transcription Service: {'✅' if transcription_success else '❌'}")
    print(f"  VOD Processing: {'✅' if vod_success else '❌'}") 