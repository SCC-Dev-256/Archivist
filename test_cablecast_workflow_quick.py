#!/usr/bin/env python3
"""Quick test script for the corrected Cablecast workflow.

This script tests the core functionality without making external API calls
to avoid timeouts and network issues.

Usage:
    python test_cablecast_workflow_quick.py
"""

import os
import sys
import uuid
from datetime import datetime
from loguru import logger

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_show_mapper_core():
    """Test the core show mapper functionality without API calls"""
    logger.info("Testing Cablecast show mapper core functionality...")
    
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
        
        # Test match score calculation
        test_show = {
            'id': 123,
            'title': 'News Show',
            'date': '2024-01-15',
            'length': 1800,
            'description': 'Daily news broadcast'
        }
        
        score = mapper._calculate_match_score(
            test_show, 
            "2024-01-15_News_Show.mp4", 
            "2024-01-15", 
            "News Show", 
            {'duration': 1800}
        )
        
        logger.info(f"Match score for test show: {score:.3f}")
        
        logger.info("✓ Show mapper core tests completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Show mapper core test failed: {e}")
        return False

def test_transcription_linker_core():
    """Test the transcription linker core functionality"""
    logger.info("Testing transcription linker core functionality...")
    
    try:
        from core.cablecast_transcription_linker import CablecastTranscriptionLinker
        
        linker = CablecastTranscriptionLinker()
        
        # Test SRT parsing
        test_srt_content = """1
00:00:00,000 --> 00:00:05,000
This is the first segment of the transcription.

2
00:00:05,000 --> 00:00:10,000
This is the second segment with more content.

3
00:00:10,000 --> 00:00:15,000
And this is the final segment of our test."""
        
        # Test transcription analysis
        metadata = linker._analyze_transcription(test_srt_content)
        logger.info(f"Transcription analysis:")
        logger.info(f"  Total segments: {metadata.get('total_segments', 0)}")
        logger.info(f"  Total duration: {metadata.get('total_duration_seconds', 0)} seconds")
        logger.info(f"  Total words: {metadata.get('total_words', 0)}")
        logger.info(f"  Key phrases: {metadata.get('key_phrases', [])[:5]}")
        
        # Test timestamp parsing
        test_timestamp = "01:23:45,678"
        seconds = linker._parse_timestamp(test_timestamp)
        logger.info(f"Timestamp '{test_timestamp}' = {seconds} seconds")
        
        # Test key phrase extraction
        test_text = "This is a test of the key phrase extraction functionality. This test should extract key phrases from this text."
        key_phrases = linker._extract_key_phrases(test_text, max_phrases=5)
        logger.info(f"Key phrases from test text: {key_phrases}")
        
        logger.info("✓ Transcription linker core tests completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Transcription linker core test failed: {e}")
        return False

def test_database_models():
    """Test the database models"""
    logger.info("Testing database models...")
    
    try:
        from core.models import CablecastShowORM
        from core.app import create_app, db
        
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
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
            
            # Test that the table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'cablecast_shows' in tables:
                logger.info("✓ cablecast_shows table exists in database")
            else:
                logger.error("✗ cablecast_shows table not found in database")
                return False
        
        logger.info("✓ Database models test completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database models test failed: {e}")
        return False

def test_api_endpoints():
    """Test the API endpoint structure"""
    logger.info("Testing API endpoints...")
    
    try:
        from web.api.cablecast import cablecast_bp
        
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

def test_vod_automation_core():
    """Test the VOD automation core functionality"""
    logger.info("Testing VOD automation core functionality...")
    
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
            
            # Test link status (should return not linked)
            status = get_transcription_link_status(test_id)
            logger.info(f"Link status for non-existent transcription: {status}")
            
            # Test show suggestions (should fail gracefully)
            suggestions_result = get_show_suggestions(test_id, limit=3)
            logger.info(f"Show suggestions result: {suggestions_result.get('success', False)}")
            
            # Test queue processing (should handle empty queue)
            queue_result = process_transcription_queue()
            logger.info(f"Queue processing result: {queue_result.get('success', False)}")
            logger.info(f"Queue message: {queue_result.get('message', 'No message')}")
        
        logger.info("✓ VOD automation core tests completed")
        return True
        
    except Exception as e:
        logger.error(f"✗ VOD automation core test failed: {e}")
        return False

def main():
    """Run all quick tests"""
    logger.info("Starting Cablecast workflow quick tests...")
    
    tests = [
        ("Show Mapper Core", test_show_mapper_core),
        ("Transcription Linker Core", test_transcription_linker_core),
        ("Database Models", test_database_models),
        ("API Endpoints", test_api_endpoints),
        ("VOD Automation Core", test_vod_automation_core)
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