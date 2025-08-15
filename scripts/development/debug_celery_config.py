#!/usr/bin/env python3
"""
Debug Celery Configuration

This script helps debug why Celery tasks aren't returning proper AsyncResult objects.
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
    """Main debug function."""
    log("Starting Celery Configuration Debug")
    log("=" * 50)
    
    # Test 1: Check environment variables
    log("\n=== Environment Variables ===")
    log(f"REDIS_URL: {os.getenv('REDIS_URL', 'Not set')}")
    log(f"REDIS_HOST: {os.getenv('REDIS_HOST', 'Not set')}")
    log(f"REDIS_PORT: {os.getenv('REDIS_PORT', 'Not set')}")
    log(f"REDIS_DB: {os.getenv('REDIS_DB', 'Not set')}")
    log(f"CELERY_TASK_ALWAYS_EAGER: {os.getenv('CELERY_TASK_ALWAYS_EAGER', 'Not set')}")
    
    # Test 2: Check config import
    log("\n=== Config Import ===")
    try:
        from core.config import REDIS_URL
        log(f"✓ Config imported successfully")
        log(f"  - REDIS_URL from config: {REDIS_URL}")
    except Exception as e:
        log(f"✗ Config import failed: {e}", "ERROR")
        return 1
    
    # Test 3: Check Celery app creation
    log("\n=== Celery App Creation ===")
    try:
        from core.tasks import celery_app
        log(f"✓ Celery app created successfully")
        log(f"  - App type: {type(celery_app)}")
        log(f"  - Broker URL: {getattr(celery_app.conf, 'broker_url', 'Not set')}")
        log(f"  - Result backend: {getattr(celery_app.conf, 'result_backend', 'Not set')}")
        log(f"  - Task always eager: {getattr(celery_app.conf, 'task_always_eager', 'Not set')}")
        log(f"  - Task eager propagates: {getattr(celery_app.conf, 'task_eager_propagates', 'Not set')}")
        
        # Check if broker is accessible
        try:
            import redis
            r = redis.from_url(REDIS_URL)
            r.ping()
            log("✓ Redis broker is accessible")
        except Exception as e:
            log(f"✗ Redis broker not accessible: {e}", "ERROR")
            
    except Exception as e:
        log(f"✗ Celery app creation failed: {e}", "ERROR")
        return 1
    
    # Test 4: Check task registration
    log("\n=== Task Registration ===")
    try:
        registered_tasks = list(celery_app.tasks.keys())
        log(f"✓ Found {len(registered_tasks)} registered tasks")
        
        # Look for VOD tasks
        vod_tasks = [task for task in registered_tasks if 'vod_processing' in task]
        log(f"  - VOD tasks: {vod_tasks}")
        
        # Check for cleanup task specifically
        cleanup_task = 'vod_processing.cleanup_temp_files'
        if cleanup_task in registered_tasks:
            log(f"✓ {cleanup_task} is registered")
        else:
            log(f"✗ {cleanup_task} is NOT registered", "ERROR")
            
    except Exception as e:
        log(f"✗ Task registration check failed: {e}", "ERROR")
        return 1
    
    # Test 5: Test task submission
    log("\n=== Task Submission Test ===")
    try:
        from core.tasks.vod_processing import cleanup_temp_files
        
        # Submit task
        result = cleanup_temp_files.delay()
        log(f"✓ Task submitted successfully")
        log(f"  - Result type: {type(result)}")
        log(f"  - Result ID: {result.id}")
        
        # Check if it's a proper AsyncResult
        from celery.result import AsyncResult
        if isinstance(result, AsyncResult):
            log("✓ Result is proper AsyncResult object")
            log(f"  - Has ready method: {hasattr(result, 'ready')}")
            log(f"  - Has get method: {hasattr(result, 'get')}")
            log(f"  - Has status method: {hasattr(result, 'status')}")
        else:
            log("✗ Result is NOT AsyncResult object", "ERROR")
            log(f"  - Expected: AsyncResult, Got: {type(result)}")
            
    except Exception as e:
        log(f"✗ Task submission test failed: {e}", "ERROR")
        return 1
    
    log("\n" + "=" * 50)
    log("Debug completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 