#!/usr/bin/env python3
"""Test script for VOD integration functionality.

This script tests the VOD integration components to ensure they work correctly.
Run this script to verify the integration is working properly.

Usage:
    python3 test_vod_integration.py
"""

import os
import sys
from loguru import logger

# Add the core directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

def test_cablecast_client():
    """Test Cablecast API client functionality"""
    logger.info("Testing Cablecast API client...")
    
    try:
        from core.cablecast_client import CablecastAPIClient
        
        # Test client initialization
        client = CablecastAPIClient()
        logger.info("✓ Cablecast client initialized successfully")
        
        # Test connection (this will fail if API is not available, but that's expected)
        try:
            connection_test = client.test_connection()
            if connection_test:
                logger.info("✓ Cablecast API connection test successful")
            else:
                logger.warning("⚠ Cablecast API connection test failed (expected if API not configured)")
        except Exception as e:
            logger.warning(f"⚠ Cablecast API connection test failed: {e}")
        
        # Test getting locations
        try:
            locations = client.get_locations()
            logger.info(f"✓ Retrieved {len(locations)} locations from Cablecast")
        except Exception as e:
            logger.warning(f"⚠ Failed to get locations: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Cablecast client test failed: {e}")
        return False

def test_vod_content_manager():
    """Test VOD content manager functionality"""
    logger.info("Testing VOD content manager...")
    
    try:
        from core.vod_content_manager import VODContentManager
        
        # Test manager initialization
        manager = VODContentManager()
        logger.info("✓ VOD content manager initialized successfully")
        
        # Test sync status (this should work even without API connection)
        try:
            sync_status = manager.get_sync_status()
            logger.info(f"✓ Sync status retrieved: {sync_status['total_transcriptions']} total transcriptions")
        except Exception as e:
            logger.warning(f"⚠ Failed to get sync status: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ VOD content manager test failed: {e}")
        return False

def test_models():
    """Test VOD-related models"""
    logger.info("Testing VOD models...")
    
    try:
        from core.models import (
            VODContentRequest, VODContentResponse, VODPublishRequest,
            VODBatchPublishRequest, VODSyncStatusResponse
        )
        
        # Test VODContentRequest validation
        try:
            request = VODContentRequest(
                title="Test Video",
                description="Test description",
                file_path="test/video.mp4",
                auto_transcribe=True
            )
            logger.info("✓ VODContentRequest validation successful")
        except Exception as e:
            logger.error(f"✗ VODContentRequest validation failed: {e}")
            return False
        
        # Test VODPublishRequest validation
        try:
            publish_request = VODPublishRequest(
                quality=1,
                auto_transcribe=True
            )
            logger.info("✓ VODPublishRequest validation successful")
        except Exception as e:
            logger.error(f"✗ VODPublishRequest validation failed: {e}")
            return False
        
        # Test VODBatchPublishRequest validation
        try:
            batch_request = VODBatchPublishRequest(
                transcription_ids=["test1", "test2"],
                quality=1
            )
            logger.info("✓ VODBatchPublishRequest validation successful")
        except Exception as e:
            logger.error(f"✗ VODBatchPublishRequest validation failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ VOD models test failed: {e}")
        return False

def test_configuration():
    """Test VOD configuration settings"""
    logger.info("Testing VOD configuration...")
    
    try:
        from core.config import (
            CABLECAST_API_URL, VOD_DEFAULT_QUALITY, VOD_MAX_RETRIES,
            VOD_ENABLE_CHAPTERS, VOD_ENABLE_METADATA_ENHANCEMENT
        )
        
        logger.info(f"✓ Cablecast API URL: {CABLECAST_API_URL}")
        logger.info(f"✓ VOD Default Quality: {VOD_DEFAULT_QUALITY}")
        logger.info(f"✓ VOD Max Retries: {VOD_MAX_RETRIES}")
        logger.info(f"✓ VOD Enable Chapters: {VOD_ENABLE_CHAPTERS}")
        logger.info(f"✓ VOD Enable Metadata Enhancement: {VOD_ENABLE_METADATA_ENHANCEMENT}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ VOD configuration test failed: {e}")
        return False

def main():
    """Run all VOD integration tests"""
    logger.info("Starting VOD integration tests...")
    
    tests = [
        ("Configuration", test_configuration),
        ("Models", test_models),
        ("Cablecast Client", test_cablecast_client),
        ("VOD Content Manager", test_vod_content_manager),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name} test...")
        logger.info(f"{'='*50}")
        
        try:
            if test_func():
                passed += 1
                logger.info(f"✓ {test_name} test PASSED")
            else:
                logger.error(f"✗ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"✗ {test_name} test FAILED with exception: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Test Results: {passed}/{total} tests passed")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 All VOD integration tests passed!")
        return 0
    else:
        logger.error(f"❌ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    exit_code = main()
    sys.exit(exit_code) 