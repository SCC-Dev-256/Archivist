"""Exception classes for the Archivist application.

This module provides centralized exception handling for all application errors,
making error handling consistent and easier to manage.

Key Features:
- Base exception class for all application errors
- Domain-specific exception classes
- Consistent error messages and codes
- Easy error categorization and handling

Example:
    >>> from core.exceptions import TranscriptionError
    >>> raise TranscriptionError("Failed to process audio file")
"""

class ArchivistException(Exception):
    """Base exception for all Archivist application errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

class TranscriptionError(ArchivistException):
    """Exception raised for transcription-related errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "TRANSCRIPTION_ERROR", details)

class VODError(ArchivistException):
    """Exception raised for VOD integration errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "VOD_ERROR", details)

class FileError(ArchivistException):
    """Exception raised for file operation errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "FILE_ERROR", details)

class QueueError(ArchivistException):
    """Exception raised for task queue errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "QUEUE_ERROR", details)

class ConfigurationError(ArchivistException):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "CONFIG_ERROR", details)

class SecurityError(ArchivistException):
    """Exception raised for security-related errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "SECURITY_ERROR", details)

class DatabaseError(ArchivistException):
    """Exception raised for database operation errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "DATABASE_ERROR", details)

class APIError(ArchivistException):
    """Exception raised for API-related errors."""
    
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.status_code = status_code
        super().__init__(message, "API_ERROR", details)

class ValidationError(ArchivistException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: str = None, details: dict = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR", details)

# Convenience functions for common error patterns
def handle_transcription_error(func):
    """Decorator to handle transcription errors consistently."""
    from functools import wraps
    from loguru import logger
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Transcription error in {func.__name__}: {e}")
            raise TranscriptionError(f"Transcription failed: {str(e)}")
    return wrapper

def handle_vod_error(func):
    """Decorator to handle VOD errors consistently."""
    from functools import wraps
    from loguru import logger
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"VOD error in {func.__name__}: {e}")
            raise VODError(f"VOD operation failed: {str(e)}")
    return wrapper

def handle_file_error(func):
    """Decorator to handle file operation errors consistently."""
    from functools import wraps
    from loguru import logger
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"File error in {func.__name__}: {e}")
            raise FileError(f"File operation failed: {str(e)}")
    return wrapper 