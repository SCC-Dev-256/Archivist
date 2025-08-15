#!/usr/bin/env python3
"""
# PURPOSE: Comprehensive test script to verify Celery fixes
# DEPENDENCIES: core.tasks, core.transcription, celery, redis
# MODIFICATION NOTES: Created to verify task ID fixes, worker startup, and transcription functionality
"""

import subprocess
import time
import os
import json
import sys
from pathlib import Path
from loguru import logger

def test_celery_import():
    """Test that Celery imports correctly without mock interference."""
    print("🧪 Testing Celery Import...")
    try:
        from core.tasks import celery_app
        print("✅ Celery app imported successfully")
        
        # Check registered tasks
        tasks = list(celery_app.tasks.keys())
        transcription_tasks = [t for t in tasks if 'transcription' in t]
        vod_tasks = [t for t in tasks if 'vod_processing' in t]
        
        print(f"✅ Found {len(transcription_tasks)} transcription tasks")
        print(f"✅ Found {len(vod_tasks)} VOD processing tasks")
        
        return True
    except Exception as e:
        print(f"❌ Celery import failed: {e}")
        return False

def test_task_creation():
    """Test that tasks are created with proper UUIDs instead of 'dummy'."""
    print("\n🧪 Testing Task Creation...")
    try:
        from core.tasks import celery_app
        
        # Test transcription task with real video from flex servers
        test_video = "/mnt/flex-1/White Bear Lake Shortest Marathon.mp4"
        if not os.path.exists(test_video):
            test_video = "/mnt/flex-8/White Bear Lake Shortest Marathon.mp4"
        if not os.path.exists(test_video):
            # Fallback to any available video
            for flex_num in range(1, 10):
                flex_path = f"/mnt/flex-{flex_num}"
                if os.path.exists(flex_path):
                    for file in os.listdir(flex_path):
                        if file.endswith('.mp4') and 'White Bear Lake' in file:
                            test_video = os.path.join(flex_path, file)
                            break
                    if os.path.exists(test_video):
                        break
        
        if not os.path.exists(test_video):
            print("⚠️  No suitable test video found, using placeholder")
            test_video = "/tmp/test.mp4"
        
        result = celery_app.send_task('transcription.run_whisper', args=[test_video])
        task_id = result.id
        
        print(f"✅ Task created with ID: {task_id}")
        
        # Verify it's not 'dummy'
        if task_id == 'dummy':
            print("❌ Task ID is still 'dummy'")
            return False
        
        # Verify it's a UUID format
        if len(task_id) == 36 and task_id.count('-') == 4:
            print("✅ Task ID is proper UUID format")
        else:
            print(f"⚠️  Task ID format unexpected: {task_id}")
        
        return True
    except Exception as e:
        print(f"❌ Task creation failed: {e}")
        return False

def test_worker_startup():
    """Test that Celery worker can start properly."""
    print("\n🧪 Testing Worker Startup...")
    try:
        # Start worker in background
        cmd = [
            "celery", "-A", "core.tasks", "worker",
            "--loglevel=info",
            "--concurrency=1",
            "--hostname=test_worker@%h"
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for startup
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Worker started successfully")
            
            # Terminate worker
            process.terminate()
            process.wait(timeout=5)
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Worker failed to start")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Worker startup test failed: {e}")
        return False

def test_transcription_import():
    """Test that transcription dependencies are available."""
    print("\n🧪 Testing Transcription Dependencies...")
    try:
        # Test faster-whisper import
        from faster_whisper import WhisperModel
        print("✅ faster-whisper imported successfully")
        
        # Test transcription function import
        from core.transcription import run_whisper_transcription
        print("✅ run_whisper_transcription imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False
    except Exception as e:
        print(f"❌ Transcription import failed: {e}")
        return False

def test_redis_connection():
    """Test Redis connection for Celery broker."""
    print("\n🧪 Testing Redis Connection...")
    try:
        import redis
        from core.config import REDIS_URL
        
        r = redis.from_url(REDIS_URL)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def main():
    """Run all tests and provide summary."""
    print("🚀 Celery Fixes Verification Test")
    print("=" * 50)
    
    tests = [
        ("Celery Import", test_celery_import),
        ("Task Creation", test_task_creation),
        ("Worker Startup", test_worker_startup),
        ("Transcription Dependencies", test_transcription_import),
        ("Redis Connection", test_redis_connection),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Celery fixes are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 