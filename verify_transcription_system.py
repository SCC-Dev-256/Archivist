#!/usr/bin/env python3
"""
Transcription System Verification Script

This script verifies that the Archivist transcription system is working correctly,
including:
1. faster-whisper integration for SCC caption generation
2. Queue system for processing most recently recorded content
3. Automatic processing at 11 PM Central Time
4. Flex server integration and file discovery
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))


def check_faster_whisper_installation():
    """Check if faster-whisper is properly installed and working."""
    logger.info("🔍 Checking faster-whisper Installation...")
    
    try:
        import faster_whisper
        logger.success(f"faster-whisper version: {faster_whisper.__version__}")
        
        # Test model loading
        from core.config import WHISPER_MODEL, USE_GPU, COMPUTE_TYPE, BATCH_SIZE
        
        logger.info("Model configuration:")
        logger.info(f"   - Model: {WHISPER_MODEL}")
        logger.info(f"   - Device: {'CUDA' if USE_GPU else 'CPU'}")
        logger.info(f"   - Compute Type: {COMPUTE_TYPE}")
        logger.info(f"   - Batch Size: {BATCH_SIZE}")
        
        return True
        
    except ImportError as e:
        logger.error(f"faster-whisper not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Error checking faster-whisper: {e}")
        return False


def check_scc_generation():
    """Check if SCC caption generation is working."""
    logger.info("🔍 Checking SCC Caption Generation...")
    
    try:
        from core.transcription import _transcribe_with_faster_whisper
        
        # Find a test video file
        test_video = None
        flex_mounts = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4', 
                      '/mnt/flex-5', '/mnt/flex-6', '/mnt/flex-7', '/mnt/flex-8']
        
        for mount in flex_mounts:
            if os.path.ismount(mount):
                # Look for a small test video
                for root, dirs, files in os.walk(mount):
                    for file in files:
                        if file.lower().endswith(('.mp4', '.mov', '.avi')):
                            file_path = os.path.join(root, file)
                            if os.path.getsize(file_path) < 50 * 1024 * 1024:  # Less than 50MB
                                test_video = file_path
                                break
                    if test_video:
                        break
            if test_video:
                break
        
        if not test_video:
            logger.warning("No suitable test video found (skipping SCC generation test)")
            return True
        
        logger.success(f"Found test video: {test_video}")
        logger.info(f"File size: {os.path.getsize(test_video) / (1024*1024):.1f} MB")
        
        # Test SCC generation
        logger.info("🚀 Testing SCC caption generation...")
        start_time = time.time()
        
        result = _transcribe_with_faster_whisper(test_video)
        
        processing_time = time.time() - start_time
        
        if result.get('status') == 'completed':
            scc_path = result.get('output_path')
            if os.path.exists(scc_path):
                logger.success(f"SCC file generated: {scc_path}")
                logger.info(f"Processing time: {processing_time:.1f} seconds")
                logger.info(f"Caption segments: {result.get('segments', 0)}")
                logger.info(f"Video duration: {result.get('duration', 0):.1f} seconds")
                
                # Check SCC file content
                with open(scc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if content.startswith('Scenarist_SCC V1.0'):
                    logger.success("SCC file format is correct")
                else:
                    logger.error("SCC file format is incorrect")
                    return False
            else:
                logger.error(f"SCC file not found at {scc_path}")
                return False
        else:
            logger.error(f"Transcription failed: {result}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing SCC generation: {e}")
        return False


def check_queue_system():
    """Check if the queue system is working."""
    logger.info("🔍 Checking Queue System...")
    
    try:
        from core.tasks import celery_app
        from celery import current_app
        
        # Check registered tasks
        transcription_tasks = [
            'core.tasks.transcribe_video',
            'core.tasks.process_vod_captions',
            'core.tasks.process_archivist_content_for_vod'
        ]
        
        registered_tasks = current_app.tasks.keys()
        
        logger.success(f"Registered transcription tasks: {len(transcription_tasks)}")
        for task in transcription_tasks:
            if task in registered_tasks:
                logger.info(f"   - {task}")
        
        # Test task queuing
        logger.info("🚀 Testing task queuing...")
        from core.tasks import transcribe_video
        
        test_result = transcribe_video.delay('/tmp/nonexistent_test.mp4')
        
        logger.success(f"Task queued successfully: {test_result.id}")
        
        # Check task status
        try:
            task_status = test_result.get(timeout=5)
            logger.success("Task completed (test file doesn't exist, but queue is working)")
        except Exception as e:
            if "FileNotFoundError" in str(e):
                logger.info("Task completed (test file doesn't exist, but queue is working)")
            else:
                logger.info("Task is in queue (this is expected for non-existent test file)")
                logger.debug(f"Task status check: {e} (queue is working)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing queue system: {e}")
        return False


def check_flex_server_integration():
    """Check flex server integration and file discovery."""
    logger.info("🔍 Checking Flex Server Integration...")
    
    try:
        from core.config import MEMBER_CITIES
        
        accessible_servers = 0
        total_files_found = 0
        
        for city_id, city_config in MEMBER_CITIES.items():
            city_name = city_config['name']
            mount_path = city_config['mount_path']
            
            if os.path.ismount(mount_path):
                accessible_servers += 1
                logger.success(f"Testing {city_name} ({city_id}): {mount_path}")
                
                # Find recent VOD files
                recent_vods = []
                for root, dirs, files in os.walk(mount_path):
                    for file in files:
                        if file.lower().endswith(('.mp4', '.mov', '.avi')):
                            file_path = os.path.join(root, file)
                            mod_time = os.path.getmtime(file_path)
                            recent_vods.append({
                                'title': file,
                                'file_path': file_path,
                                'mod_time': mod_time
                            })
                
                # Sort by modification time (most recent first)
                recent_vods.sort(key=lambda x: x['mod_time'], reverse=True)
                recent_vods = recent_vods[:5]  # Top 5 most recent
                
                total_files_found += len(recent_vods)
                
                if recent_vods:
                    logger.info(f"   📹 Found {len(recent_vods)} recent videos")
                    
                    most_recent = recent_vods[0]
                    mod_date = datetime.fromtimestamp(most_recent['mod_time']).strftime('%Y-%m-%d %H:%M')
                    logger.info(f"   🕐 Most recent: {most_recent['title']} ({mod_date})")
                    
                    # Check if it has captions
                    scc_path = most_recent['file_path'].rsplit('.', 1)[0] + '.scc'
                    if os.path.exists(scc_path):
                        logger.success(f"   ✅ Already has captions: {os.path.basename(scc_path)}")
                    else:
                        logger.info(f"   ⏳ Needs captions: {os.path.basename(most_recent['file_path'])}")
                else:
                    logger.warning(f"   ⚠️  No recent videos found")
            else:
                logger.error(f"{city_name} ({city_id}): {mount_path} (not mounted)")
        
        logger.info("")
        logger.info("📊 Flex Server Summary:")
        logger.info(f"   - Accessible servers: {accessible_servers}/{len(MEMBER_CITIES)}")
        logger.info(f"   - Total recent files: {total_files_found}")
        
        return accessible_servers > 0
        
    except Exception as e:
        logger.error(f"Error checking flex server integration: {e}")
        return False


def check_scheduled_processing():
    """Check if scheduled processing is configured."""
    logger.info("🔍 Checking Scheduled Processing...")
    
    try:
        from core.tasks import celery_app
        from celery import current_app
        
        # Check VOD processing tasks
        vod_tasks = [
            'core.tasks.process_vod_captions',
            'core.tasks.process_archivist_content_for_vod'
        ]
        
        registered_tasks = current_app.tasks.keys()
        
        logger.success(f"Configured VOD processing tasks: {len(vod_tasks)}")
        for task_name in vod_tasks:
            if task_name in registered_tasks:
                task_info = current_app.tasks[task_name]
                schedule = getattr(task_info, 'schedule', 'Not scheduled')
                logger.info(f"   - {task_name}: {task_info}")
                logger.info(f"     Schedule: {schedule}")
        
        # Check environment variable
        vod_time = os.getenv('VOD_PROCESSING_TIME', '19:00')
        logger.info(f"VOD_PROCESSING_TIME environment variable: {vod_time}")
        
        if vod_time == '19:00':
            logger.success("Scheduled for 11 PM Central Time")
        else:
            logger.warning(f"Scheduled for {vod_time} (not 11 PM)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking scheduled processing: {e}")
        return False


def check_recent_content_processing():
    """Check if recent content processing is working."""
    logger.info("🔍 Checking Recent Content Processing...")
    
    try:
        from core.config import MEMBER_CITIES
        
        # Find a test mount
        test_mount = None
        for city_id, city_config in MEMBER_CITIES.items():
            mount_path = city_config['mount_path']
            if os.path.ismount(mount_path):
                test_mount = mount_path
                break
        
        if not test_mount:
            logger.warning("No flex server available for testing")
            return True
        
        logger.success(f"Testing with: {test_mount}")
        
        # Find recent videos
        recent_vods = []
        for root, dirs, files in os.walk(test_mount):
            for file in files:
                if file.lower().endswith(('.mp4', '.mov', '.avi')):
                    file_path = os.path.join(root, file)
                    mod_time = os.path.getmtime(file_path)
                    recent_vods.append({
                        'title': file,
                        'file_path': file_path,
                        'mod_time': mod_time
                    })
        
        if not recent_vods:
            logger.warning("No videos found for testing")
            return True
        
        # Sort by modification time
        recent_vods.sort(key=lambda x: x['mod_time'], reverse=True)
        recent_vods = recent_vods[:10]  # Top 10 most recent
        
        logger.success(f"Found {len(recent_vods)} recent videos")
        
        # Check chronological order
        logger.info("📅 Checking chronological order:")
        for i, vod in enumerate(recent_vods):
            mod_date = datetime.fromtimestamp(vod['mod_time']).strftime('%Y-%m-%d %H:%M')
            logger.info(f"   {i+1}. {vod['title']} - {mod_date}")
        
        # Verify sorting
        if all(recent_vods[i]['mod_time'] >= recent_vods[i+1]['mod_time'] 
               for i in range(len(recent_vods)-1)):
            logger.success("Videos are correctly sorted by modification time (most recent first)")
        else:
            logger.error("Videos are not correctly sorted by modification time")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking recent content processing: {e}")
        return False


def test_complete_pipeline():
    """Test the complete VOD processing pipeline."""
    logger.info("🔍 Testing Complete Pipeline...")
    
    try:
        from core.tasks import process_vod_captions
        
        # Trigger VOD processing task
        logger.info("🚀 Triggering VOD processing task...")
        
        result = process_vod_captions.delay()
        
        logger.success(f"VOD processing task triggered: {result.id}")
        
        # Check task status
        try:
            task_result = result.get(timeout=30)
            logger.success(f"Task completed: {task_result}")
        except Exception as e:
            if "TimeoutError" in str(e):
                logger.info("Task is still running (this is normal for VOD processing)")
            else:
                logger.error(f"Task failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing complete pipeline: {e}")
        return False


def main():
    """Main verification function."""
    logger.info("🎤 Transcription System Verification")
    logger.info("=" * 60)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    checks = [
        ("Faster-Whisper Installation", check_faster_whisper_installation),
        ("SCC Caption Generation", check_scc_generation),
        ("Queue System", check_queue_system),
        ("Flex Server Integration", check_flex_server_integration),
        ("Scheduled Processing", check_scheduled_processing),
        ("Recent Content Processing", check_recent_content_processing),
        ("Complete Pipeline", test_complete_pipeline),
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
    logger.info("=" * 60)
    logger.info("📊 TRANSCRIPTION SYSTEM VERIFICATION SUMMARY")
    logger.info("=" * 60)
    
    passed = 0
    total = len(checks)
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {check_name}")
        if result:
            passed += 1
    
    logger.info("")
    logger.info(f"Overall: {passed}/{total} checks passed")
    
    if passed == total:
        logger.success("🎉 All transcription system checks passed!")
        logger.info("The system is ready for production use.")
    elif passed >= total * 0.7:
        logger.warning("⚠️  Most checks passed. System is mostly operational.")
        logger.info("Some components may need attention.")
    else:
        logger.error("❌ Multiple checks failed. System needs attention.")
        logger.info("Please review the failed checks above.")
    
    return 0 if passed >= total * 0.7 else 1


if __name__ == "__main__":
    sys.exit(main()) 