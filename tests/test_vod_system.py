#!/usr/bin/env python3
"""
Comprehensive VOD Processing System Test

This script tests all components of the VOD processing system:
- Celery task registration
- Task queue integration
- GUI interface availability
- Scheduled task configuration
- VOD processing pipeline
"""

import os
import sys
import time
import requests
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_celery_tasks():
    """Test Celery task registration and functionality."""
    print("\n🔍 Testing Celery Tasks...")
    
    try:
        from core.tasks import celery_app
        
        # Check if tasks are registered
        registered_tasks = celery_app.tasks.keys()
        vod_tasks = [task for task in registered_tasks if 'vod_processing' in task]
        
        expected_tasks = [
            'vod_processing.process_recent_vods',
            'vod_processing.process_single_vod',
            'vod_processing.download_vod_content',
            'vod_processing.generate_vod_captions',
            'vod_processing.retranscode_vod_with_captions',
            'vod_processing.upload_captioned_vod',
            'vod_processing.validate_vod_quality',
            'vod_processing.cleanup_temp_files'
        ]
        
        missing_tasks = [task for task in expected_tasks if task not in vod_tasks]
        
        if missing_tasks:
            print(f"❌ Missing tasks: {missing_tasks}")
            return False
        
        print(f"✅ All {len(vod_tasks)} VOD processing tasks registered")
        
        # Test task triggering
        from core.tasks.vod_processing import cleanup_temp_files
        test_task = cleanup_temp_files.delay()
        print(f"✅ Test task triggered: {test_task.id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Celery task test failed: {e}")
        return False

def test_task_queue():
    """Test task queue integration."""
    print("\n🔍 Testing Task Queue Integration...")
    
    try:
        from core.task_queue import QueueManager
        
        queue_manager = QueueManager()
        
        # Test queue operations
        jobs = queue_manager.get_all_jobs()
        print(f"✅ Task queue accessible: {len(jobs)} jobs")
        
        # Test job creation
        test_job_id = queue_manager.enqueue_transcription("test_video.mp4")
        print(f"✅ Test job created: {test_job_id}")
        
        # Test job status
        status = queue_manager.get_job_status(test_job_id)
        print(f"✅ Job status retrieved: {status['status']}")
        
        # Clean up test job
        queue_manager.remove_job(test_job_id)
        print("✅ Test job cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Task queue test failed: {e}")
        return False

def test_gui_interfaces():
    """Test GUI interface availability."""
    print("\n🔍 Testing GUI Interfaces...")
    
    interfaces = [
        ("Admin UI", "http://localhost:8080"),
        ("Monitoring Dashboard", "http://localhost:5051"),
        ("Admin Status API", "http://localhost:8080/api/admin/status"),
        ("Unified Queue API", "http://localhost:8080/api/unified-queue/tasks/"),
        ("API Documentation", "http://localhost:8080/api/docs")
    ]
    
    all_working = True
    
    for name, url in interfaces:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: {url}")
            else:
                print(f"⚠️ {name}: {url} (Status: {response.status_code})")
                all_working = False
        except Exception as e:
            print(f"❌ {name}: {url} - {e}")
            all_working = False
    
    return all_working

def test_scheduled_tasks():
    """Test scheduled task configuration."""
    print("\n🔍 Testing Scheduled Tasks...")
    
    try:
        from core.tasks.scheduler import celery_app
        
        # Check beat schedule
        beat_schedule = celery_app.conf.beat_schedule
        
        expected_schedules = [
            'daily-caption-check',
            'daily-vod-processing',
            'evening-vod-processing',
            'vod-cleanup'
        ]
        
        missing_schedules = [schedule for schedule in expected_schedules if schedule not in beat_schedule]
        
        if missing_schedules:
            print(f"❌ Missing scheduled tasks: {missing_schedules}")
            return False
        
        print("✅ All scheduled tasks configured:")
        for schedule_name, schedule_config in beat_schedule.items():
            print(f"   - {schedule_name}: {schedule_config['schedule']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Scheduled task test failed: {e}")
        return False

