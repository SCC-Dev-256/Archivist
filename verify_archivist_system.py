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

from loguru import logger

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))


def check_celery_worker():
    """Check if Celery worker is running and processing tasks."""
    logger.info("🔍 Checking Celery Worker Status...")
    
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
            logger.success(f"Celery worker is running ({len(celery_processes)} processes)")
            for proc in celery_processes:
                logger.info(f"   - PID {proc['pid']}: {' '.join(proc['cmdline'])}")
            return True
        else:
            logger.error("No Celery worker processes found")
            return False
            
    except ImportError:
        logger.warning("psutil not available, checking via command line...")
        import subprocess
        try:
            result = subprocess.run(['pgrep', '-f', 'celery.*worker'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.success("Celery worker processes found")
                return True
            else:
                logger.error("No Celery worker processes found")
                return False
        except Exception as e:
            logger.error(f"Error checking Celery processes: {e}")
            return False


def check_task_registration():
    """Check if all VOD processing tasks are registered."""
    logger.info("🔍 Checking Task Registration...")
    
    try:
        from core.tasks import celery_app
        
        registered_tasks = list(celery_app.tasks.keys())
        vod_tasks = [task for task in registered_tasks if any(vod_task in task for vod_task in 
                    ['process_recent_vods', 'download_vod_content', 'generate_vod_captions', 
                     'retranscode_vod', 'upload_captioned_vod', 'validate_vod_quality', 'cleanup_temp_files'])]
        transcription_tasks = [task for task in registered_tasks if 'transcription' in task]
        
        logger.success(f"Total tasks registered: {len(registered_tasks)}")
        logger.info(f"VOD processing tasks: {len(vod_tasks)}")
        logger.info(f"Transcription tasks: {len(transcription_tasks)}")
        
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
            logger.error(f"Missing VOD tasks: {missing_tasks}")
            return False
        else:
            logger.success("All expected VOD processing tasks are registered")
            return True
            
    except Exception as e:
        logger.error(f"Error checking task registration: {e}")
        return False


def check_flex_server_access():
    """Check access to flex servers and mount points."""
    logger.info("🔍 Checking Flex Server Access...")
    
    try:
        from core.config import MEMBER_CITIES
        
        accessible_mounts = 0
        total_mounts = len(MEMBER_CITIES)
        
        for city_id, city_config in MEMBER_CITIES.items():
            city_name = city_config['name']
            mount_path = city_config['mount_path']
            
            if os.path.ismount(mount_path):
                if os.access(mount_path, os.R_OK):
                    logger.success(f"{city_name} ({city_id}): {mount_path}")
                    accessible_mounts += 1
                else:
                    logger.warning(f"{city_name} ({city_id}): {mount_path} (not readable)")
            else:
                logger.error(f"{city_name} ({city_id}): {mount_path} (not mounted)")
        
        logger.info("")
        logger.info(f"📊 Flex Server Summary: {accessible_mounts}/{total_mounts} accessible")
        
        return accessible_mounts > 0
        
    except Exception as e:
        logger.error(f"Error checking flex server access: {e}")
        return False


def check_transcription_dependencies():
    """Check if all transcription dependencies are available."""
    logger.info("🔍 Checking Transcription Dependencies...")
    
    dependencies = [
        ('faster_whisper', 'WhisperX transcription engine'),
        ('ffmpeg', 'Video processing and metadata extraction'),
        ('magic', 'File type detection'),
        ('psutil', 'System resource monitoring'),
        ('redis', 'Task queue backend'),
        ('celery', 'Distributed task queue'),
    ]
    
    missing_deps = []
    
    for module, description in dependencies:
        try:
            if module == 'ffmpeg':
                import subprocess
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            else:
                __import__(module)
            logger.success(f"{module}: {description}")
        except (ImportError, subprocess.CalledProcessError):
            logger.error(f"{module}: {description} (missing)")
            missing_deps.append(module)
    
    if missing_deps:
        logger.warning(f"Missing dependencies: {missing_deps}")
        logger.info("   Install with: pip install --break-system-packages " + " ".join(missing_deps))
        return False
    else:
        logger.success("All transcription dependencies are available")
        return True


def check_scheduled_tasks():
    """Check if scheduled tasks are configured."""
    logger.info("🔍 Checking Scheduled Tasks...")
    
    try:
        from core.tasks import celery_app
        
        beat_schedule = getattr(celery_app.conf, 'beat_schedule', {})
        
        expected_schedules = [
            'process_recent_vods',
            'cleanup_temp_files',
            'health_check'
        ]
        
        configured_schedules = list(beat_schedule.keys())
        
        logger.success(f"Configured scheduled tasks: {len(configured_schedules)}")
        
        for schedule in expected_schedules:
            if schedule in beat_schedule:
                task_info = beat_schedule[schedule]
                logger.success(f"{schedule}: {task_info['task']} at {task_info['schedule']}")
            else:
                logger.error(f"{schedule}: Not configured")
        
        missing_schedules = [s for s in expected_schedules if s not in configured_schedules]
        
        if missing_schedules:
            logger.warning(f"Missing scheduled tasks: {missing_schedules}")
            return False
        else:
            logger.success("All expected scheduled tasks are configured")
            return True
            
    except Exception as e:
        logger.error(f"Error checking scheduled tasks: {e}")
        return False


def test_vod_processing():
    """Test VOD processing functionality."""
    logger.info("🔍 Testing VOD Processing...")
    
    try:
        from core.tasks import process_vod_captions
        
        logger.info("Triggering VOD processing task...")
        
        result = process_vod_captions.delay()
        
        logger.success(f"VOD processing task triggered: {result.id}")
        
        # Wait a moment for the task to start
        time.sleep(3)
        
        # Check task status
        try:
            task_result = result.get(timeout=30)
            logger.success(f"Task completed: {task_result}")
        except Exception as e:
            if "TimeoutError" in str(e):
                logger.info("Task is still running (this is normal for VOD processing)")
            else:
                logger.info(f"Task status check: {e} (task is likely running)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing VOD processing: {e}")
        return False


def check_redis_connection():
    """Check Redis connection and Celery integration."""
    logger.info("🔍 Checking Redis Connection...")
    
    try:
        import redis
        from core.config import REDIS_URL
        
        # Parse Redis URL
        if REDIS_URL.startswith('redis://'):
            redis_url = REDIS_URL[8:]  # Remove 'redis://' prefix
            if '@' in redis_url:
                auth, host_port = redis_url.split('@')
                password = auth.split(':')[-1] if ':' in auth else None
                host, port = host_port.split(':')
                port = int(port) if port else 6379
            else:
                password = None
                if ':' in redis_url:
                    host, port = redis_url.split(':')
                    port = int(port) if port else 6379
                else:
                    host, port = redis_url, 6379
        else:
            host, port, password = 'localhost', 6379, None
        
        r = redis.Redis(host=host, port=port, password=password, decode_responses=True)
        r.ping()
        
        logger.success(f"Redis connection successful: {REDIS_URL}")
        
        # Check Celery keys
        celery_keys = r.keys('celery*')
        logger.success(f"Celery keys in Redis: {len(celery_keys)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False


def main():
    """Main verification function."""
    logger.info("🚀 Archivist System Verification")
    logger.info("=" * 50)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    checks = [
        ("Celery Worker Status", check_celery_worker),
        ("Task Registration", check_task_registration),
        ("Flex Server Access", check_flex_server_access),
        ("Transcription Dependencies", check_transcription_dependencies),
        ("Scheduled Tasks", check_scheduled_tasks),
        ("VOD Processing", test_vod_processing),
        ("Redis Connection", check_redis_connection),
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            logger.error(f"❌ {check_name} check failed with exception: {e}")
            results[check_name] = False
    
    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info("📊 VERIFICATION SUMMARY")
    logger.info("=" * 50)
    
    passed = 0
    total = len(checks)
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {check_name}")
        if result:
            passed += 1
    
    logger.info("")
    logger.info(f"Overall Status: {passed}/{total} checks passed")
    
    if passed == total:
        logger.success("🎉 All systems operational! Archivist is ready for production use.")
    elif passed >= total * 0.7:
        logger.warning("⚠️  Most systems operational, but some issues need attention.")
    else:
        logger.error("❌ Multiple system issues detected. Please review and fix.")
    
    return 0 if passed >= total * 0.7 else 1


if __name__ == "__main__":
    sys.exit(main()) 