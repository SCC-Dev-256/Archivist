#!/usr/bin/env python3
"""
Final Celery Test

This script tests if we can get Celery to run in normal mode and return proper AsyncResult objects.
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
    log("Final Celery Test")
    log("=" * 50)
    
    # Test 1: Check if Celery is running in eager mode
    log("\n=== Checking Celery Mode ===")
    try:
        from core.tasks import celery_app
        
        # Check if task_always_eager is set
        task_always_eager = getattr(celery_app.conf, 'task_always_eager', None)
        log(f"Task always eager: {task_always_eager}")
        
        # Check if broker is accessible
        try:
            import redis
            r = redis.from_url('redis://localhost:6379/0')
            r.ping()
            log("✓ Redis is accessible")
        except Exception as e:
            log(f"✗ Redis not accessible: {e}", "ERROR")
            
    except Exception as e:
        log(f"✗ Celery mode check failed: {e}", "ERROR")
        return 1
    
    # Test 2: Try to force normal mode
    log("\n=== Forcing Normal Mode ===")
    try:
        # Set task_always_eager to False explicitly
        celery_app.conf.task_always_eager = False
        celery_app.conf.task_eager_propagates = False
        log("✓ Set task_always_eager to False")
        
        # Test task submission
        from core.tasks.vod_processing import cleanup_temp_files
        
        result = cleanup_temp_files.delay()
        log(f"✓ Task submitted: {type(result)}")
        
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
            log("✗ Result is still NOT AsyncResult object", "ERROR")
            log(f"  - Expected: AsyncResult, Got: {type(result)}")
            
    except Exception as e:
        log(f"✗ Normal mode test failed: {e}", "ERROR")
        return 1
    
    # Test 3: Check if there's a worker running
    log("\n=== Checking for Celery Worker ===")
    try:
        import subprocess
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'celery' in result.stdout.lower():
            log("✓ Celery worker process found")
        else:
            log("⚠ No Celery worker process found", "WARNING")
            log("  - This might be why tasks are running in eager mode")
            
    except Exception as e:
        log(f"✗ Worker check failed: {e}", "ERROR")
    
    # Test 4: Try to start a worker
    log("\n=== Testing Worker Start ===")
    try:
        import subprocess
        import time
        
        # Start a worker in the background
        worker_process = subprocess.Popen([
            'celery', '-A', 'core.tasks', 'worker', 
            '--loglevel=info', '--concurrency=1'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for worker to start
        time.sleep(3)
        
        # Test task submission
        result = cleanup_temp_files.delay()
        log(f"✓ Task submitted with worker: {type(result)}")
        
        from celery.result import AsyncResult
        if isinstance(result, AsyncResult):
            log("✓ Result is AsyncResult object with worker")
            
            # Wait for completion
            timeout = 10
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if result.ready():
                    break
                time.sleep(0.5)
            
            if result.ready():
                task_result = result.get(timeout=5)
                log(f"✓ Task completed with worker: {task_result}")
            else:
                log("⚠ Task did not complete within timeout", "WARNING")
        else:
            log("✗ Result is still NOT AsyncResult object", "ERROR")
        
        # Stop the worker
        worker_process.terminate()
        worker_process.wait()
        log("✓ Worker stopped")
        
    except Exception as e:
        log(f"✗ Worker test failed: {e}", "ERROR")
        return 1
    
    log("\n" + "=" * 50)
    log("Final Celery test completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 