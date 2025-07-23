#!/usr/bin/env python3
"""
Test API fixes and improvements.
"""

import os
import sys
import time
import requests
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Configure logging for tests
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

def test_api_health():
    """Test API health endpoint."""
    logger.info("🏥 Testing API Health...")
    
    try:
        response = requests.get("http://localhost:5000/health", timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ API health check passed")
            return True
        else:
            logger.error(f"❌ API health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Could not connect to API server")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def test_transcription_endpoint():
    """Test transcription endpoint."""
    logger.info("🎤 Testing Transcription Endpoint...")
    
    try:
        response = requests.get("http://localhost:5000/api/transcribe", timeout=10)
        
        if response.status_code == 405:  # Method Not Allowed (expected for GET)
            logger.info("✅ Transcription endpoint exists (correctly rejects GET)")
            return True
        elif response.status_code == 404:
            logger.warning("⚠️ Transcription endpoint not found")
            return False
        else:
            logger.info(f"✅ Transcription endpoint responded: {response.status_code}")
            return True
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Could not connect to transcription endpoint")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def test_queue_endpoint():
    """Test queue endpoint."""
    logger.info("📋 Testing Queue Endpoint...")
    
    try:
        response = requests.get("http://localhost:5000/api/queue", timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ Queue endpoint working")
            return True
        elif response.status_code == 404:
            logger.warning("⚠️ Queue endpoint not found")
            return False
        else:
            logger.info(f"✅ Queue endpoint responded: {response.status_code}")
            return True
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Could not connect to queue endpoint")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def main():
    """Run all API fix tests."""
    logger.info("🚀 Starting API Fix Tests")
    logger.info("=" * 50)
    
    tests = [
        ("API Health", test_api_health),
        ("Transcription Endpoint", test_transcription_endpoint),
        ("Queue Endpoint", test_queue_endpoint)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ Test '{test_name}' failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("=" * 50)
    logger.info("📊 API Fix Test Results:")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {status} {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All API fix tests passed!")
        return True
    else:
        logger.error("❌ Some API fix tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 