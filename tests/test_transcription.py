#!/usr/bin/env python3
"""
Test script for transcription functionality.
Tests both the service layer and direct transcription methods.
"""

import os
import sys
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Configure logging for tests
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

def test_transcription_service():
    """Test the transcription service layer."""
    logger.info("🎤 Testing Transcription Service...")
    
    try:
        from core.services import TranscriptionService
        
        service = TranscriptionService()
        logger.info("✅ TranscriptionService imported successfully")
        
        # Test service initialization
        if hasattr(service, 'transcribe_file'):
            logger.info("✅ transcribe_file method available")
        else:
            logger.error("❌ transcribe_file method not found")
            return False
            
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import TranscriptionService: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing TranscriptionService: {e}")
        return False

def test_direct_transcription():
    """Test direct transcription functionality."""
    logger.info("🎤 Testing Direct Transcription...")
    
    try:
        from core.transcription import run_whisper_transcription
        
        logger.info("✅ run_whisper_transcription imported successfully")
        
        # Test function availability
        if callable(run_whisper_transcription):
            logger.info("✅ run_whisper_transcription is callable")
        else:
            logger.error("❌ run_whisper_transcription is not callable")
            return False
            
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import run_whisper_transcription: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing direct transcription: {e}")
        return False

def test_task_transcription():
    """Test task-based transcription."""
    logger.info("🎤 Testing Task Transcription...")
    
    try:
        from core.tasks.transcription import run_whisper_transcription
        
        logger.info("✅ Task transcription imported successfully")
        
        # Test function availability
        if callable(run_whisper_transcription):
            logger.info("✅ Task run_whisper_transcription is callable")
        else:
            logger.error("❌ Task run_whisper_transcription is not callable")
            return False
            
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import task transcription: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing task transcription: {e}")
        return False

def find_test_video():
    """Find a test video file."""
    logger.info("🔍 Looking for test video files...")
    
    # Common test video locations
    test_locations = [
        "test_videos/",
        "data/test_videos/",
        "output/test_videos/",
        "backup_20250718_170846/test_videos/"
    ]
    
    for location in test_locations:
        if os.path.exists(location):
            logger.info(f"✅ Found test directory: {location}")
            
            # Look for video files
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
            for ext in video_extensions:
                for file in os.listdir(location):
                    if file.endswith(ext):
                        test_video = os.path.join(location, file)
                        logger.info(f"✅ Found test video: {test_video}")
                        return test_video
    
    logger.warning("⚠️  No test video files found")
    return None

def main():
    """Run all transcription tests."""
    logger.info("🚀 Starting Transcription System Tests")
    logger.info("=" * 50)
    
    # Test service layer
    service_ok = test_transcription_service()
    
    # Test direct transcription
    direct_ok = test_direct_transcription()
    
    # Test task transcription
    task_ok = test_task_transcription()
    
    # Find test video
    test_video = find_test_video()
    
    # Summary
    logger.info("=" * 50)
    logger.info("📊 Test Results Summary:")
    logger.info(f"   Service Layer: {'✅ PASS' if service_ok else '❌ FAIL'}")
    logger.info(f"   Direct Transcription: {'✅ PASS' if direct_ok else '❌ FAIL'}")
    logger.info(f"   Task Transcription: {'✅ PASS' if task_ok else '❌ FAIL'}")
    logger.info(f"   Test Video: {'✅ FOUND' if test_video else '❌ NOT FOUND'}")
    
    if service_ok and direct_ok and task_ok:
        logger.info("🎉 All transcription tests passed!")
        return True
    else:
        logger.error("❌ Some transcription tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 