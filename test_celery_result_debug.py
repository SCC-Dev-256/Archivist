#!/usr/bin/env python3
"""
Celery Result Object Debug Test

This script specifically tests why Celery tasks aren't returning proper AsyncResult objects.
"""

import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def log(message: str, level: str = "INFO"):
    """Log messages with timestamps."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def test_celery_app_import():
    """Test Celery app import and basic configuration."""
    try:
        log("Testing Celery app import...")
        
        from core.tasks import celery_app
        
        log(f"✓ Celery app imported successfully")
        log(f"  - App type: {type(celery_app)}")
        log(f"  - Broker URL: {getattr(celery_app.conf, 'broker_url', 'Not set')}")
        log(f"  - Result backend: {getattr(celery_app.conf, 'result_backend', 'Not set')}")
        
        return celery_app
    except Exception as e:
        log(f"✗ Celery app import failed: {e}", "ERROR")
        return None

def test_task_registration(celery_app):
    """Test that tasks are properly registered."""
    try:
        log("Testing task registration...")
        
        registered_tasks = list(celery_app.tasks.keys())
        log(f"✓ Found {len(registered_tasks)} registered tasks")
        
        # Check for specific VOD tasks
        vod_tasks = [task for task in registered_tasks if 'vod_processing' in task]
        log(f"  - VOD tasks: {vod_tasks}")
        
        # Check for cleanup task specifically
        cleanup_task = 'vod_processing.cleanup_temp_files'
        if cleanup_task in registered_tasks:
            log(f"✓ {cleanup_task} is registered")
            return True
        else:
            log(f"✗ {cleanup_task} is NOT registered", "ERROR")
            return False
            
    except Exception as e:
        log(f"✗ Task registration test failed: {e}", "ERROR")
        return False

def test_task_import():
    """Test direct task import."""
    try:
        log("Testing direct task import...")
        
        from core.tasks.vod_processing import cleanup_temp_files
        
        log(f"✓ Task imported successfully")
        log(f"  - Task type: {type(cleanup_temp_files)}")
        log(f"  - Has delay method: {hasattr(cleanup_temp_files, 'delay')}")
        log(f"  - Has apply_async method: {hasattr(cleanup_temp_files, 'apply_async')}")
        
        return cleanup_temp_files
    except Exception as e:
        log(f"✗ Task import failed: {e}", "ERROR")
        return None

def test_task_submission_direct(task_func):
    """Test direct task submission."""
    try:
        log("Testing direct task submission...")
        
        # Submit task directly
        result = task_func.delay()
        
        log(f"✓ Task submitted successfully")
        log(f"  - Result type: {type(result)}")
        log(f"  - Result ID: {result.id}")
        log(f"  - Has ready method: {hasattr(result, 'ready')}")
        log(f"  - Has get method: {hasattr(result, 'get')}")
        log(f"  - Has status method: {hasattr(result, 'status')}")
        
        # Check if it's a proper AsyncResult
        from celery.result import AsyncResult
        if isinstance(result, AsyncResult):
            log("✓ Result is proper AsyncResult object")
        else:
            log("✗ Result is NOT AsyncResult object", "ERROR")
            log(f"  - Expected: AsyncResult, Got: {type(result)}")
        
        return result
    except Exception as e:
        log(f"✗ Direct task submission failed: {e}", "ERROR")
        return None

def test_task_submission_via_app(celery_app):
    """Test task submission via celery app."""
    try:
        log("Testing task submission via celery app...")
        
        # Submit task via app
        result = celery_app.send_task('vod_processing.cleanup_temp_files')
        
        log(f"✓ Task submitted via app successfully")
        log(f"  - Result type: {type(result)}")
        log(f"  - Result ID: {result.id}")
        log(f"  - Has ready method: {hasattr(result, 'ready')}")
        log(f"  - Has get method: {hasattr(result, 'get')}")
        
        # Check if it's a proper AsyncResult
        from celery.result import AsyncResult
        if isinstance(result, AsyncResult):
            log("✓ App result is proper AsyncResult object")
        else:
            log("✗ App result is NOT AsyncResult object", "ERROR")
        
        return result
    except Exception as e:
        log(f"✗ App task submission failed: {e}", "ERROR")
        return None

def test_result_retrieval(result):
    """Test result retrieval."""
    if not result:
        log("No result to test", "WARNING")
        return False
        
    try:
        log("Testing result retrieval...")
        
        # Wait for task completion
        log("Waiting for task completion...")
        start_time = time.time()
        timeout = 30
        
        while time.time() - start_time < timeout:
            if result.ready():
                break
            time.sleep(1)
        
        if result.ready():
            log("✓ Task completed")
            
            # Get result
            task_result = result.get(timeout=10)
            log(f"✓ Task result retrieved: {task_result}")
            
            # Check result structure
            if isinstance(task_result, dict):
                log("✓ Result is dictionary")
                if 'success' in task_result:
                    log(f"  - Success: {task_result['success']}")
                if 'cleaned_count' in task_result:
                    log(f"  - Cleaned count: {task_result['cleaned_count']}")
            else:
                log(f"⚠ Result is not dictionary: {type(task_result)}", "WARNING")
            
            return True
        else:
            log("✗ Task timeout", "ERROR")
            return False
            
    except Exception as e:
        log(f"✗ Result retrieval failed: {e}", "ERROR")
        return False

def test_redis_connection():
    """Test Redis connection."""
    try:
        log("Testing Redis connection...")
        
        import redis
        
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        
        log("✓ Redis connection successful")
        return True
    except Exception as e:
        log(f"✗ Redis connection failed: {e}", "ERROR")
        return False

def main():
    """Main test function."""
    log("Starting Celery Result Debug Tests")
    log("=" * 50)
    
    results = {}
    
    # Test 1: Redis connection
    log("\n=== Testing Redis Connection ===")
    results['redis'] = test_redis_connection()
    
    # Test 2: Celery app import
    log("\n=== Testing Celery App Import ===")
    celery_app = test_celery_app_import()
    results['app_import'] = celery_app is not None
    
    if celery_app:
        # Test 3: Task registration
        log("\n=== Testing Task Registration ===")
        results['task_registration'] = test_task_registration(celery_app)
        
        # Test 4: Task import
        log("\n=== Testing Task Import ===")
        task_func = test_task_import()
        results['task_import'] = task_func is not None
        
        if task_func:
            # Test 5: Direct task submission
            log("\n=== Testing Direct Task Submission ===")
            direct_result = test_task_submission_direct(task_func)
            results['direct_submission'] = direct_result is not None
            
            # Test 6: App task submission
            log("\n=== Testing App Task Submission ===")
            app_result = test_task_submission_via_app(celery_app)
            results['app_submission'] = app_result is not None
            
            # Test 7: Result retrieval
            log("\n=== Testing Result Retrieval ===")
            test_result = direct_result or app_result
            results['result_retrieval'] = test_result_retrieval(test_result)
    
    # Print results
    log("\n" + "=" * 50)
    log("CELERY RESULT DEBUG RESULTS")
    log("=" * 50)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        log(f"{status}: {test_name.replace('_', ' ').title()}")
    
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