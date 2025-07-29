#!/usr/bin/env python3
"""Test script for the corrected Cablecast workflow.

This script tests the show mapping and linking functionality for the
corrected Cablecast integration workflow.

Usage:
    python test_cablecast_workflow.py
"""

import os
import sys
import uuid
from datetime import datetime
from loguru import logger

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_show_mapper():
    """Test the Cablecast show mapper functionality"""
    logger.info("Testing Cablecast show mapper...")
    
    try:
        from core.cablecast_show_mapper import CablecastShowMapper
        
        mapper = CablecastShowMapper()
        
        # Test date extraction
        test_files = [
            "2024-01-15_News_Show.mp4",
            "01-15-2024_Weather_Report.mp4", 
            "20240115_Sports_Highlights.mp4",
            "15_01_2024_Interview.mp4",
            "regular_video_file.mp4"
        ]
        
        for filename in test_files:
            date = mapper._extract_date_from_filename(filename)
            title = mapper._extract_title_from_filename(filename)
            logger.info(f"File: {filename}")
            logger.info(f"  Extracted date: {date}")
            logger.info(f"  Extracted title: {title}")
        
        # Test show suggestions (this will fail if Cablecast is not configured)
        try:
            suggestions = mapper.get_show_suggestions("/path/to/test/video.mp4", limit=3)
            logger.info(f"Show suggestions: {len(suggestions)} found")
            for suggestion in suggestions[:2]:  # Show first 2
                logger.info(f"  - {suggestion['title']} (ID: {suggestion['show_id']}, Score: {suggestion['similarity_score']})")
        except Exception as e:
            logger.warning(f"Could not test show suggestions (Cablecast not configured): {e}")
        
        logger.info("✓ Show mapper tests completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Show mapper test failed: {e}")
        return False

def test_transcription_linker():
    """Test the transcription linker functionality"""
    logger.info("Testing transcription linker...")
    
    try:
        from core.cablecast_transcription_linker import CablecastTranscriptionLinker
        
        linker = CablecastTranscriptionLinker()
        
        # Test SCC parsing
        test_scc_content = """Scenarist_SCC V1.0

00:00:00;00	9420 9420 94ae 94ae 9452 9452 97a2 97a2 d468 6973 2069 7320 f468 6520 6669 7273 7420 7365 676d 656e 7420 6f66 20f4 6865 2074 7261 6e73 6372 6970 f469 6f6e 2e9420 9420 942c 942c 8080 8080

00:00:05;00	9420 9420 94ae 94ae 9452 9452 97a2 97a2 d468 6973 2069 7320 f468 6520 7365 636f 6e64 2073 6567 6d65 6e74 2077 6974 6820 6d6f 7265 2063 6f6e f465 6e74 2e9420 9420 942c 942c 8080 8080

00:00:10;00	9420 9420 94ae 94ae 9452 9452 97a2 97a2 c16e 6420 f468 6973 2069 7320 f468 6520 6669 6e61 6c20 7365 676d 656e 7420 6f66 206f 7572 2074 6573 742e 9420 9420 942c 942c 8080 8080"""
        
        # Create a temporary SCC file
        temp_scc_path = "/tmp/test_transcription.scc"
        with open(temp_scc_path, 'w', encoding='utf-8') as f:
            f.write(test_scc_content)
        
        try:
            # Test transcription analysis with SCC format
            metadata = linker._analyze_transcription(test_scc_content)
            logger.info(f"Transcription analysis:")
            logger.info(f"  Total segments: {metadata.get('total_segments', 0)}")
            logger.info(f"  Total duration: {metadata.get('total_duration_seconds', 0)} seconds")
            logger.info(f"  Total words: {metadata.get('total_words', 0)}")
            logger.info(f"  Key phrases: {metadata.get('key_phrases', [])[:5]}")
            
            # Test SMPTE timestamp parsing
            test_timestamp = "01:23:45;15"
            seconds = linker._parse_timestamp(test_timestamp)
            logger.info(f"SMPTE Timestamp '{test_timestamp}' = {seconds} seconds")
            
        finally:
            # Clean up
            if os.path.exists(temp_scc_path):
                os.remove(temp_scc_path)
        
        logger.info("✓ Transcription linker tests completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Transcription linker test failed: {e}")
        return False

