#!/usr/bin/env python3
"""
Debug Captioning Pipeline

This script provides comprehensive debugging for the automated captioning system.
It tests each component individually and provides detailed logging.
"""

import os
import sys
import time
import traceback
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test all required imports."""
    print("🔍 Testing imports...")
    
    try:
        print("  ✓ Importing faster_whisper...")
        from faster_whisper import WhisperModel
        print("  ✓ faster_whisper imported successfully")
    except ImportError as e:
        print(f"  ❌ faster_whisper import failed: {e}")
        return False
    
    try:
        print("  ✓ Importing transcription module...")
        from core.transcription import _transcribe_with_faster_whisper
        print("  ✓ Transcription module imported successfully")
    except ImportError as e:
        print(f"  ❌ Transcription module import failed: {e}")
        return False
    
    try:
        print("  ✓ Importing VOD processing...")
        from core.tasks.vod_processing import generate_vod_captions
        print("  ✓ VOD processing imported successfully")
    except ImportError as e:
        print(f"  ❌ VOD processing import failed: {e}")
        return False
    
    try:
        print("  ✓ Importing Celery app...")
        from core.tasks import celery_app
        print("  ✓ Celery app imported successfully")
    except ImportError as e:
        print(f"  ❌ Celery app import failed: {e}")
        return False
    
    return True

def test_model_loading():
    """Test Whisper model loading."""
    print("\n🔍 Testing Whisper model loading...")
    
    try:
        from faster_whisper import WhisperModel
        from core.config import WHISPER_MODEL, USE_GPU, COMPUTE_TYPE, BATCH_SIZE
        
        print(f"  Model: {WHISPER_MODEL}")
        print(f"  GPU: {USE_GPU}")
        print(f"  Compute Type: {COMPUTE_TYPE}")
        print(f"  Batch Size: {BATCH_SIZE}")
        
        print("  Loading model...")
        start_time = time.time()
        model = WhisperModel(
            WHISPER_MODEL,
            device="cuda" if USE_GPU else "cpu",
            compute_type=COMPUTE_TYPE,
            cpu_threads=BATCH_SIZE
        )
        load_time = time.time() - start_time
        
        print(f"  ✓ Model loaded successfully in {load_time:.2f} seconds")
        return True
        
    except Exception as e:
        print(f"  ❌ Model loading failed: {e}")
        traceback.print_exc()
        return False

def test_file_access():
    """Test file access to video files."""
    print("\n🔍 Testing file access...")
    
    test_video = "/mnt/flex-1/14204-1-Birchwood Special Council Meeting (20190325).mpeg"
    
    if os.path.exists(test_video):
        print(f"  ✓ Test video exists: {test_video}")
        file_size = os.path.getsize(test_video)
        print(f"  ✓ File size: {file_size / (1024*1024):.1f} MB")
        
        if os.access(test_video, os.R_OK):
            print("  ✓ File is readable")
        else:
            print("  ❌ File is not readable")
            return False
    else:
        print(f"  ❌ Test video not found: {test_video}")
        return False
    
    # Test output directory
    output_dir = "/mnt/flex-1"
    if os.path.exists(output_dir):
        print(f"  ✓ Output directory exists: {output_dir}")
        if os.access(output_dir, os.W_OK):
            print("  ✓ Output directory is writable")
        else:
            print("  ❌ Output directory is not writable")
            return False
    else:
        print(f"  ❌ Output directory not found: {output_dir}")
        return False
    
    return True

def test_direct_transcription():
    """Test direct transcription without Celery."""
    print("\n🔍 Testing direct transcription...")
    
    test_video = "/mnt/flex-1/14204-1-Birchwood Special Council Meeting (20190325).mpeg"
    
    try:
        from core.transcription import _transcribe_with_faster_whisper
        
        print("  Starting direct transcription...")
        start_time = time.time()
        
        result = _transcribe_with_faster_whisper(test_video)
        
        transcription_time = time.time() - start_time
        print(f"  ✓ Direct transcription completed in {transcription_time:.2f} seconds")
        print(f"  ✓ Output path: {result.get('output_path', 'N/A')}")
        print(f"  ✓ Segments: {result.get('segments', 0)}")
        print(f"  ✓ Status: {result.get('status', 'N/A')}")
        
        # Check if SCC file was created
        scc_path = result.get('output_path')
        if scc_path and os.path.exists(scc_path):
            print(f"  ✓ SCC file created: {scc_path}")
            file_size = os.path.getsize(scc_path)
            print(f"  ✓ SCC file size: {file_size} bytes")
        else:
            print(f"  ❌ SCC file not created or not found")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Direct transcription failed: {e}")
        traceback.print_exc()
        return False

def test_celery_task():
    """Test Celery task execution."""
    print("\n🔍 Testing Celery task...")
    
    try:
        from core.tasks.vod_processing import generate_vod_captions
        
        test_video = "/mnt/flex-1/14204-1-Birchwood Special Council Meeting (20190325).mpeg"
        
        print("  Submitting Celery task...")
        task = generate_vod_captions.delay(14204, test_video, 'flex1')
        
        print(f"  ✓ Task submitted: {task.id}")
        print("  Waiting for task completion...")
        
        # Wait for task with timeout
        try:
            result = task.get(timeout=300)  # 5 minute timeout
            print(f"  ✓ Task completed: {result}")
            return True
        except Exception as e:
            print(f"  ❌ Task failed or timed out: {e}")
            return False
            
    except Exception as e:
        print(f"  ❌ Celery task submission failed: {e}")
        traceback.print_exc()
        return False

def test_celery_worker_status():
    """Test Celery worker status."""
    print("\n🔍 Testing Celery worker status...")
    
    try:
        from core.tasks import celery_app
        
        # Check active workers
        inspect = celery_app.control.inspect()
        active = inspect.active()
        registered = inspect.registered()
        stats = inspect.stats()
        
        print(f"  Active workers: {len(active) if active else 0}")
        print(f"  Registered workers: {len(registered) if registered else 0}")
        
        if active:
            for worker, tasks in active.items():
                print(f"  Worker {worker}: {len(tasks)} active tasks")
        
        if registered:
            for worker, tasks in registered.items():
                print(f"  Worker {worker}: {len(tasks)} registered tasks")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Celery worker status check failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all debugging tests."""
    print("🚀 Starting Captioning Pipeline Debug")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Model Loading", test_model_loading),
        ("File Access", test_file_access),
        ("Direct Transcription", test_direct_transcription),
        ("Celery Worker Status", test_celery_worker_status),
        ("Celery Task", test_celery_task),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            traceback.print_exc()
            results[test_name] = False
    
    print("\n" + "=" * 50)
    print("📊 Debug Results Summary")
    print("=" * 50)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Captioning pipeline should be working.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main() 