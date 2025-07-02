#!/usr/bin/env python3
"""Simple test script to verify service layer imports."""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test importing the service layer."""
    try:
        print("Testing service layer imports...")
        
        # Test importing individual services
        from core.services.transcription import TranscriptionService
        print("✓ TranscriptionService imported")
        
        from core.services.file import FileService
        print("✓ FileService imported")
        
        from core.services.queue import QueueService
        print("✓ QueueService imported")
        
        # Test importing from the main services module
        from core.services import TranscriptionService, FileService, QueueService
        print("✓ All services imported from main module")
        
        # Test creating service instances
        transcription_service = TranscriptionService()
        print("✓ TranscriptionService instance created")
        
        file_service = FileService()
        print("✓ FileService instance created")
        
        queue_service = QueueService()
        print("✓ QueueService instance created")
        
        print("All service layer tests passed!")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1) 