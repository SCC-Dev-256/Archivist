#!/usr/bin/env python3
"""
Test script to verify Celery worker startup functionality
"""

import subprocess
import time
import psutil
import sys
from pathlib import Path

def check_worker_running():
    """Check if Celery worker is running."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if (proc.info['cmdline'] and 
            'celery' in proc.info['cmdline'] and 
            'worker' in proc.info['cmdline'] and
            proc.is_running()):
            return True
    return False

def test_worker_startup():
    """Test worker startup using the dedicated script."""
    print("🧪 Testing Celery Worker Startup")
    print("=" * 40)
    
    # Stop any existing workers
    print("1. Stopping existing workers...")
    subprocess.run(["pkill", "-f", "celery.*worker"], capture_output=True)
    time.sleep(2)
    
    if check_worker_running():
        print("❌ Workers still running after stop")
        return False
    
    print("✅ Workers stopped")
    
    # Test the dedicated startup script
    print("2. Testing dedicated startup script...")
    worker_script = Path("scripts/deployment/start_celery_worker.sh")
    
    if not worker_script.exists():
        print("❌ Worker startup script not found")
        return False
    
    # Start worker in background
    process = subprocess.Popen(
        [str(worker_script), "--concurrency", "2"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for worker to start
    print("3. Waiting for worker to start...")
    for attempt in range(15):
        time.sleep(1)
        if check_worker_running():
            print("✅ Worker started successfully")
            
            # Stop the worker
            print("4. Stopping worker...")
            subprocess.run(["pkill", "-f", "celery.*worker"], capture_output=True)
            time.sleep(2)
            
            if not check_worker_running():
                print("✅ Worker stopped successfully")
                return True
            else:
                print("❌ Worker failed to stop")
                return False
    
    print("❌ Worker failed to start within timeout")
    return False

def test_unified_startup():
    """Test the unified startup system."""
    print("\n🧪 Testing Unified Startup System")
    print("=" * 40)
    
    # Stop any existing processes
    print("1. Stopping existing processes...")
    subprocess.run(["pkill", "-f", "start_archivist_unified"], capture_output=True)
    subprocess.run(["pkill", "-f", "celery.*worker"], capture_output=True)
    time.sleep(2)
    
    # Test dry-run first
    print("2. Testing dry-run...")
    result = subprocess.run(
        ["./start_archivist.sh", "complete", "--dry-run"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Dry-run successful")
    else:
        print("❌ Dry-run failed")
        print(f"Error: {result.stderr}")
        return False
    
    # Test actual startup (briefly)
    print("3. Testing actual startup (5 seconds)...")
    process = subprocess.Popen(
        ["./start_archivist.sh", "complete"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait 5 seconds
    time.sleep(5)
    
    # Check if services are running
    services_running = {
        "celery_worker": check_worker_running(),
        "celery_beat": any("celery.*beat" in str(proc.info['cmdline']) for proc in psutil.process_iter(['pid', 'cmdline']) if proc.info['cmdline'])
    }
    
    print("4. Service status:")
    for service, running in services_running.items():
        status = "✅ Running" if running else "❌ Not running"
        print(f"   {service}: {status}")
    
    # Stop the startup process
    print("5. Stopping startup process...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    
    # Clean up
    subprocess.run(["pkill", "-f", "celery"], capture_output=True)
    
    return any(services_running.values())

def main():
    """Main test function."""
    print("🚀 Archivist Worker Startup Test Suite")
    print("=" * 50)
    
    # Test 1: Dedicated worker script
    test1_passed = test_worker_startup()
    
    # Test 2: Unified startup system
    test2_passed = test_unified_startup()
    
    # Summary
    print("\n📊 Test Results")
    print("=" * 20)
    print(f"Worker Script Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Unified System Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Worker startup is working correctly.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 