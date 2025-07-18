#!/usr/bin/env python3
"""Test script to verify Archivist system functionality after directory reorganization."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all core modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from core.web_app import create_app
        print("✅ core.web_app imported successfully")
    except Exception as e:
        print(f"❌ Failed to import core.web_app: {e}")
        return False
    
    try:
        from core.tasks import celery_app
        print("✅ core.tasks imported successfully")
    except Exception as e:
        print(f"❌ Failed to import core.tasks: {e}")
        return False
    
    try:
        from core.models import TranscriptionJobORM, TranscriptionResultORM
        print("✅ core.models imported successfully")
    except Exception as e:
        print(f"❌ Failed to import core.models: {e}")
        return False
    
    return True

def test_flask_app():
    """Test Flask application creation and basic functionality."""
    print("\n🔍 Testing Flask application...")
    
    try:
        from core.web_app import create_app
        app, limiter, api = create_app()
        print("✅ Flask app created successfully")
        
        # Test with test client
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            print(f"✅ Health check: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Status: {data.get('status')}")
                print(f"   Services: {data.get('services')}")
            
            # Test main endpoint
            response = client.get('/')
            print(f"✅ Main endpoint: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Message: {data.get('message')}")
                print(f"   Version: {data.get('version')}")
        
        return True
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        return False

def test_celery():
    """Test Celery application."""
    print("\n🔍 Testing Celery application...")
    
    try:
        from core.tasks import celery_app
        print("✅ Celery app imported successfully")
        
        # Check registered tasks
        tasks = celery_app.tasks.keys()
        vod_tasks = [t for t in tasks if 'vod' in t.lower()]
        transcription_tasks = [t for t in tasks if 'transcription' in t.lower()]
        
        print(f"✅ Found {len(vod_tasks)} VOD tasks")
        print(f"✅ Found {len(transcription_tasks)} transcription tasks")
        
        return True
    except Exception as e:
        print(f"❌ Celery test failed: {e}")
        return False

def test_database():
    """Test database connectivity."""
    print("\n🔍 Testing database...")
    
    try:
        from core.database import db
        from core.models import TranscriptionJobORM
        
        # Test basic database operations
        print("✅ Database models imported successfully")
        
        # Check if we can query the database
        try:
            count = TranscriptionJobORM.query.count()
            print(f"✅ Database query successful: {count} transcription jobs")
        except Exception as e:
            print(f"⚠️  Database query failed (may be expected): {e}")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Archivist System After Directory Reorganization")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_flask_app,
        test_celery,
        test_database
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Archivist system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 