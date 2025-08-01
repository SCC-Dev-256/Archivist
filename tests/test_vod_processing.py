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
    working_mounts = ['/mnt/flex-1', '/mnt/flex-5', '/mnt/flex-6', '/mnt/flex-8', '/mnt/flex-9']
    for mount in working_mounts:
        test_file = f"{mount}/test_write_{int(time.time())}.txt"
        try:
            with open(test_file, 'w') as f:
                f.write(f"Test write at {time.ctime()}")
            os.remove(test_file)
        except Exception as e:
            assert False, f"Write access failed for {mount}: {e}"

def test_celery_connection():
    """Test Celery connection and task registration"""
    from core.tasks import celery_app
    from core.tasks.vod_processing import process_single_vod
    registered_tasks = celery_app.tasks.keys()
    vod_tasks = [task for task in registered_tasks if 'vod_processing' in task]
    assert len(vod_tasks) > 0, "No VOD processing tasks registered in Celery."
    return True

def test_cablecast_connection():
    """Test Cablecast API connection"""
    from core.cablecast_client import CablecastClient
    client = CablecastClient()
    assert client.test_connection(), "Cablecast API connection failed."
    return True

def test_vod_processing_task():
    """Test a simple VOD processing task"""
    from core.tasks.vod_processing import process_single_vod
    result = process_single_vod.delay('test_vod.mp4', '/mnt/flex-1/test_video.mp4')
    assert hasattr(result, 'id'), "VOD processing task did not return a result ID."
    return result.id

def test_storage_paths():
    """Test storage path creation and access"""
    from core.vod_content_manager import VODContentManager
    cities = ['Grant', 'Lake Elmo', 'Mahtomedi', 'Oakdale', 'White Bear Lake']
    for city in cities:
        manager = VODContentManager(city)
        storage_path = manager.get_storage_path()
        assert os.path.exists(storage_path), f"Storage path does not exist for {city}: {storage_path}"

def main():
    """Run all tests"""
    test_flex_mount_access()
    celery_ok = test_celery_connection()
    cablecast_ok = test_cablecast_connection()
    test_storage_paths()
    if celery_ok:
        task_id = test_vod_processing_task()
    # Print summary for human readability
    print("\n📊 Test Summary:")
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