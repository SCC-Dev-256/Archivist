#!/usr/bin/env python3
"""
Debug script to see what processes are being detected
"""

import psutil

def debug_process_detection():
    """Debug process detection logic."""
    print("🔍 Debugging process detection...")
    
    # List all Python processes
    print("\nAll Python processes:")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if proc.info['name'] == 'python':
            print(f"  PID {proc.info['pid']}: {' '.join(proc.info['cmdline'] or [])}")
    
    # Check for Celery processes specifically
    print("\nProcesses with 'celery' in command line:")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if (proc.info['cmdline'] and 
            any('celery' in arg for arg in proc.info['cmdline'])):
            print(f"  PID {proc.info['pid']} (name: {proc.info['name']}): {' '.join(proc.info['cmdline'])}")
    
    # Check for worker processes specifically
    print("\nProcesses with 'worker' in command line:")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if (proc.info['cmdline'] and 
            any('worker' in arg for arg in proc.info['cmdline'])):
            print(f"  PID {proc.info['pid']} (name: {proc.info['name']}): {' '.join(proc.info['cmdline'])}")
    
    # Test the exact logic from startup manager
    print("\nTesting startup manager logic:")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if (proc.info['name'] == 'python' and 
            proc.info['cmdline'] and 
            any('celery' in arg for arg in proc.info['cmdline']) and
            any('worker' in arg for arg in proc.info['cmdline']) and
            proc.is_running()):
            print(f"✅ Found Python Celery worker process: {proc.info['pid']}")
            print(f"   Command: {' '.join(proc.info['cmdline'])}")
            return True
    
    print("❌ No matching processes found")
    return False

if __name__ == "__main__":
    debug_process_detection() 