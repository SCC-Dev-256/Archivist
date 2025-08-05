#!/usr/bin/env python3
"""
Test Celery Broker Configuration

This script tests the Celery broker configuration to understand why tasks are running in eager mode.
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
    log("Testing Celery Broker Configuration")
    log("=" * 50)
    
    # Test 1: Check environment
    log("\n=== Environment Check ===")
    from dotenv import load_dotenv
    load_dotenv()
    
    redis_url = os.getenv('REDIS_URL')
    log(f"REDIS_URL from env: {redis_url}")
    
    # Test 2: Check Redis connection
    log("\n=== Redis Connection Test ===")
    try:
        import redis
        r = redis.from_url(redis_url)
        r.ping()
        log("✓ Redis connection successful")
    except Exception as e:
        log(f"✗ Redis connection failed: {e}", "ERROR")
        return 1
    
    # Test 3: Check Celery app configuration
    log("\n=== Celery App Configuration ===")
    try:
        from core.tasks import celery_app
        
        log(f"App type: {type(celery_app)}")
        log(f"Broker URL: {celery_app.conf.broker_url}")
        log(f"Result backend: {celery_app.conf.result_backend}")
        log(f"Task always eager: {celery_app.conf.task_always_eager}")
        log(f"Task eager propagates: {celery_app.conf.task_eager_propagates}")
        
        # Check if broker is accessible from Celery's perspective
        try:
            from celery.backends.redis import RedisBackend
            backend = RedisBackend(redis_url)
            backend.client.ping()
            log("✓ Celery can connect to Redis backend")
        except Exception as e:
            log(f"✗ Celery cannot connect to Redis backend: {e}", "ERROR")
            
    except Exception as e:
        log(f"✗ Celery app configuration check failed: {e}", "ERROR")
        return 1
    
    # Test 4: Test task submission with explicit broker
    log("\n=== Task Submission Test ===")
    try:
        from celery import Celery
        
        # Create a new Celery app with explicit configuration
        test_app = Celery(
            "test_app",
            broker=redis_url,
            backend=redis_url,
        )
        
        test_app.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            result_expires=86400,
            timezone="UTC",
            enable_utc=True,
        )
        
        @test_app.task
        def test_task():
            return {"success": True, "message": "Test task completed"}
        
        # Submit task
        result = test_task.delay()
        log(f"✓ Test task submitted")
        log(f"  - Result type: {type(result)}")
        log(f"  - Result ID: {result.id}")
        
        # Check if it's AsyncResult
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
        log(f"✗ Task submission test failed: {e}", "ERROR")
        return 1
    
    # Test 5: Check if the issue is with the main app
    log("\n=== Main App Task Test ===")
    try:
        from core.tasks.vod_processing import cleanup_temp_files
        
        # Check task configuration
        log(f"Task name: {cleanup_temp_files.name}")
        log(f"Task app: {cleanup_temp_files.app}")
        log(f"Task broker: {cleanup_temp_files.app.conf.broker_url}")
        log(f"Task backend: {cleanup_temp_files.app.conf.result_backend}")
        
        # Submit task
        result = cleanup_temp_files.delay()
        log(f"✓ Main app task submitted")
        log(f"  - Result type: {type(result)}")
        log(f"  - Result ID: {result.id}")
        
        # Check if it's AsyncResult
        from celery.result import AsyncResult
        if isinstance(result, AsyncResult):
            log("✓ Main app result is AsyncResult object")
        else:
            log("✗ Main app result is NOT AsyncResult object", "ERROR")
            log(f"  - Expected: AsyncResult, Got: {type(result)}")
            
    except Exception as e:
        log(f"✗ Main app task test failed: {e}", "ERROR")
        return 1
    
    log("\n" + "=" * 50)
    log("Broker configuration test completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 