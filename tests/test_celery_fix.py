#!/usr/bin/env python3
"""
Test Celery Fix

This script tests different ways to create a Celery app to fix the configuration issue.
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def log(message: str, level: str = "INFO"):
    """Log messages with timestamps."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def main():
    """Main test function."""
    log("Testing Celery Fix")
    log("=" * 50)
    
    # Test 1: Create Celery app with different approach
    log("\n=== Testing Different Celery App Creation ===")
    try:
        from celery import Celery
        from core.config import REDIS_URL
        
        log(f"REDIS_URL: {REDIS_URL}")
        
        # Method 1: Create app without broker/backend, then set config
        app1 = Celery('test_app1')
        app1.conf.update(
            broker_url=REDIS_URL,
            result_backend=REDIS_URL,
            task_serializer='json',
            result_serializer='json',
            accept_content=['json'],
            result_expires=86400,
            timezone='UTC',
            enable_utc=True,
        )
        
        log("✓ App 1 created with conf.update")
        
        # Method 2: Create app with broker/backend in constructor
        app2 = Celery(
            'test_app2',
            broker=REDIS_URL,
            backend=REDIS_URL,
        )
        app2.conf.update(
            task_serializer='json',
            result_serializer='json',
            accept_content=['json'],
            result_expires=86400,
            timezone='UTC',
            enable_utc=True,
        )
        
        log("✓ App 2 created with broker/backend in constructor")
        
        # Method 3: Create app with explicit configuration
        app3 = Celery('test_app3')
        app3.conf.broker_url = REDIS_URL
        app3.conf.result_backend = REDIS_URL
        app3.conf.task_serializer = 'json'
        app3.conf.result_serializer = 'json'
        app3.conf.accept_content = ['json']
        app3.conf.result_expires = 86400
        app3.conf.timezone = 'UTC'
        app3.conf.enable_utc = True
        
        log("✓ App 3 created with explicit conf assignment")
        
        # Test which method works
        for i, app in enumerate([app1, app2, app3], 1):
            try:
                broker_url = getattr(app.conf, 'broker_url', None)
                result_backend = getattr(app.conf, 'result_backend', None)
                log(f"  App {i}: broker_url={broker_url}, result_backend={result_backend}")
            except Exception as e:
                log(f"  App {i}: Error accessing config: {e}")
        
        # Test task creation and submission
        @app1.task
        def test_task1():
            return {"success": True, "message": "Task 1 completed"}
        
        @app2.task
        def test_task2():
            return {"success": True, "message": "Task 2 completed"}
        
        @app3.task
        def test_task3():
            return {"success": True, "message": "Task 3 completed"}
        
        # Submit tasks
        results = []
        for i, (app, task) in enumerate([(app1, test_task1), (app2, test_task2), (app3, test_task3)], 1):
            try:
                result = task.delay()
                log(f"✓ App {i} task submitted: {type(result)}")
                results.append((i, result))
            except Exception as e:
                log(f"✗ App {i} task submission failed: {e}", "ERROR")
        
        # Check results
        from celery.result import AsyncResult
        for i, result in results:
            if isinstance(result, AsyncResult):
                log(f"✓ App {i} result is AsyncResult")
            else:
                log(f"✗ App {i} result is NOT AsyncResult: {type(result)}", "ERROR")
                
    except Exception as e:
        log(f"✗ Celery fix test failed: {e}", "ERROR")
        return 1
    
    # Test 2: Fix the main app
    log("\n=== Testing Main App Fix ===")
    try:
        from core.tasks import celery_app
        
        # Try to fix the main app configuration
        try:
            celery_app.conf.broker_url = REDIS_URL
            celery_app.conf.result_backend = REDIS_URL
            log("✓ Main app configuration updated")
        except Exception as e:
            log(f"✗ Main app configuration update failed: {e}", "ERROR")
        
        # Test main app task
        from core.tasks.vod_processing import cleanup_temp_files
        
        result = cleanup_temp_files.delay()
        log(f"✓ Main app task submitted: {type(result)}")
        
        if isinstance(result, AsyncResult):
            log("✓ Main app result is AsyncResult")
        else:
            log("✗ Main app result is NOT AsyncResult", "ERROR")
            
    except Exception as e:
        log(f"✗ Main app fix test failed: {e}", "ERROR")
        return 1
    
    log("\n" + "=" * 50)
    log("Celery fix test completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 