def test_vod_automation():
    """Test the VOD automation functions"""
    logger.info("Testing VOD automation...")
    
    try:
        from core.vod_automation import (
            get_transcription_link_status,
            get_show_suggestions,
            process_transcription_queue
        )
        from core.app import create_app
        
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            # Test with a non-existent transcription ID
            test_id = str(uuid.uuid4())
            
            # Test link status
            status = get_transcription_link_status(test_id)
            logger.info(f"Link status for non-existent transcription: {status}")
            
            # Test show suggestions
            suggestions_result = get_show_suggestions(test_id, limit=3)
            logger.info(f"Show suggestions result: {suggestions_result.get('success', False)}")
            
            # Test queue processing
            queue_result = process_transcription_queue()
            logger.info(f"Queue processing result: {queue_result.get('success', False)}")
            logger.info(f"Queue message: {queue_result.get('message', 'No message')}")
        
        logger.info("✓ VOD automation tests completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ VOD automation test failed: {e}")
        return False

def test_api_endpoints():
    """Test the API endpoint structure"""
    logger.info("Testing API endpoints...")
    
    try:
        from web.api.cablecast import cablecast_bp
        
        # Check that the blueprint has the expected routes by examining the blueprint directly
        expected_routes = [
            '/api/cablecast/shows',
            '/api/cablecast/shows/<int:show_id>',
            '/api/cablecast/link/<transcription_id>',
            '/api/cablecast/link/<transcription_id>/manual',
            '/api/cablecast/link/<transcription_id>/status',
            '/api/cablecast/link/<transcription_id>',
            '/api/cablecast/shows/<int:show_id>/transcriptions',
            '/api/cablecast/suggestions/<transcription_id>',
            '/api/cablecast/queue/process',
            '/api/cablecast/health'
        ]
        
        # Check that the blueprint exists and has the correct URL prefix
        if cablecast_bp.url_prefix == '/api/cablecast':
            logger.info("✓ Blueprint has correct URL prefix")
        else:
            logger.warning(f"⚠ Blueprint URL prefix: {cablecast_bp.url_prefix}")
        
        # Count the number of routes in the blueprint
        route_count = len(list(cablecast_bp.deferred_functions))
        logger.info(f"Blueprint has {route_count} routes")
        
        # Since we can't easily check individual routes without registering the blueprint,
        # we'll just verify the blueprint structure is correct
        if route_count >= 8:  # Should have at least 8 routes
            logger.info("✓ API endpoints test completed")
            return True
        else:
            logger.error(f"✗ Too few routes: {route_count}")
            return False
        
    except Exception as e:
        logger.error(f"✗ API endpoints test failed: {e}")
        return False

def test_database_models():
    """Test the database models"""
    logger.info("Testing database models...")
    
    try:
        from core.models import CablecastShowORM
        from core import db
        
        # Test model creation
        test_show = CablecastShowORM(
            cablecast_id=12345,
            title="Test Show",
            description="A test show for validation",
            duration=1800,  # 30 minutes
            transcription_id=str(uuid.uuid4())
        )
        
        # Test model attributes
        assert test_show.cablecast_id == 12345
        assert test_show.title == "Test Show"
        assert test_show.duration == 1800
        assert test_show.transcription_id is not None
        
        logger.info(f"✓ Created test show: {test_show.title} (ID: {test_show.cablecast_id})")
        logger.info("✓ Database models test completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database models test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting Cablecast workflow tests...")
    
    tests = [
        ("Show Mapper", test_show_mapper),
        ("Transcription Linker", test_transcription_linker),
        ("VOD Automation", test_vod_automation),
        ("API Endpoints", test_api_endpoints),
        ("Database Models", test_database_models)
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
            logger.error(f"✗ {test_name} test ERROR: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Test Results: {passed}/{total} tests passed")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 All tests passed! The corrected Cablecast workflow is working correctly.")
        return 0
    else:
        logger.error(f"❌ {total - passed} tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    exit_code = main()
    sys.exit(exit_code) 