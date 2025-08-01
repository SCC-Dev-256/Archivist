#!/usr/bin/env python3
"""
Simple test script to verify service layer imports.
"""

import os
import sys
from pathlib import Path
import traceback

from loguru import logger

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test importing the service layer."""
    try:
        logger.info("Testing service layer imports...")
        
        # Test importing individual services
        from core.services.transcription import TranscriptionService
        logger.info("✓ TranscriptionService imported")
        
        from core.services.file import FileService
        logger.info("✓ FileService imported")
        
        from core.services.queue import QueueService
        logger.info("✓ QueueService imported")
        
        # Test importing from the main services module
        from core.services import TranscriptionService as TS, FileService as FS, QueueService as QS
        logger.info("✓ All services imported from main module")
        
        # Test creating service instances
        transcription_service = TranscriptionService()
        logger.info("✓ TranscriptionService instance created")
        
        file_service = FileService()
        logger.info("✓ FileService instance created")
        
        queue_service = QueueService()
        logger.info("✓ QueueService instance created")
        
        logger.info("All service layer tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1) 