#!/usr/bin/env python3
"""
Test script to verify Celery worker health check
"""

import psutil

def check_celery_worker_health():
    """Test the same health check logic as the startup manager."""
    print("🔍 Testing Celery worker health check...")
    
    try:
        # Check for any Python or Celery process running celery worker
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if ((proc.info['name'] == 'python' or proc.info['name'] == 'celery') and 
                proc.info['cmdline'] and 
                any('celery' in arg for arg in proc.info['cmdline']) and
                any('worker' in arg for arg in proc.info['cmdline']) and
                proc.is_running()):
                print(f"✅ Found Celery worker process: {proc.info['pid']}")
                print(f"   Command: {' '.join(proc.info['cmdline'])}")
                return True
        
        # If no process found, try the inspect method as fallback
        try:
            from core.tasks import celery_app
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            if stats:
                print(f"✅ Found Celery workers via inspect: {list(stats.keys())}")
                return True
        except Exception as e:
            print(f"❌ Celery inspect failed: {e}")
        
        print("❌ No Celery worker found")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Celery Worker Health Check")
    print("=" * 40)
    
    result = check_celery_worker_health()
    print(f"\nResult: {'✅ SUCCESS' if result else '❌ FAILED'}") 