def test_vod_processing_pipeline():
    """Test VOD processing pipeline components."""
    print("\n🔍 Testing VOD Processing Pipeline...")
    
    try:
        from core.tasks.vod_processing import (
            process_recent_vods,
            process_single_vod,
            download_vod_content_task,
            generate_vod_captions,
            retranscode_vod_with_captions,
            upload_captioned_vod,
            validate_vod_quality,
            cleanup_temp_files
        )
        
        print("✅ All VOD processing functions imported successfully")
        
        # Test task registration
        from core.tasks import celery_app
        registered_tasks = celery_app.tasks.keys()
        
        pipeline_tasks = [
            'vod_processing.process_recent_vods',
            'vod_processing.process_single_vod',
            'vod_processing.download_vod_content',
            'vod_processing.generate_vod_captions',
            'vod_processing.retranscode_vod_with_captions',
            'vod_processing.upload_captioned_vod',
            'vod_processing.validate_vod_quality',
            'vod_processing.cleanup_temp_files'
        ]
        
        for task in pipeline_tasks:
            if task in registered_tasks:
                print(f"✅ {task}")
            else:
                print(f"❌ {task} - Not registered")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ VOD processing pipeline test failed: {e}")
        return False

def test_system_resources():
    """Test system resources and dependencies."""
    print("\n🔍 Testing System Resources...")
    
    try:
        # Test Redis connection
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful")
        
        # Test PostgreSQL connection
        from core.config import DATABASE_URL
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        print("✅ PostgreSQL connection successful")
        
        # Test flex mounts
        flex_mounts = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4', '/mnt/flex-5']
        for mount in flex_mounts:
            if os.path.ismount(mount):
                print(f"✅ Flex mount {mount} available")
            else:
                print(f"⚠️ Flex mount {mount} not available")
        
        # Test Celery workers
        from core.tasks import celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            print(f"✅ Celery workers active: {len(stats)}")
        else:
            print("⚠️ No Celery workers detected")
        
        return True
        
    except Exception as e:
        print(f"❌ System resources test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints functionality."""
    print("\n🔍 Testing API Endpoints...")
    
    endpoints = [
        ("Admin Status", "http://localhost:8080/api/admin/status", "GET"),
        ("Cities", "http://localhost:8080/api/admin/cities", "GET"),
        ("Queue Summary", "http://localhost:8080/api/admin/queue/summary", "GET"),
        ("Celery Summary", "http://localhost:8080/api/admin/celery/summary", "GET"),
        ("Unified Tasks", "http://localhost:8080/api/unified-queue/tasks/", "GET"),
        ("Unified Summary", "http://localhost:8080/api/unified-queue/tasks/summary", "GET"),
        ("Unified Workers", "http://localhost:8080/api/unified-queue/workers/", "GET")
    ]
    
    all_working = True
    
    for name, url, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, timeout=5)
                
            if response.status_code == 200:
                print(f"✅ {name}: {url}")
            else:
                print(f"⚠️ {name}: {url} (Status: {response.status_code})")
                all_working = False
        except Exception as e:
            print(f"❌ {name}: {url} - {e}")
            all_working = False
    
    return all_working

def main():
    """Run all tests."""
    print("🚀 Comprehensive VOD Processing System Test")
    print("=" * 60)
    
    tests = [
        ("Celery Tasks", test_celery_tasks),
        ("Task Queue", test_task_queue),
        ("GUI Interfaces", test_gui_interfaces),
        ("Scheduled Tasks", test_scheduled_tasks),
        ("VOD Processing Pipeline", test_vod_processing_pipeline),
        ("System Resources", test_system_resources),
        ("API Endpoints", test_api_endpoints)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! VOD processing system is ready.")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Please check the system configuration.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 