#!/usr/bin/env python3
"""
Test script to force VOD processing without pattern filtering.
This will process all videos found on flex servers regardless of title patterns.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.tasks import celery_app
from core.config import MEMBER_CITIES
from core.tasks.vod_processing import get_recent_vods_from_flex_server, process_single_vod
from loguru import logger

def test_force_processing():
    """Force process all videos found on flex servers."""
    print("🔍 Testing Force VOD Processing...")
    
    total_processed = 0
    
    for city_id, city_config in MEMBER_CITIES.items():
        city_name = city_config['name']
        mount_path = city_config['mount_path']
        
        print(f"\n📁 Checking {city_name} ({city_id}) at {mount_path}")
        
        # Check if mount is accessible
        if not os.path.ismount(mount_path):
            print(f"❌ Mount not available: {mount_path}")
            continue
        
        if not os.access(mount_path, os.R_OK):
            print(f"❌ Mount not readable: {mount_path}")
            continue
        
        # Get all videos (bypass pattern filtering)
        recent_vods = get_recent_vods_from_flex_server(mount_path, city_id, limit=10)
        
        if not recent_vods:
            print(f"❌ No videos found on {mount_path}")
            continue
        
        print(f"✅ Found {len(recent_vods)} videos on {mount_path}")
        
        # Process each video (skip pattern filtering)
        for i, vod in enumerate(recent_vods[:3]):  # Process up to 3 videos per city
            try:
                vod_id = vod.get('id', f"flex_{city_id}_{i}")
                vod_title = vod.get('title', 'Unknown')
                vod_path = vod.get('file_path', '')
                
                print(f"🎬 Processing: {vod_title}")
                print(f"   Path: {vod_path}")
                print(f"   Size: {vod.get('file_size', 0) / (1024*1024):.1f} MB")
                
                # Queue the processing task
                vod_result = process_single_vod.delay(vod_id, city_id, vod_path)
                
                print(f"✅ Queued task: {vod_result.id}")
                total_processed += 1
                
            except Exception as e:
                print(f"❌ Failed to queue {vod_title}: {e}")
    
    print(f"\n🎉 Total videos queued for processing: {total_processed}")
    return total_processed > 0

if __name__ == "__main__":
    success = test_force_processing()
    sys.exit(0 if success else 1) 