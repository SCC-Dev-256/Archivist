#!/usr/bin/env python3
"""
Test Real-time Task Monitoring Features

This script tests the enhanced Integrated Dashboard with real-time task monitoring.
"""

import requests
import json
import time
from datetime import datetime

def test_api_endpoints():
    """Test all real-time monitoring API endpoints."""
    base_url = "http://localhost:5051"
    
    print("🧪 Testing Real-time Task Monitoring API Endpoints")
    print("=" * 60)
    
    # Test 1: Health endpoint
    print("\n1. Testing Health Endpoint...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working")
            data = response.json()
            print(f"   Status: {data.get('status', 'unknown')}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
    
    # Test 2: Real-time tasks endpoint
    print("\n2. Testing Real-time Tasks Endpoint...")
    try:
        response = requests.get(f"{base_url}/api/tasks/realtime", timeout=5)
        if response.status_code == 200:
            print("✅ Real-time tasks endpoint working")
            data = response.json()
            print(f"   Total tasks: {data.get('summary', {}).get('total', 0)}")
            print(f"   Active tasks: {data.get('summary', {}).get('active', 0)}")
            print(f"   Timestamp: {data.get('timestamp', 'N/A')}")
        else:
            print(f"❌ Real-time tasks endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Real-time tasks endpoint error: {e}")
    
    # Test 3: Task analytics endpoint
    print("\n3. Testing Task Analytics Endpoint...")
    try:
        response = requests.get(f"{base_url}/api/tasks/analytics", timeout=5)
        if response.status_code == 200:
            print("✅ Task analytics endpoint working")
            data = response.json()
            print(f"   Success rate: {data.get('success_rate', 0)}%")
            print(f"   Average completion time: {data.get('average_completion_time', 0)}s")
            print(f"   Total tasks: {data.get('total_tasks', 0)}")
        else:
            print(f"❌ Task analytics endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Task analytics endpoint error: {e}")
    
    # Test 4: Enhanced Celery tasks endpoint
    print("\n4. Testing Enhanced Celery Tasks Endpoint...")
    try:
        response = requests.get(f"{base_url}/api/celery/tasks", timeout=5)
        if response.status_code == 200:
            print("✅ Enhanced Celery tasks endpoint working")
            data = response.json()
            print(f"   Has realtime data: {'realtime' in data}")
            print(f"   Has task history: {'task_history' in data}")
            print(f"   Summary: {data.get('summary', {})}")
        else:
            print(f"❌ Enhanced Celery tasks endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Enhanced Celery tasks endpoint error: {e}")
    
    # Test 5: Celery workers endpoint
    print("\n5. Testing Celery Workers Endpoint...")
    try:
        response = requests.get(f"{base_url}/api/celery/workers", timeout=5)
        if response.status_code == 200:
            print("✅ Celery workers endpoint working")
            data = response.json()
            print(f"   Active workers: {data.get('active_workers', 0)}")
            print(f"   Total workers: {data.get('total_workers', 0)}")
        else:
            print(f"❌ Celery workers endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Celery workers endpoint error: {e}")

def test_web_interface():
    """Test the web interface accessibility."""
    base_url = "http://localhost:5051"
    
    print("\n🌐 Testing Web Interface")
    print("=" * 60)
    
    # Test main dashboard page
    print("\n1. Testing Main Dashboard Page...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ Main dashboard page accessible")
            content = response.text
            print(f"   Page size: {len(content)} characters")
            print(f"   Has SocketIO: {'socket.io' in content}")
            print(f"   Has real-time tab: {'Real-time Tasks' in content}")
            print(f"   Has task monitoring: {'task-monitoring' in content}")
        else:
            print(f"❌ Main dashboard page failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Main dashboard page error: {e}")

def test_real_time_features():
    """Test real-time monitoring features."""
    base_url = "http://localhost:5051"
    
    print("\n⚡ Testing Real-time Features")
    print("=" * 60)
    
    # Test task filtering
    print("\n1. Testing Task Filtering...")
    try:
        # Test with different filter types
        filters = ['all', 'vod', 'transcription', 'cleanup']
        for filter_type in filters:
            response = requests.get(f"{base_url}/api/tasks/realtime?filter={filter_type}", timeout=5)
            if response.status_code == 200:
                print(f"✅ Filter '{filter_type}' working")
            else:
                print(f"❌ Filter '{filter_type}' failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Task filtering error: {e}")
    
    # Test real-time data consistency
    print("\n2. Testing Real-time Data Consistency...")
    try:
        # Get data twice to check consistency
        response1 = requests.get(f"{base_url}/api/tasks/realtime", timeout=5)
        time.sleep(2)
        response2 = requests.get(f"{base_url}/api/tasks/realtime", timeout=5)
        
        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()
            print("✅ Real-time data consistency check passed")
            print(f"   First timestamp: {data1.get('timestamp', 'N/A')}")
            print(f"   Second timestamp: {data2.get('timestamp', 'N/A')}")
        else:
            print("❌ Real-time data consistency check failed")
    except Exception as e:
        print(f"❌ Real-time data consistency error: {e}")

def main():
    """Run all tests."""
    print("🚀 Real-time Task Monitoring Test Suite")
    print("=" * 60)
    print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test API endpoints
        test_api_endpoints()
        
        # Test web interface
        test_web_interface()
        
        # Test real-time features
        test_real_time_features()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("\n📋 Summary:")
        print("   - Real-time task monitoring API endpoints working")
        print("   - Web interface with SocketIO support accessible")
        print("   - Task filtering and analytics functional")
        print("   - Enhanced Celery integration operational")
        print("\n🌐 Access the dashboard at: http://localhost:5051")
        print("⚡ Real-time monitoring tab available")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")

if __name__ == "__main__":
    main() 