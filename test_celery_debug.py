#!/usr/bin/env python3
"""
Celery Debug Test Script

This script tests Celery functionality step by step to identify and fix issues.
"""

import os
import sys
import time
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def log(message: str, level: str = "INFO"):
    """Log messages with timestamps."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def test_celery_imports():
    """Test basic Celery imports."""
    try:
        log("Testing Celery imports...")
        
        from core.tasks import celery_app
        from core.tasks.vod_processing import cleanup_temp_files
        
        log("✓ Celery imports successful")
        return True
    except Exception as e:
        log(f"✗ Celery import failed: {e}", "ERROR")
        return False

def test_celery_app_config():
    """Test Celery app configuration."""
    try:
        log("Testing Celery app configuration...")
        
        from core.tasks import celery_app
        
        # Check broker URL
        broker_url = celery_app.conf.get('broker_url', 'Not set')
        log(f"Broker URL: {broker_url}")
        
        # Check result backend
        result_backend = celery_app.conf.get('result_backend', 'Not set')
        log(f"Result backend: {result_backend}")
        
        # Check registered tasks
        registered_tasks = list(celery_app.tasks.keys())
        log(f"Registered tasks: {len(registered_tasks)}")
        
        # Check for specific tasks
        vod_tasks = [task for task in registered_tasks if 'vod' in task.lower()]
        log(f"VOD tasks: {vod_tasks}")
        
        log("✓ Celery app configuration looks good")
        return True
    except Exception as e:
        log(f"✗ Celery app config failed: {e}", "ERROR")
        return False

def test_celery_task_submission():
    """Test Celery task submission with proper result handling."""
    try:
        log("Testing Celery task submission...")
        
        from core.tasks import celery_app
        from core.tasks.vod_processing import cleanup_temp_files
        
        # Test task submission
        log("Submitting cleanup_temp_files task...")
        result = cleanup_temp_files.delay()
        
        # Check result object type
        log(f"Result type: {type(result)}")
        log(f"Result ID: {result.id}")
        
        # Check if result has required methods
        if hasattr(result, 'ready'):
            log("✓ Result has 'ready' method")
        else:
            log("✗ Result missing 'ready' method", "ERROR")
            return False
            
        if hasattr(result, 'get'):
            log("✓ Result has 'get' method")
        else:
            log("✗ Result missing 'get' method", "ERROR")
            return False
        
        # Wait for task completion
        log("Waiting for task completion...")
        start_time = time.time()
        timeout = 30
        
        while time.time() - start_time < timeout:
            if result.ready():
                break
            time.sleep(1)
        
        if result.ready():
            try:
                task_result = result.get(timeout=10)
                log(f"✓ Task completed successfully: {task_result}")
                return True
            except Exception as e:
                log(f"✗ Task result retrieval failed: {e}", "ERROR")
                return False
        else:
            log("✗ Task timeout", "ERROR")
            return False
            
    except Exception as e:
        log(f"✗ Celery task submission failed: {e}", "ERROR")
        return False

def test_redis_connection():
    """Test Redis connection."""
    try:
        log("Testing Redis connection...")
        
        import redis
        
        # Try to connect to Redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        
        log("✓ Redis connection successful")
        return True
    except Exception as e:
        log(f"✗ Redis connection failed: {e}", "ERROR")
        return False

def test_celery_worker_status():
    """Test Celery worker status."""
    try:
        log("Testing Celery worker status...")
        
        from core.tasks import celery_app
        
        # Check active workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            log(f"✓ Found {len(active_workers)} active workers")
            for worker, tasks in active_workers.items():
                log(f"  - {worker}: {len(tasks)} active tasks")
            return True
        else:
            log("⚠ No active workers found", "WARNING")
            return False
            
    except Exception as e:
        log(f"✗ Celery worker status check failed: {e}", "ERROR")
        return False

def test_vod_processing_with_real_files():
    """Test VOD processing with real files."""
    try:
        log("Testing VOD processing with real files...")
        
        from core.tasks.vod_processing import (
            validate_video_file, get_vod_file_path, get_recent_vods_from_flex_server
        )
        from core.config import MEMBER_CITIES
        
        # Find real video files
        test_vod_files = []
        for city_id, city_config in MEMBER_CITIES.items():
            mount_path = city_config.get('mount_path')
            if mount_path and os.path.ismount(mount_path):
                try:
                    vod_files = get_recent_vods_from_flex_server(mount_path, city_id, limit=1)
                    test_vod_files.extend(vod_files)
                    if test_vod_files:
                        break
                except Exception as e:
                    log(f"Warning: Could not scan {city_id}: {e}", "WARNING")
        
        if not test_vod_files:
            log("No real video files found", "ERROR")
            return False
        
        # Test with first real file
        vod_data = test_vod_files[0]
        log(f"Testing with: {vod_data.get('title', 'Unknown')}")
        
        # Get file path
        file_path = get_vod_file_path(vod_data)
        if not file_path:
            log("✗ Could not get file path", "ERROR")
            return False
        
        log(f"File path: {file_path}")
        
        # Validate video file
        if os.path.exists(file_path):
            validation_result = validate_video_file(file_path)
            log(f"Video validation: {validation_result}")
            
            file_size = os.path.getsize(file_path)
            log(f"File size: {file_size / (1024*1024):.1f} MB")
            
            if validation_result and file_size > 1024*1024:
                log("✓ Real video file validated successfully")
                return True
            else:
                log("✗ Video validation failed", "ERROR")
                return False
        else:
            log("✗ File not found", "ERROR")
            return False
            
    except Exception as e:
        log(f"✗ VOD processing test failed: {e}", "ERROR")
        return False

def main():
    """Main test function."""
    log("Starting Celery Debug Tests")
    log("=" * 50)
    
    results = {}
    
    # Test 1: Redis connection
    log("\n=== Testing Redis Connection ===")
    results['redis'] = test_redis_connection()
    
    # Test 2: Celery imports
    log("\n=== Testing Celery Imports ===")
    results['imports'] = test_celery_imports()
    
    # Test 3: Celery app config
    log("\n=== Testing Celery App Config ===")
    results['config'] = test_celery_app_config()
    
    # Test 4: Celery worker status
    log("\n=== Testing Celery Worker Status ===")
    results['worker_status'] = test_celery_worker_status()
    
    # Test 5: Task submission
    log("\n=== Testing Task Submission ===")
    results['task_submission'] = test_celery_task_submission()
    
    # Test 6: VOD processing
    log("\n=== Testing VOD Processing ===")
    results['vod_processing'] = test_vod_processing_with_real_files()
    
    # Print results
    log("\n" + "=" * 50)
    log("CELERY DEBUG TEST RESULTS")
    log("=" * 50)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        log(f"{status}: {test_name.replace('_', ' ').title()}")
    
    # Save results
    try:
        with open('celery_debug_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        log("Results saved to: celery_debug_results.json")
    except Exception as e:
        log(f"Warning: Could not save results: {e}", "WARNING")
    
    # Overall result
    passed = sum(results.values())
    total = len(results)
    success_rate = passed / total if total > 0 else 0
    
    log(f"\nOverall: {passed}/{total} tests passed ({success_rate:.1%})")
    
    if success_rate >= 0.8:
        log("🎉 Most tests passed!")
        return 0
    else:
        log("❌ Several tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 