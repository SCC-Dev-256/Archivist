#!/usr/bin/env python3
"""
Test script to verify Celery beat health check logic
"""

import psutil

def check_celery_beat_health():
    """Test the same health check logic as the startup manager."""
    print("🔍 Testing Celery beat health check...")
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if (proc.info['cmdline'] and 
                any('celery' in arg for arg in proc.info['cmdline']) and
                any('beat' in arg for arg in proc.info['cmdline']) and
                proc.is_running()):
                print(f"✅ Found Celery beat process: {proc.info['pid']} (name: {proc.info['name']})")
                print(f"   Command: {' '.join(proc.info['cmdline'])}")
                return True
        print("❌ No Celery beat found")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def debug_beat_processes():
    """Debug beat process detection."""
    print("🔍 Debugging beat process detection...")
    
    # List all processes with 'celery' in command line
    print("\nProcesses with 'celery' in command line:")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if (proc.info['cmdline'] and 
            any('celery' in arg for arg in proc.info['cmdline'])):
            print(f"  PID {proc.info['pid']} (name: {proc.info['name']}): {' '.join(proc.info['cmdline'])}")
    
    # List all processes with 'beat' in command line
    print("\nProcesses with 'beat' in command line:")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if (proc.info['cmdline'] and 
            any('beat' in arg for arg in proc.info['cmdline'])):
            print(f"  PID {proc.info['pid']} (name: {proc.info['name']}): {' '.join(proc.info['cmdline'])}")

if __name__ == "__main__":
    print("🧪 Testing Celery Beat Health Check")
    print("=" * 40)
    
    debug_beat_processes()
    print("\n" + "=" * 40)
    result = check_celery_beat_health()
    print(f"\nResult: {'✅ SUCCESS' if result else '❌ FAILED'}") 