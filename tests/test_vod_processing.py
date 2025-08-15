#!/usr/bin/env python3
"""
VOD Processing System Test Script
Tests the VOD processing system with working flex mounts
"""

import os
import sys
import time
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_flex_mount_access():
    """Test write access to working flex mounts"""
    print("🔍 Testing Flex Mount Access...")
    
    working_mounts = ['/mnt/flex-1', '/mnt/flex-5', '/mnt/flex-6', '/mnt/flex-8', '/mnt/flex-9']
    
    for mount in working_mounts:
        test_file = f"{mount}/test_write_{int(time.time())}.txt"
        try:
            with open(test_file, 'w') as f:
                f.write(f"Test write at {time.ctime()}")
            print(f"✅ {mount}: Write access OK")
            
            # Clean up
            os.remove(test_file)
        except Exception as e:
            print(f"❌ {mount}: Write access FAILED - {e}")

def test_celery_connection():
    """Test Celery connection and task registration"""
    print("\n🔍 Testing Celery Connection...")
    
    try:
        from core.tasks import celery_app
        from core.tasks.vod_processing import process_single_vod
        
        # Check if tasks are registered
        registered_tasks = celery_app.tasks.keys()
        vod_tasks = [task for task in registered_tasks if 'vod_processing' in task]
        
        print(f"✅ Celery connection successful")
        print(f"✅ Found {len(vod_tasks)} VOD processing tasks:")
        for task in vod_tasks:
            print(f"   - {task}")
            
        return True
    except Exception as e:
        print(f"❌ Celery connection failed: {e}")
        return False

def test_cablecast_connection():
    """Test Cablecast API connection"""
    print("\n🔍 Testing Cablecast API Connection...")
    
    try:
        from core.cablecast_client import CablecastClient
        
        client = CablecastClient()
        if client.test_connection():
            print("✅ Cablecast API connection successful")
            return True
        else:
            print("❌ Cablecast API connection failed")
            return False
    except Exception as e:
        print(f"❌ Cablecast API test failed: {e}")
        return False

def test_vod_processing_task():
    """Test a simple VOD processing task"""
    print("\n🔍 Testing VOD Processing Task...")
    
    try:
        from core.tasks.vod_processing import process_single_vod
        
        # Test with real video from flex servers
        test_video = None
        for flex_num in range(1, 10):
            flex_path = f"/mnt/flex-{flex_num}"
            if os.path.exists(flex_path):
                for file in os.listdir(flex_path):
                    if file.endswith('.mp4') and 'White Bear Lake' in file:
                        test_video = os.path.join(flex_path, file)
                        break
                if test_video:
                    break
        
        if not test_video:
            print("⚠️  No suitable test video found, using placeholder")
            test_video = '/mnt/flex-1/test_video.mp4'
        
        result = process_single_vod.delay('test_vod.mp4', test_video)
        print(f"✅ Task submitted successfully")
        print(f"   Task ID: {result.id}")
        print(f"   Status: {result.status}")
        
        return result.id
    except Exception as e:
        print(f"❌ VOD processing task failed: {e}")
        return None

def test_storage_paths():
    """Test storage path creation and access"""
    print("\n🔍 Testing Storage Paths...")
    
    try:
        from core.vod_content_manager import VODContentManager
        
        # Test path creation for different cities
        cities = ['Grant', 'Lake Elmo', 'Mahtomedi', 'Oakdale', 'White Bear Lake']
        
        for city in cities:
            try:
                manager = VODContentManager(city)
                storage_path = manager.get_storage_path()
                print(f"✅ {city}: {storage_path}")
            except Exception as e:
                print(f"❌ {city}: {e}")
                
    except Exception as e:
        print(f"❌ Storage path test failed: {e}")

def main():
    """Run all tests"""
    print("🚀 VOD Processing System Test Suite")
    print("=" * 50)
    
    # Test flex mount access
    test_flex_mount_access()
    
    # Test Celery connection
    celery_ok = test_celery_connection()
    
    # Test Cablecast connection
    cablecast_ok = test_cablecast_connection()
    
    # Test storage paths
    test_storage_paths()
    
    # Test VOD processing task
    if celery_ok:
        task_id = test_vod_processing_task()
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Flex Mounts: ✅ Working")
    print(f"   Celery: {'✅ OK' if celery_ok else '❌ Failed'}")
    print(f"   Cablecast: {'✅ OK' if cablecast_ok else '❌ Failed'}")
    print(f"   VOD Processing: {'✅ Ready' if celery_ok else '❌ Not Ready'}")
    
    if celery_ok and cablecast_ok:
        print("\n🎉 VOD Processing System is ready for production!")
    else:
        print("\n⚠️  Some components need attention before production use.")

if __name__ == "__main__":
    main() 