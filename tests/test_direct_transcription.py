#!/usr/bin/env python3
"""
Test direct transcription functionality without Celery.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Configure logging for tests
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

def test_direct_transcription():
    """Test direct transcription without Celery."""
    logger.info("🎤 Testing Direct Transcription...")
    
    try:
        from core.transcription import run_whisper_transcription
        
        logger.info("✅ Direct transcription function imported")
        
        # Test function availability
        if callable(run_whisper_transcription):
            logger.info("✅ Direct transcription function is callable")
            return True
        else:
            logger.error("❌ Direct transcription function is not callable")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Failed to import direct transcription: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def main():
    """Run direct transcription test."""
    logger.info("🚀 Starting Direct Transcription Test")
    logger.info("=" * 50)
    
    success = test_direct_transcription()
    
    logger.info("=" * 50)
    if success:
        logger.info("🎉 Direct transcription test passed!")
    else:
        logger.error("❌ Direct transcription test failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 