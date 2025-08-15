#!/usr/bin/env python3
"""
Simple Celery Test

This script creates a simple Celery app to test if the basic functionality works.
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
    log("Testing Simple Celery App")
    log("=" * 50)
    
    # Test 1: Create a simple Celery app
    log("\n=== Creating Simple Celery App ===")
    try:
        from celery import Celery
        
        # Create app with explicit configuration
        app = Celery('test_app')
        app.conf.update(
            broker_url='redis://localhost:6379/0',
            result_backend='redis://localhost:6379/0',
            task_serializer='json',
            result_serializer='json',
            accept_content=['json'],
            result_expires=86400,
            timezone='UTC',
            enable_utc=True,
        )
        
        log("✓ Simple Celery app created")
        log(f"  - Broker URL: {app.conf.broker_url}")
        log(f"  - Result backend: {app.conf.result_backend}")
        
        # Test 2: Create a simple task
        @app.task
        def simple_task():
            return {"success": True, "message": "Simple task completed"}
        
        log("✓ Simple task created")
        
        # Test 3: Submit task
        result = simple_task.delay()
        log("✓ Task submitted")
        log(f"  - Result type: {type(result)}")
        log(f"  - Result ID: {result.id}")
        
        # Test 4: Check if it's AsyncResult
        from celery.result import AsyncResult
        if isinstance(result, AsyncResult):
            log("✓ Result is AsyncResult object")
            
            # Wait for completion
            import time
            timeout = 10
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if result.ready():
                    break
                time.sleep(0.5)
            
            if result.ready():
                task_result = result.get(timeout=5)
                log(f"✓ Task completed: {task_result}")
            else:
                log("⚠ Task did not complete within timeout", "WARNING")
        else:
            log("✗ Result is NOT AsyncResult object", "ERROR")
            log(f"  - Expected: AsyncResult, Got: {type(result)}")
            
    except Exception as e:
        log(f"✗ Simple Celery test failed: {e}", "ERROR")
        return 1
    
    # Test 5: Compare with main app
    log("\n=== Comparing with Main App ===")
    try:
        from core.tasks import celery_app
        
        log("✓ Main app imported")
        log(f"  - Main app type: {type(celery_app)}")
        
        # Try to access configuration
        try:
            broker_url = getattr(celery_app.conf, 'broker_url', 'Not accessible')
            log(f"  - Main app broker URL: {broker_url}")
        except Exception as e:
            log(f"  - Main app broker URL access failed: {e}")
        
        # Try to submit a task from main app
        from core.tasks.vod_processing import cleanup_temp_files
        
        result = cleanup_temp_files.delay()
        log("✓ Main app task submitted")
        log(f"  - Result type: {type(result)}")
        log(f"  - Result ID: {result.id}")
        
        # Check if it's AsyncResult
        if isinstance(result, AsyncResult):
            log("✓ Main app result is AsyncResult object")
        else:
            log("✗ Main app result is NOT AsyncResult object", "ERROR")
            log(f"  - Expected: AsyncResult, Got: {type(result)}")
            
    except Exception as e:
        log(f"✗ Main app comparison failed: {e}", "ERROR")
        return 1
    
    log("\n" + "=" * 50)
    log("Simple Celery test completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 