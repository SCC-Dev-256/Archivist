#!/usr/bin/env python3
"""Test script for Cablecast API connection.

This script tests the connection to the Cablecast API and verifies
that the integration is working properly.

Usage:
    python test_cablecast_api_connection.py
"""

import os
import sys
from loguru import logger

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_cablecast_configuration():
    """Test that Cablecast configuration is properly set"""
    logger.info("Testing Cablecast configuration...")
    
    try:
        from core.config import CABLECAST_API_URL, CABLECAST_API_KEY, CABLECAST_LOCATION_ID
        
        # Check if API URL is configured
        if CABLECAST_API_URL == "https://your-cablecast-instance.com/api":
            logger.error("✗ CABLECAST_API_URL is not configured")
            return False
        
        # Check if API key is configured
        if CABLECAST_API_KEY == "your_cablecast_api_key_here":
            logger.error("✗ CABLECAST_API_KEY is not configured")
            return False
        
        # Check if location ID is configured
        if CABLECAST_LOCATION_ID == "1":
            logger.warning("⚠ CABLECAST_LOCATION_ID is using default value")
        
        logger.info(f"✓ API URL: {CABLECAST_API_URL}")
        logger.info(f"✓ API Key: {'*' * len(CABLECAST_API_KEY)} (configured)")
        logger.info(f"✓ Location ID: {CABLECAST_LOCATION_ID}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Configuration test failed: {e}")
        return False

def test_cablecast_connection():
    """Test connection to Cablecast API"""
    logger.info("Testing Cablecast API connection...")
    
    try:
        from core.cablecast_client import CablecastAPIClient
        
        client = CablecastAPIClient()
        
        # Test connection by getting shows
        shows = client.get_shows()
        
        if shows is not None:
            logger.info(f"✓ Successfully connected to Cablecast API")
            logger.info(f"✓ Found {len(shows)} shows")
            return True
        else:
            logger.error("✗ Failed to connect to Cablecast API")
            return False
            
    except Exception as e:
        logger.error(f"✗ Connection test failed: {e}")
        return False

def test_cablecast_endpoints():
    """Test Cablecast API endpoints"""
    logger.info("Testing Cablecast API endpoints...")
    
    try:
        from core.cablecast_client import CablecastAPIClient
        
        client = CablecastAPIClient()
        
        # Test getting locations
        locations = client.get_locations()
        if locations:
            logger.info(f"✓ Locations endpoint working ({len(locations)} locations)")
        else:
            logger.warning("⚠ Locations endpoint returned no data")
        
        # Test getting VOD qualities
        qualities = client.get_vod_qualities()
        if qualities:
            logger.info(f"✓ VOD qualities endpoint working ({len(qualities)} qualities)")
        else:
            logger.warning("⚠ VOD qualities endpoint returned no data")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Endpoints test failed: {e}")
        return False

def test_vod_integration():
    """Test VOD integration components"""
    logger.info("Testing VOD integration components...")
    
    try:
        from core.vod_content_manager import VODContentManager
        from core.cablecast_integration import CablecastIntegrationService
        
        # Test VOD content manager
        vod_manager = VODContentManager()
        logger.info("✓ VOD content manager initialized")
        
        # Test Cablecast integration service
        integration_service = CablecastIntegrationService()
        logger.info("✓ Cablecast integration service initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ VOD integration test failed: {e}")
        return False

def test_database_integration():
    """Test database integration"""
    logger.info("Testing database integration...")
    
    try:
        from core.app import create_app
        from core import db
        from core.models import CablecastShowORM
        
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            # Test that the table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'cablecast_shows' in tables:
                logger.info("✓ cablecast_shows table exists")
                return True
            else:
                logger.error("✗ cablecast_shows table not found")
                return False
                
    except Exception as e:
        logger.error(f"✗ Database integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting Cablecast API integration tests...")
    
    tests = [
        ("Configuration", test_cablecast_configuration),
        ("Database Integration", test_database_integration),
        ("VOD Integration", test_vod_integration),
        ("API Connection", test_cablecast_connection),
        ("API Endpoints", test_cablecast_endpoints),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"✗ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY")
    logger.info("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Cablecast integration is ready.")
        return True
    else:
        logger.error("❌ Some tests failed. Please check the configuration.")
        return False

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    success = main()
    sys.exit(0 if success else 1) 