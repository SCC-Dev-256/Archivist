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
from .helo import HeloService

__all__ = [
    'TranscriptionService',
    'VODService', 
    'FileService',
    'QueueService',
    'HeloService'
]

# Create singleton instances for easy access
transcription_service = TranscriptionService()
vod_service = VODService()
file_service = FileService()
queue_service = QueueService() 
helo_service = HeloService()