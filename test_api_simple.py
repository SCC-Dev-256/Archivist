#!/usr/bin/env python3
"""
Simple API test script to check if Flask server is responding.
"""

import requests
import time

def test_api_health():
    """Test the health endpoint."""
    print("🔍 Testing API health endpoint...")
    
    try:
        response = requests.get("http://127.0.0.1:5050/api/health", timeout=5)
        print(f"✅ Health API Response Status: {response.status_code}")
        print(f"✅ Response: {response.text}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server")
        return False
    except requests.exceptions.Timeout:
        print("❌ API request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_queue_api():
    """Test the queue endpoint."""
    print("\n🔍 Testing queue API endpoint...")
    
    try:
        response = requests.get("http://127.0.0.1:5050/api/queue", timeout=10)
        print(f"✅ Queue API Response Status: {response.status_code}")
        print(f"✅ Response: {response.text[:200]}...")  # First 200 chars
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server")
        return False
    except requests.exceptions.Timeout:
        print("❌ API request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run simple API tests."""
    print("🚀 Starting Simple API Tests\n")
    
    tests = [
        ("API Health", test_api_health),
        ("Queue API", test_queue_api),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All API tests passed!")
        return 0
    else:
        print("⚠️  Some API tests failed.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 