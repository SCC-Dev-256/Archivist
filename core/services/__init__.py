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

__all__ = [
    'TranscriptionService',
    'VODService', 
    'FileService',
    'QueueService'
]

# Note: Singleton instances are now created in core/__init__.py to avoid circular imports 