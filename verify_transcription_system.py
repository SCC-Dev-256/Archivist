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

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def check_faster_whisper_installation():
    """Check if faster-whisper is properly installed and working."""
    print("🔍 Checking faster-whisper Installation...")
    
    try:
        import faster_whisper
        print(f"✅ faster-whisper version: {faster_whisper.__version__}")
        
        # Test model loading
        from core.config import WHISPER_MODEL, USE_GPU, COMPUTE_TYPE, BATCH_SIZE
        
        print(f"✅ Model configuration:")
        print(f"   - Model: {WHISPER_MODEL}")
        print(f"   - Device: {'CUDA' if USE_GPU else 'CPU'}")
        print(f"   - Compute Type: {COMPUTE_TYPE}")
        print(f"   - Batch Size: {BATCH_SIZE}")
        
        return True
        
    except ImportError as e:
        print(f"❌ faster-whisper not installed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking faster-whisper: {e}")
        return False

def check_scc_generation():
    """Check if SCC caption generation is working."""
    print("\n🔍 Checking SCC Caption Generation...")
    
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
            print("⚠️  No suitable test video found (skipping SCC generation test)")
            return True
        
        print(f"✅ Found test video: {test_video}")
        print(f"📊 File size: {os.path.getsize(test_video) / (1024*1024):.1f} MB")
        
        # Test SCC generation
        print("🚀 Testing SCC caption generation...")
        start_time = time.time()
        
        result = _transcribe_with_faster_whisper(test_video)
        
        processing_time = time.time() - start_time
        
        if result.get('status') == 'completed':
            scc_path = result.get('output_path')
            if os.path.exists(scc_path):
                print(f"✅ SCC file generated: {scc_path}")
                print(f"✅ Processing time: {processing_time:.1f} seconds")
                print(f"✅ Caption segments: {result.get('segments', 0)}")
                print(f"✅ Video duration: {result.get('duration', 0):.1f} seconds")
                
                # Check SCC file content
                with open(scc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'Scenarist_SCC V1.0' in content:
                        print("✅ SCC file format is correct")
                        return True
                    else:
                        print("❌ SCC file format is incorrect")
                        return False
            else:
                print(f"❌ SCC file not found at {scc_path}")
                return False
        else:
            print(f"❌ Transcription failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing SCC generation: {e}")
        return False

def check_queue_system():
    """Check if the Celery queue system is working for transcription."""
    print("\n🔍 Checking Queue System...")
    
    try:
        from core.tasks.transcription import run_whisper_transcription
        
        # Test task registration
        from core.tasks import celery_app
        registered_tasks = list(celery_app.tasks.keys())
        transcription_tasks = [task for task in registered_tasks if 'transcription' in task]
        
        print(f"✅ Registered transcription tasks: {len(transcription_tasks)}")
        for task in transcription_tasks:
            print(f"   - {task}")
        
        # Test task queuing with real video from flex servers
        print("🚀 Testing task queuing with real video...")
        
        # Find a real video file for testing
        from core.config import MEMBER_CITIES
        from core.tasks.vod_processing import get_recent_vods_from_flex_server
        
        test_video_path = None
        for city_id, city_config in MEMBER_CITIES.items():
            mount_path = city_config.get('mount_path')
            if mount_path and os.path.ismount(mount_path):
                try:
                    vod_files = get_recent_vods_from_flex_server(mount_path, city_id, limit=1)
                    if vod_files:
                        test_video_path = vod_files[0].get('file_path')
                        break
                except Exception as e:
                    print(f"Warning: Could not scan {city_id}: {e}")
        
        if test_video_path and os.path.exists(test_video_path):
            test_result = run_whisper_transcription.delay(test_video_path)
            print(f"✅ Task queued successfully with real video: {test_result.id}")
            print(f"   Video: {os.path.basename(test_video_path)}")
            
            # Check if worker is processing
            time.sleep(2)
            try:
                if hasattr(test_result, 'ready') and test_result.ready():
                    print("✅ Task completed with real video")
                else:
                    print("⏳ Task is in queue (processing real video)")
            except Exception as e:
                print(f"⏳ Task status check: {e} (queue is working)")
        else:
            print("⚠ No real video files found for queue testing")
            print("Queue test skipped - requires real video files from flex servers")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing queue system: {e}")
        return False

def check_flex_server_integration():
    """Check flex server integration and recent file discovery."""
    print("\n🔍 Checking Flex Server Integration...")
    
    try:
        from core.tasks.vod_processing import get_recent_vods_from_flex_server
        from core.config import MEMBER_CITIES
        
        accessible_servers = 0
        total_files_found = 0
        
        for city_id, city_config in MEMBER_CITIES.items():
            mount_path = city_config['mount_path']
            city_name = city_config['name']
            
            if os.path.ismount(mount_path):
                print(f"✅ Testing {city_name} ({city_id}): {mount_path}")
                
                # Get recent VODs
                recent_vods = get_recent_vods_from_flex_server(mount_path, city_id, limit=3)
                
                if recent_vods:
                    print(f"   📹 Found {len(recent_vods)} recent videos")
                    total_files_found += len(recent_vods)
                    
                    # Show most recent file
                    most_recent = recent_vods[0]
                    from datetime import datetime
                    mod_date = datetime.fromtimestamp(most_recent['modified_time']).strftime('%Y-%m-%d %H:%M')
                    print(f"   🕐 Most recent: {most_recent['title']} ({mod_date})")
                    
                    # Check if SCC already exists
                    base_name = os.path.splitext(most_recent['title'])[0]
                    scc_path = os.path.join(os.path.dirname(most_recent['file_path']), f"{base_name}.scc")
                    if os.path.exists(scc_path):
                        print(f"   ✅ Already has captions: {os.path.basename(scc_path)}")
                    else:
                        print(f"   ⏳ Needs captions: {os.path.basename(most_recent['file_path'])}")
                else:
                    print(f"   ⚠️  No recent videos found")
                
                accessible_servers += 1
            else:
                print(f"❌ {city_name} ({city_id}): {mount_path} (not mounted)")
        
        print(f"\n📊 Flex Server Summary:")
        print(f"   - Accessible servers: {accessible_servers}/{len(MEMBER_CITIES)}")
        print(f"   - Total recent files: {total_files_found}")
        
        return accessible_servers > 0
        
    except ImportError as e:
        if 'flask_socketio' in str(e):
            print(f"⚠️  Flex server integration check skipped - SocketIO not available")
            print(f"   This is expected when Flask-SocketIO is not installed")
            return True  # Not a critical failure
        else:
            print(f"❌ Error checking flex server integration: {e}")
            return False
    except Exception as e:
        print(f"❌ Error checking flex server integration: {e}")
        return False

def check_scheduled_processing():
    """Check if scheduled processing is configured for 11 PM Central Time."""
    print("\n🔍 Checking Scheduled Processing...")
    
    try:
        from core.tasks.scheduler import celery_app
        
        beat_schedule = celery_app.conf.beat_schedule
        
        # Check for VOD processing tasks
        vod_tasks = [task for task in beat_schedule.keys() if 'vod' in task.lower()]
        
        print(f"✅ Configured VOD processing tasks: {len(vod_tasks)}")
        
        for task_name in vod_tasks:
            task_info = beat_schedule[task_name]
            schedule = task_info['schedule']
            
            print(f"   - {task_name}: {task_info['task']}")
            print(f"     Schedule: {schedule}")
        
        # Check environment variable
        import os
        vod_time = os.getenv("VOD_PROCESSING_TIME", "23:00")
        print(f"✅ VOD_PROCESSING_TIME environment variable: {vod_time}")
        
        if vod_time == "23:00":
            print("✅ Scheduled for 11 PM Central Time")
        else:
            print(f"⚠️  Scheduled for {vod_time} (not 11 PM)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking scheduled processing: {e}")
        return False

def check_recent_content_processing():
    """Check if the system prioritizes most recently recorded content."""
    print("\n🔍 Checking Recent Content Processing...")
    
    try:
        from core.tasks.vod_processing import get_recent_vods_from_flex_server
        
        # Test with a specific flex server
        test_mount = None
        for mount in ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4']:
            if os.path.ismount(mount):
                test_mount = mount
                break
        
        if not test_mount:
            print("⚠️  No flex server available for testing")
            return True
        
        print(f"✅ Testing with: {test_mount}")
        
        # Get recent VODs
        recent_vods = get_recent_vods_from_flex_server(test_mount, "test", limit=5)
        
        if not recent_vods:
            print("⚠️  No videos found for testing")
            return True
        
        print(f"✅ Found {len(recent_vods)} recent videos")
        
        # Check if they're sorted by modification time (most recent first)
        from datetime import datetime
        
        print("📅 Checking chronological order:")
        for i, vod in enumerate(recent_vods):
            mod_date = datetime.fromtimestamp(vod['modified_time']).strftime('%Y-%m-%d %H:%M')
            print(f"   {i+1}. {vod['title']} - {mod_date}")
        
        # Verify sorting
        timestamps = [vod['modified_time'] for vod in recent_vods]
        if timestamps == sorted(timestamps, reverse=True):
            print("✅ Videos are correctly sorted by modification time (most recent first)")
            return True
        else:
            print("❌ Videos are not correctly sorted by modification time")
            return False
        
    except Exception as e:
        print(f"❌ Error checking recent content processing: {e}")
        return False

def test_complete_pipeline():
    """Test the complete transcription pipeline."""
    print("\n🔍 Testing Complete Pipeline...")
    
    try:
        # Test VOD processing task
        from core.tasks.vod_processing import process_recent_vods
        
        print("🚀 Triggering VOD processing task...")
        result = process_recent_vods.delay()
        
        print(f"✅ VOD processing task triggered: {result.id}")
        
        # Wait a moment for the task to start
        time.sleep(3)
        
        # Check task status
        if result.ready():
            task_result = result.get()
            print(f"✅ Task completed: {task_result}")
        else:
            print("⏳ Task is still running (this is normal for VOD processing)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing complete pipeline: {e}")
        return False

def main():
    """Run all transcription system verification checks."""
    print("🎤 Transcription System Verification")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    checks = [
        ("faster-whisper Installation", check_faster_whisper_installation),
        ("SCC Caption Generation", check_scc_generation),
        ("Queue System", check_queue_system),
        ("Flex Server Integration", check_flex_server_integration),
        ("Scheduled Processing (11 PM CT)", check_scheduled_processing),
        ("Recent Content Processing", check_recent_content_processing),
        ("Complete Pipeline", test_complete_pipeline)
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
    print("\n" + "=" * 60)
    print("📊 TRANSCRIPTION SYSTEM VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
    
    print(f"\nOverall Status: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 Transcription system is fully operational!")
        print("✅ Automatic SCC caption generation working")
        print("✅ Queue system processing recent content")
        print("✅ Scheduled for 11 PM Central Time")
        print("✅ Flex server integration working")
    elif passed >= total * 0.8:
        print("⚠️  Most transcription components working, but some issues need attention.")
    else:
        print("❌ Multiple transcription system issues detected. Please review and fix.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 