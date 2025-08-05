#!/usr/bin/env python3
"""
Debug script to test Celery worker health check logic
"""

import psutil
import time
import subprocess
import os

def check_celery_worker_health():
    """Test the same health check logic as the startup manager."""
    print("🔍 Testing Celery worker health check...")
    
    try:
        # First check if the process is running
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if (proc.info['cmdline'] and 
                'celery' in proc.info['cmdline'] and 
                'worker' in proc.info['cmdline'] and
                proc.is_running()):
                print(f"✅ Found Celery worker process: {proc.info['pid']}")
                print(f"   Command: {' '.join(proc.info['cmdline'])}")
                return True
        
        # Also check for any Python process running celery worker
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if (proc.info['name'] == 'python' and 
                proc.info['cmdline'] and 
                any('celery' in arg for arg in proc.info['cmdline']) and
                any('worker' in arg for arg in proc.info['cmdline']) and
                proc.is_running()):
                print(f"✅ Found Python Celery worker process: {proc.info['pid']}")
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

def start_celery_worker():
    """Start a Celery worker using the same command as startup manager."""
    print("🚀 Starting Celery worker...")
    
    venv_celery = os.path.join("/opt/Archivist", "venv_py311", "bin", "celery")
    worker_cmd = [
        venv_celery, "-A", "core.tasks", "worker",
        "--loglevel=info",
        "--concurrency=4",
        "--hostname=vod_worker@%h",
        "--queues=vod_processing,default"
    ]
    
    print(f"Command: {' '.join(worker_cmd)}")
    
    worker_process = subprocess.Popen(
        worker_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/opt/Archivist"
    )
    
    return worker_process

def main():
    print("🧪 Celery Worker Health Check Debug")
    print("=" * 40)
    
    # Check initial state
    print("\n1. Initial health check:")
    initial_health = check_celery_worker_health()
    
    if initial_health:
        print("❌ Worker already running, stopping it first...")
        subprocess.run(["pkill", "-f", "celery.*worker"], capture_output=True)
        time.sleep(2)
    
    # Start worker
    print("\n2. Starting worker...")
    worker_process = start_celery_worker()
    
    # Test health check multiple times
    print("\n3. Testing health check during startup:")
    for attempt in range(30):
        time.sleep(1)
        print(f"   Attempt {attempt + 1}: ", end="")
        
        # Check if process died first
        if worker_process.poll() is not None:
            stdout, stderr = worker_process.communicate()
            print(f"❌ Worker process died!")
            print(f"   stdout: {stdout.decode()}")
            print(f"   stderr: {stderr.decode()}")
            break
        
        if check_celery_worker_health():
            print("✅ SUCCESS!")
            break
        else:
            print("❌ Not ready yet")
    else:
        print("❌ Worker failed to start within 30 seconds")
        # Get any output from the process
        try:
            stdout, stderr = worker_process.communicate(timeout=1)
            if stdout:
                print(f"   stdout: {stdout.decode()}")
            if stderr:
                print(f"   stderr: {stderr.decode()}")
        except subprocess.TimeoutExpired:
            worker_process.kill()
            print("   Process still running but not detected by health check")
    
    # Cleanup
    print("\n4. Cleanup...")
    subprocess.run(["pkill", "-f", "celery.*worker"], capture_output=True)
    time.sleep(2)
    
    print("\n✅ Debug complete!")

if __name__ == "__main__":
    main() 