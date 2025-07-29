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

# Create singleton instances for services
transcription_service = TranscriptionService()
vod_service = VODService()
file_service = FileService()
queue_service = QueueService()

# Export queue utility functions to avoid circular imports
def get_all_jobs():
    """Get all jobs from the queue service."""
    return queue_service.get_all_jobs()

def get_queue_status():
    """Get queue status from the queue service."""
    return queue_service.get_queue_status()

def get_job_status(job_id: str):
    """Get status of a specific job."""
    return queue_service.get_job_status(job_id)

__all__ = [
    'TranscriptionService',
    'VODService', 
    'FileService',
    'QueueService',
    'transcription_service',
    'vod_service',
    'file_service',
    'queue_service',
    'get_all_jobs',
    'get_queue_status',
    'get_job_status',
]

# Note: Singleton instances are now created in core/__init__.py to avoid circular imports 