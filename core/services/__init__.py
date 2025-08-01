"""Service layer for Archivist application.

This module provides clean abstractions for all business logic, separating
concerns and making the application more maintainable and testable.

Key Features:
- Service layer abstractions for all major functionality
- Clean separation of concerns
- Consistent error handling
- Easy testing and mocking

Example:
    >>> from core.services import TranscriptionService, VODService
    >>> transcription_service = TranscriptionService()
    >>> result = transcription_service.transcribe_file("video.mp4")
"""

from .transcription import TranscriptionService
from .vod import VODService
from .file import FileService
from .queue import QueueService

# Lazy singleton instances to prevent heavy imports at module load time
_transcription_service = None
_vod_service = None
_file_service = None
_queue_service = None

def get_transcription_service():
    """Get the transcription service singleton instance with graceful degradation."""
    global _transcription_service
    if _transcription_service is None:
        try:
            _transcription_service = TranscriptionService()
        except Exception as e:
            from loguru import logger
            logger.warning(f"Failed to initialize TranscriptionService: {e}")
            _transcription_service = MockTranscriptionService()
    return _transcription_service

def get_vod_service():
    """Get the VOD service singleton instance with graceful degradation."""
    global _vod_service
    if _vod_service is None:
        try:
            _vod_service = VODService()
        except Exception as e:
            from loguru import logger
            logger.warning(f"Failed to initialize VODService: {e}")
            _vod_service = MockVODService()
    return _vod_service

def get_file_service():
    """Get the file service singleton instance with graceful degradation."""
    global _file_service
    if _file_service is None:
        try:
            _file_service = FileService()
        except Exception as e:
            from loguru import logger
            logger.warning(f"Failed to initialize FileService: {e}")
            _file_service = MockFileService()
    return _file_service

def get_queue_service():
    """Get the queue service singleton instance with graceful degradation."""
    global _queue_service
    if _queue_service is None:
        try:
            _queue_service = QueueService()
        except Exception as e:
            from loguru import logger
            logger.warning(f"Failed to initialize QueueService: {e}")
            _queue_service = MockQueueService()
    return _queue_service

# Export queue utility functions to avoid circular imports
def get_all_jobs():
    """Get all jobs from the queue service."""
    return get_queue_service().get_all_jobs()

def get_queue_status():
    """Get queue status from the queue service."""
    return get_queue_service().get_queue_status()

def get_job_status(job_id: str):
    """Get status of a specific job."""
    return get_queue_service().get_job_status(job_id)

__all__ = [
    'TranscriptionService',
    'VODService', 
    'FileService',
    'QueueService',
    'get_transcription_service',
    'get_vod_service',
    'get_file_service',
    'get_queue_service',
    'get_all_jobs',
    'get_queue_status',
    'get_job_status',
]

# Mock service classes for graceful degradation
class MockTranscriptionService:
    """Mock transcription service for graceful degradation."""
    
    def __init__(self):
        self.available = False
    
    def transcribe_file(self, *args, **kwargs):
        from core.exceptions import ServiceUnavailableError
        raise ServiceUnavailableError("Transcription service unavailable")
    
    def get_status(self, *args, **kwargs):
        return {"status": "unavailable", "error": "Service not initialized"}

class MockVODService:
    """Mock VOD service for graceful degradation."""
    
    def __init__(self):
        self.available = False
    
    def process_vod(self, *args, **kwargs):
        from core.exceptions import ServiceUnavailableError
        raise ServiceUnavailableError("VOD service unavailable")
    
    def get_status(self, *args, **kwargs):
        return {"status": "unavailable", "error": "Service not initialized"}

class MockFileService:
    """Mock file service for graceful degradation."""
    
    def __init__(self):
        self.available = False
    
    def process_file(self, *args, **kwargs):
        from core.exceptions import ServiceUnavailableError
        raise ServiceUnavailableError("File service unavailable")
    
    def get_status(self, *args, **kwargs):
        return {"status": "unavailable", "error": "Service not initialized"}

class MockQueueService:
    """Mock queue service for graceful degradation."""
    
    def __init__(self):
        self.available = False
    
    def get_all_jobs(self, *args, **kwargs):
        return []
    
    def get_queue_status(self, *args, **kwargs):
        return {"status": "unavailable", "error": "Service not initialized"}

# Note: Singleton instances are now created lazily to avoid heavy imports at module load time 