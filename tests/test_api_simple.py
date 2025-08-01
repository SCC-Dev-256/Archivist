#!/usr/bin/env python3
"""
Simple API test script for the Archivist application.
Tests basic API functionality and endpoints.
"""

import os
import sys
import requests
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Configure logging for tests
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

# Configuration
API_BASE_URL = "http://localhost:5000"
TEST_TIMEOUT = 30

def test_api_health():
    """Test API health endpoint."""
    logger.info("🏥 Testing API Health...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            logger.info("✅ API health check passed")
            return True
        else:
            logger.error(f"❌ API health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Could not connect to API server")
        return False
    except requests.exceptions.Timeout:
        logger.error("❌ API health check timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in API health check: {e}")
        return False

def test_transcription_endpoint():
    """Test transcription endpoint."""
    logger.info("🎤 Testing Transcription Endpoint...")
    
    try:
        # Test endpoint availability
        response = requests.get(f"{API_BASE_URL}/api/transcribe", timeout=TEST_TIMEOUT)
        
        # Should return 405 Method Not Allowed for GET (endpoint expects POST)
        if response.status_code == 405:
            logger.info("✅ Transcription endpoint exists (correctly rejects GET)")
            return True
        elif response.status_code == 404:
            logger.warning("⚠️  Transcription endpoint not found")
            return False
        else:
            logger.info(f"✅ Transcription endpoint responded: {response.status_code}")
            return True
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Could not connect to transcription endpoint")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing transcription endpoint: {e}")
        return False

def test_queue_endpoint():
    """Test queue endpoint."""
    logger.info("📋 Testing Queue Endpoint...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/queue", timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            logger.info("✅ Queue endpoint working")
            return True
        elif response.status_code == 404:
            logger.warning("⚠️  Queue endpoint not found")
            return False
        else:
            logger.info(f"✅ Queue endpoint responded: {response.status_code}")
            return True
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Could not connect to queue endpoint")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing queue endpoint: {e}")
        return False

def test_cablecast_endpoint():
    """Test Cablecast endpoint."""
    logger.info("📺 Testing Cablecast Endpoint...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/cablecast/shows", timeout=TEST_TIMEOUT)
        
        if response.status_code == 200:
            logger.info("✅ Cablecast endpoint working")
            return True
        elif response.status_code == 401:
            logger.warning("⚠️  Cablecast endpoint requires authentication")
            return True  # This is expected behavior
        elif response.status_code == 404:
            logger.warning("⚠️  Cablecast endpoint not found")
            return False
        else:
            logger.info(f"✅ Cablecast endpoint responded: {response.status_code}")
            return True
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Could not connect to Cablecast endpoint")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing Cablecast endpoint: {e}")
        return False

def main():
    """Run all API tests."""
    logger.info("🚀 Starting Simple API Tests")
    logger.info("=" * 50)
    
    # Test API health
    health_ok = test_api_health()
    
    # Test transcription endpoint
    transcription_ok = test_transcription_endpoint()
    
    # Test queue endpoint
    queue_ok = test_queue_endpoint()
    
    # Test Cablecast endpoint
    cablecast_ok = test_cablecast_endpoint()
    
    # Summary
    logger.info("=" * 50)
    logger.info("📊 API Test Results Summary:")
    logger.info(f"   Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    logger.info(f"   Transcription: {'✅ PASS' if transcription_ok else '❌ FAIL'}")
    logger.info(f"   Queue: {'✅ PASS' if queue_ok else '❌ FAIL'}")
    logger.info(f"   Cablecast: {'✅ PASS' if cablecast_ok else '❌ FAIL'}")
    
    if health_ok and transcription_ok and queue_ok and cablecast_ok:
        logger.info("🎉 All API tests passed!")
        return True
    else:
        logger.error("❌ Some API tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 