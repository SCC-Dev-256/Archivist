#!/usr/bin/env python3
"""
Test script to verify API fixes for hanging issues.
"""

import os
import pytest
import requests
import time
import signal
from contextlib import contextmanager

@contextmanager
def timeout(seconds):
    """Context manager for timeout handling."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set the signal handler and a 5-second alarm
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

# Provide concrete targets for pytest parameterization
_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5050")
_TARGETS = [
    (f"{_BASE_URL}/", "Main page"),
    (f"{_BASE_URL}/api/browse", "Browse API"),
    (f"{_BASE_URL}/api/metrics", "Metrics API"),
    (f"{_BASE_URL}/api/health", "Health API"),
    (f"{_BASE_URL}/api/queue", "Queue API"),
    (f"{_BASE_URL}/api/transcriptions", "Transcriptions API"),
]

@pytest.mark.parametrize("url,name", _TARGETS)
def test_endpoint(url, name, timeout_seconds=10):
    """Test an endpoint with timeout protection."""
    print(f"\n🔍 Testing {name}...")
    print(f"   URL: {url}")
    
    try:
        with timeout(timeout_seconds):
            start_time = time.time()
            response = requests.get(url, timeout=timeout_seconds)
            end_time = time.time()
            
            duration = end_time - start_time
            print(f"   ✅ Response: {response.status_code} (took {duration:.2f}s)")
            
            if response.status_code == 200:
                print(f"   ✅ Success: {name} is working")
                return True
            else:
                print(f"   ❌ Error: {response.text}")
                return False
                
    except TimeoutError:
        print(f"   ❌ Timeout: {name} took too long (> {timeout_seconds}s)")
        return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection Error: Could not connect to {url}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Testing API fixes for hanging issues...")
    print("=" * 60)
    
    base_url = "http://localhost:5050"
    
    # Test endpoints that were causing hanging issues
    tests = [
        (f"{base_url}/", "Main page"),
        (f"{base_url}/api/browse", "Browse API"),
        (f"{base_url}/api/metrics", "Metrics API"),
        (f"{base_url}/api/health", "Health API"),
        (f"{base_url}/api/queue", "Queue API"),
        (f"{base_url}/api/transcriptions", "Transcriptions API"),
    ]
    
    results = []
    for url, name in tests:
        result = test_endpoint(url, name)
        results.append((name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! API fixes are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs for more details.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 