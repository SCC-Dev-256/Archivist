#!/usr/bin/env python3
"""
Debug Celery Hang Test

This script tests if celery_app creation is causing the hanging.
"""

import sys
import time
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_celery_import():
    """Test if celery import hangs."""
    print("🔍 Testing celery import...")
    start_time = time.time()
    
    try:
        # Set testing environment
        os.environ['TESTING'] = 'true'
        
        # Try to import core.tasks
        import core.tasks
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ core.tasks import: SUCCESS ({duration:.2f}s)")
        return True
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ core.tasks import: FAILED ({duration:.2f}s) - {e}")
        return False

def test_redis_connection():
    """Test if Redis connection is the issue."""
    print("🔍 Testing Redis connection...")
    
    try:
        from core.config import REDIS_URL
        print(f"✅ REDIS_URL: {REDIS_URL}")
        
        # Try to connect to Redis
        import redis
        r = redis.from_url(REDIS_URL)
        r.ping()
        print("✅ Redis connection: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ Redis connection: FAILED - {e}")
        return False

def main():
    """Run the debug tests."""
    print("🔍 DEBUGGING CELERY HANG")
    print("=" * 50)
    
    # Test Redis connection first
    redis_ok = test_redis_connection()
    
    if not redis_ok:
        print("\n⚠️  Redis is not available - this is likely causing the hang!")
        print("The celery_app tries to connect to Redis at import time.")
        print("If Redis is not running, it will hang waiting for connection.")
    
    # Test celery import
    celery_ok = test_celery_import()
    
    print("\n" + "=" * 50)
    if celery_ok:
        print("✅ Celery import works (Redis is available)")
    else:
        print("❌ Celery import fails (Redis is not available)")

if __name__ == "__main__":
    main() 