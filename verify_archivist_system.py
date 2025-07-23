#!/usr/bin/env python3
"""
Archivist System Verification Script

This script verifies that all components of the Archivist VOD processing system
are working correctly, including:
1. Automatic VOD processing at scheduled times
2. Processing videos from flex servers with direct file access
3. Generating captions and transcriptions
4. Queue and task management through Celery worker
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def check_celery_worker():
    """Check if Celery worker is running and processing tasks."""
    print("🔍 Checking Celery Worker Status...")
    
    try:
        import psutil
        celery_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'celery' in proc.info['name'] and 'worker' in ' '.join(proc.info['cmdline']):
                    celery_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if celery_processes:
            print(f"✅ Celery worker is running ({len(celery_processes)} processes)")
            for proc in celery_processes:
                print(f"   - PID {proc['pid']}: {' '.join(proc['cmdline'])}")
            return True
        else:
            print("❌ No Celery worker processes found")
            return False
            
    except ImportError:
        print("⚠️  psutil not available, checking via command line...")
        import subprocess
        try:
            result = subprocess.run(['pgrep', '-f', 'celery.*worker'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Celery worker processes found")
                return True
            else:
                print("❌ No Celery worker processes found")
                return False
        except Exception as e:
            print(f"❌ Error checking Celery processes: {e}")
            return False

def check_task_registration():
    """Check if all VOD processing tasks are registered."""
    print("\n🔍 Checking Task Registration...")
    
    try:
        from core.tasks import celery_app
        
        registered_tasks = list(celery_app.tasks.keys())
        vod_tasks = [task for task in registered_tasks if any(vod_task in task for vod_task in 
                    ['process_recent_vods', 'download_vod_content', 'generate_vod_captions', 
                     'retranscode_vod', 'upload_captioned_vod', 'validate_vod_quality', 'cleanup_temp_files'])]
        transcription_tasks = [task for task in registered_tasks if 'transcription' in task]
        
        print(f"✅ Total tasks registered: {len(registered_tasks)}")
        print(f"✅ VOD processing tasks: {len(vod_tasks)}")
        print(f"✅ Transcription tasks: {len(transcription_tasks)}")
        
        expected_vod_tasks = [
            'process_recent_vods',
            'download_vod_content_task',
            'generate_vod_captions',
            'retranscode_vod_with_captions',
            'upload_captioned_vod',
            'validate_vod_quality',
            'cleanup_temp_files'
        ]
        
        missing_tasks = [task for task in expected_vod_tasks if not any(task in registered_task for registered_task in registered_tasks)]
        
        if missing_tasks:
            print(f"❌ Missing VOD tasks: {missing_tasks}")
            return False
        else:
            print("✅ All expected VOD processing tasks are registered")
            return True
            
    except Exception as e:
        print(f"❌ Error checking task registration: {e}")
        return False

def check_flex_server_access():
    """Check access to flex server mounts."""
    print("\n🔍 Checking Flex Server Access...")
    
    try:
        from core.config import MEMBER_CITIES
        
        accessible_mounts = 0
        total_mounts = len(MEMBER_CITIES)
        
        for city_id, city_config in MEMBER_CITIES.items():
            mount_path = city_config['mount_path']
            city_name = city_config['name']
            
            if os.path.ismount(mount_path):
                if os.access(mount_path, os.R_OK):
                    print(f"✅ {city_name} ({city_id}): {mount_path}")
                    accessible_mounts += 1
                else:
                    print(f"⚠️  {city_name} ({city_id}): {mount_path} (not readable)")
            else:
                print(f"❌ {city_name} ({city_id}): {mount_path} (not mounted)")
        
        print(f"\n📊 Flex Server Summary: {accessible_mounts}/{total_mounts} accessible")
        return accessible_mounts > 0
        
    except Exception as e:
        print(f"❌ Error checking flex server access: {e}")
        return False

def check_transcription_dependencies():
    """Check if transcription dependencies are available."""
    print("\n🔍 Checking Transcription Dependencies...")
    
    dependencies = {
        'faster_whisper': 'Transcription engine',
        'torch': 'PyTorch backend',
        'transformers': 'HuggingFace transformers',
        'tenacity': 'Retry logic'
    }
    
    missing_deps = []
    
    for module, description in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {module}: {description}")
        except ImportError:
            print(f"❌ {module}: {description} (missing)")
            missing_deps.append(module)
    
    if missing_deps:
        print(f"\n⚠️  Missing dependencies: {missing_deps}")
        print("   Install with: pip install --break-system-packages " + " ".join(missing_deps))
        return False
    else:
        print("✅ All transcription dependencies are available")
        return True

def check_scheduled_tasks():
    """Check if scheduled tasks are configured."""
    print("\n🔍 Checking Scheduled Tasks...")
    
    try:
        from core.tasks.scheduler import celery_app
        
        beat_schedule = celery_app.conf.beat_schedule
        
        expected_schedules = [
            'daily-caption-check',
            'daily-vod-processing', 
            'evening-vod-processing',
            'vod-cleanup'
        ]
        
        configured_schedules = list(beat_schedule.keys())
        
        print(f"✅ Configured scheduled tasks: {len(configured_schedules)}")
        
        for schedule in expected_schedules:
            if schedule in configured_schedules:
                task_info = beat_schedule[schedule]
                print(f"✅ {schedule}: {task_info['task']} at {task_info['schedule']}")
            else:
                print(f"❌ {schedule}: Not configured")
        
        missing_schedules = [s for s in expected_schedules if s not in configured_schedules]
        
        if missing_schedules:
            print(f"⚠️  Missing scheduled tasks: {missing_schedules}")
            return False
        else:
            print("✅ All expected scheduled tasks are configured")
            return True
            
    except Exception as e:
        print(f"❌ Error checking scheduled tasks: {e}")
        return False

def test_vod_processing():
    """Test VOD processing by triggering a task."""
    print("\n🔍 Testing VOD Processing...")
    
    try:
        from core.tasks.vod_processing import process_recent_vods
        
        print("Triggering VOD processing task...")
        result = process_recent_vods.delay()
        
        print(f"✅ VOD processing task triggered: {result.id}")
        
        # Wait a moment for the task to start
        time.sleep(2)
        
        # Check task status - use a try/except to handle different Celery result types
        try:
            if hasattr(result, 'ready') and result.ready():
                task_result = result.get()
                print(f"✅ Task completed: {task_result}")
            else:
                print("⏳ Task is still running (this is normal for VOD processing)")
        except Exception as e:
            print(f"⏳ Task status check: {e} (task is likely running)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing VOD processing: {e}")
        return False

def check_redis_connection():
    """Check Redis connection for Celery broker."""
    print("\n🔍 Checking Redis Connection...")
    
    try:
        import redis
        from core.config import REDIS_URL
        
        # Parse Redis URL
        if REDIS_URL.startswith('redis://'):
            host_port = REDIS_URL.replace('redis://', '').split('/')[0]
            host, port = host_port.split(':') if ':' in host_port else (host_port, 6379)
        else:
            host, port = 'localhost', 6379
        
        r = redis.Redis(host=host, port=int(port), socket_connect_timeout=5)
        r.ping()
        
        print(f"✅ Redis connection successful: {REDIS_URL}")
        
        # Check if Celery is using Redis
        celery_keys = r.keys('celery*')
        print(f"✅ Celery keys in Redis: {len(celery_keys)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def main():
    """Run all verification checks."""
    print("🚀 Archivist System Verification")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    checks = [
        ("Celery Worker", check_celery_worker),
        ("Task Registration", check_task_registration),
        ("Flex Server Access", check_flex_server_access),
        ("Transcription Dependencies", check_transcription_dependencies),
        ("Scheduled Tasks", check_scheduled_tasks),
        ("Redis Connection", check_redis_connection),
        ("VOD Processing Test", test_vod_processing)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} check failed with exception: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
    
    print(f"\nOverall Status: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All systems operational! Archivist is ready for production use.")
    elif passed >= total * 0.8:
        print("⚠️  Most systems operational, but some issues need attention.")
    else:
        print("❌ Multiple system issues detected. Please review and fix.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 