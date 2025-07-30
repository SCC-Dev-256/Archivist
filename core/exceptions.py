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

import traceback
from functools import wraps
from typing import Any, Dict, Optional


class ArchivistException(Exception):
    """Base exception for all Archivist application errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None, original_exception: Exception = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.original_exception = original_exception
        self.traceback = traceback.format_exc() if original_exception else None
        super().__init__(self.message)
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'traceback': self.traceback
        }


# ============================================================================
# TRANSCRIPTION EXCEPTIONS
# ============================================================================

class TranscriptionError(ArchivistException):
    """Exception raised for transcription-related errors."""
    
    def __init__(self, message: str, details: dict = None, original_exception: Exception = None):
        super().__init__(message, "TRANSCRIPTION_ERROR", details, original_exception)


class WhisperModelError(TranscriptionError):
    """Exception raised for Whisper model loading/initialization errors."""
    
    def __init__(self, message: str, model_name: str = None, details: dict = None, original_exception: Exception = None):
        if model_name:
            details = details or {}
            details['model_name'] = model_name
        super().__init__(message, details, original_exception)


class AudioProcessingError(TranscriptionError):
    """Exception raised for audio processing errors."""
    
    def __init__(self, message: str, audio_file: str = None, details: dict = None, original_exception: Exception = None):
        if audio_file:
            details = details or {}
            details['audio_file'] = audio_file
        super().__init__(message, details, original_exception)


class SCCGenerationError(TranscriptionError):
    """Exception raised for SCC caption generation errors."""
    
    def __init__(self, message: str, scc_file: str = None, details: dict = None, original_exception: Exception = None):
        if scc_file:
            details = details or {}
            details['scc_file'] = scc_file
        super().__init__(message, details, original_exception)


# ============================================================================
# FILE SYSTEM EXCEPTIONS
# ============================================================================

class FileError(ArchivistException):
    """Exception raised for file operation errors."""
    
    def __init__(self, message: str, file_path: str = None, details: dict = None, original_exception: Exception = None):
        if file_path:
            details = details or {}
            details['file_path'] = file_path
        super().__init__(message, "FILE_ERROR", details, original_exception)


class FileNotFoundError(FileError):
    """Exception raised when a file is not found."""
    
    def __init__(self, file_path: str, details: dict = None, original_exception: Exception = None):
        super().__init__(f"File not found: {file_path}", file_path, details, original_exception)


class FilePermissionError(FileError):
    """Exception raised for file permission errors."""
    
    def __init__(self, file_path: str, operation: str = None, details: dict = None, original_exception: Exception = None):
        if operation:
            details = details or {}
            details['operation'] = operation
        super().__init__(f"Permission denied for file: {file_path}", file_path, details, original_exception)


class FileSizeError(FileError):
    """Exception raised for file size related errors."""
    
    def __init__(self, file_path: str, file_size: int = None, max_size: int = None, details: dict = None, original_exception: Exception = None):
        if file_size or max_size:
            details = details or {}
            if file_size:
                details['file_size'] = file_size
            if max_size:
                details['max_size'] = max_size
        super().__init__(f"File size error for: {file_path}", file_path, details, original_exception)


class FileFormatError(FileError):
    """Exception raised for unsupported file format errors."""
    
    def __init__(self, file_path: str, file_format: str = None, supported_formats: list = None, details: dict = None, original_exception: Exception = None):
        if file_format or supported_formats:
            details = details or {}
            if file_format:
                details['file_format'] = file_format
            if supported_formats:
                details['supported_formats'] = supported_formats
        super().__init__(f"Unsupported file format: {file_path}", file_path, details, original_exception)


# ============================================================================
# NETWORK AND API EXCEPTIONS
# ============================================================================

class NetworkError(ArchivistException):
    """Exception raised for network-related errors."""
    
    def __init__(self, message: str, url: str = None, status_code: int = None, details: dict = None, original_exception: Exception = None):
        if url or status_code:
            details = details or {}
            if url:
                details['url'] = url
            if status_code:
                details['status_code'] = status_code
        super().__init__(message, "NETWORK_ERROR", details, original_exception)


class ConnectionError(NetworkError):
    """Exception raised for connection errors."""
    
    def __init__(self, url: str, details: dict = None, original_exception: Exception = None):
        super().__init__(f"Connection failed to: {url}", url, None, details, original_exception)


class TimeoutError(NetworkError):
    """Exception raised for timeout errors."""
    
    def __init__(self, url: str, timeout: int = None, details: dict = None, original_exception: Exception = None):
        if timeout:
            details = details or {}
            details['timeout'] = timeout
        super().__init__(f"Request timeout for: {url}", url, None, details, original_exception)


class APIError(ArchivistException):
    """Exception raised for API-related errors."""
    
    def __init__(self, message: str, status_code: int = 500, endpoint: str = None, details: dict = None, original_exception: Exception = None):
        if endpoint:
            details = details or {}
            details['endpoint'] = endpoint
        self.status_code = status_code
        super().__init__(message, "API_ERROR", details, original_exception)


# ============================================================================
# DATABASE EXCEPTIONS
# ============================================================================

class DatabaseError(ArchivistException):
    """Exception raised for database operation errors."""
    
    def __init__(self, message: str, table: str = None, operation: str = None, details: dict = None, original_exception: Exception = None):
        if table or operation:
            details = details or {}
            if table:
                details['table'] = table
            if operation:
                details['operation'] = operation
        super().__init__(message, "DATABASE_ERROR", details, original_exception)


class DatabaseConnectionError(DatabaseError):
    """Exception raised for database connection errors."""
    
    def __init__(self, database_url: str = None, details: dict = None, original_exception: Exception = None):
        super().__init__("Database connection failed", None, "connect", details, original_exception)


class DatabaseQueryError(DatabaseError):
    """Exception raised for database query errors."""
    
    def __init__(self, message: str, query: str = None, table: str = None, details: dict = None, original_exception: Exception = None):
        if query:
            details = details or {}
            details['query'] = query
        super().__init__(message, table, "query", details, original_exception)


# ============================================================================
# QUEUE AND TASK EXCEPTIONS
# ============================================================================

class QueueError(ArchivistException):
    """Exception raised for task queue errors."""
    
    def __init__(self, message: str, task_id: str = None, queue_name: str = None, details: dict = None, original_exception: Exception = None):
        if task_id or queue_name:
            details = details or {}
            if task_id:
                details['task_id'] = task_id
            if queue_name:
                details['queue_name'] = queue_name
        super().__init__(message, "QUEUE_ERROR", details, original_exception)


class TaskNotFoundError(QueueError):
    """Exception raised when a task is not found."""
    
    def __init__(self, task_id: str, details: dict = None, original_exception: Exception = None):
        super().__init__(f"Task not found: {task_id}", task_id, None, details, original_exception)


class TaskTimeoutError(QueueError):
    """Exception raised when a task times out."""
    
    def __init__(self, task_id: str, timeout: int = None, details: dict = None, original_exception: Exception = None):
        if timeout:
            details = details or {}
            details['timeout'] = timeout
        super().__init__(f"Task timeout: {task_id}", task_id, None, details, original_exception)


class TaskExecutionError(QueueError):
    """Exception raised when a task fails during execution."""
    
    def __init__(self, task_id: str, task_name: str = None, details: dict = None, original_exception: Exception = None):
        if task_name:
            details = details or {}
            details['task_name'] = task_name
        super().__init__(f"Task execution failed: {task_id}", task_id, None, details, original_exception)


# ============================================================================
# VOD AND CABLECAST EXCEPTIONS
# ============================================================================

class VODError(ArchivistException):
    """Exception raised for VOD integration errors."""
    
    def __init__(self, message: str, vod_id: str = None, vod_url: str = None, details: dict = None, original_exception: Exception = None):
        if vod_id or vod_url:
            details = details or {}
            if vod_id:
                details['vod_id'] = vod_id
            if vod_url:
                details['vod_url'] = vod_url
        super().__init__(message, "VOD_ERROR", details, original_exception)


class CablecastError(ArchivistException):
    """Exception raised for Cablecast integration errors."""
    
    def __init__(self, message: str, show_id: str = None, endpoint: str = None, details: dict = None, original_exception: Exception = None):
        if show_id or endpoint:
            details = details or {}
            if show_id:
                details['show_id'] = show_id
            if endpoint:
                details['endpoint'] = endpoint
        super().__init__(message, "CABLECAST_ERROR", details, original_exception)


class CablecastAuthenticationError(CablecastError):
    """Exception raised for Cablecast authentication errors."""
    
    def __init__(self, endpoint: str = None, details: dict = None, original_exception: Exception = None):
        super().__init__("Cablecast authentication failed", None, endpoint, details, original_exception)


class CablecastShowNotFoundError(CablecastError):
    """Exception raised when a Cablecast show is not found."""
    
    def __init__(self, show_id: str, details: dict = None, original_exception: Exception = None):
        super().__init__(f"Cablecast show not found: {show_id}", show_id, None, details, original_exception)


# ============================================================================
# CONFIGURATION AND SECURITY EXCEPTIONS
# ============================================================================

class ConfigurationError(ArchivistException):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str, config_key: str = None, config_file: str = None, details: dict = None, original_exception: Exception = None):
        if config_key or config_file:
            details = details or {}
            if config_key:
                details['config_key'] = config_key
            if config_file:
                details['config_file'] = config_file
        super().__init__(message, "CONFIG_ERROR", details, original_exception)


class SecurityError(ArchivistException):
    """Exception raised for security-related errors."""
    
    def __init__(self, message: str, security_type: str = None, details: dict = None, original_exception: Exception = None):
        if security_type:
            details = details or {}
            details['security_type'] = security_type
        super().__init__(message, "SECURITY_ERROR", details, original_exception)


class AuthenticationError(SecurityError):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str, user: str = None, details: dict = None, original_exception: Exception = None):
        if user:
            details = details or {}
            details['user'] = user
        super().__init__(message, "authentication", details, original_exception)


class AuthorizationError(SecurityError):
    """Exception raised for authorization errors."""
    
    def __init__(self, message: str, resource: str = None, action: str = None, details: dict = None, original_exception: Exception = None):
        if resource or action:
            details = details or {}
            if resource:
                details['resource'] = resource
            if action:
                details['action'] = action
        super().__init__(message, "authorization", details, original_exception)


# ============================================================================
# SERVICE EXCEPTIONS
# ============================================================================

class ServiceUnavailableError(ArchivistException):
    """Exception raised when a service is unavailable."""
    
    def __init__(self, message: str, service_name: str = None, details: dict = None, original_exception: Exception = None):
        if service_name:
            details = details or {}
            details['service_name'] = service_name
        super().__init__(message, "SERVICE_UNAVAILABLE", details, original_exception)


class ConnectionTimeoutError(ArchivistException):
    """Exception raised when a connection times out."""
    
    def __init__(self, message: str, service_name: str = None, timeout: int = None, details: dict = None, original_exception: Exception = None):
        if service_name or timeout:
            details = details or {}
            if service_name:
                details['service_name'] = service_name
            if timeout:
                details['timeout'] = timeout
        super().__init__(message, "CONNECTION_TIMEOUT", details, original_exception)


# ============================================================================
# VALIDATION EXCEPTIONS
# ============================================================================

class ValidationError(ArchivistException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: str = None, value: Any = None, details: dict = None, original_exception: Exception = None):
        if field or value is not None:
            details = details or {}
            if field:
                details['field'] = field
            if value is not None:
                details['value'] = value
        super().__init__(message, "VALIDATION_ERROR", details, original_exception)


class RequiredFieldError(ValidationError):
    """Exception raised when a required field is missing."""
    
    def __init__(self, field: str, details: dict = None, original_exception: Exception = None):
        super().__init__(f"Required field missing: {field}", field, None, details, original_exception)


class InvalidFormatError(ValidationError):
    """Exception raised when a field has an invalid format."""
    
    def __init__(self, field: str, value: Any, expected_format: str = None, details: dict = None, original_exception: Exception = None):
        if expected_format:
            details = details or {}
            details['expected_format'] = expected_format
        super().__init__(f"Invalid format for field {field}: {value}", field, value, details, original_exception)


# ============================================================================
# CONVENIENCE FUNCTIONS AND DECORATORS
# ============================================================================

def handle_transcription_error(func):
    """Decorator to handle transcription errors consistently."""
    from loguru import logger
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (TranscriptionError, WhisperModelError, AudioProcessingError, SCCGenerationError):
            # Re-raise transcription-specific errors
            raise
        except Exception as e:
            logger.error(f"Transcription error in {func.__name__}: {e}")
            raise TranscriptionError(f"Transcription failed: {str(e)}", original_exception=e)
    return wrapper


def handle_vod_error(func):
    """Decorator to handle VOD errors consistently."""
    from loguru import logger
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (VODError, CablecastError):
            # Re-raise VOD-specific errors
            raise
        except Exception as e:
            logger.error(f"VOD error in {func.__name__}: {e}")
            raise VODError(f"VOD operation failed: {str(e)}", original_exception=e)
    return wrapper


def handle_file_error(func):
    """Decorator to handle file operation errors consistently."""
    from loguru import logger
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (FileError, FileNotFoundError, FilePermissionError, FileSizeError, FileFormatError):
            # Re-raise file-specific errors
            raise
        except Exception as e:
            logger.error(f"File error in {func.__name__}: {e}")
            raise FileError(f"File operation failed: {str(e)}", original_exception=e)
    return wrapper


def handle_network_error(func):
    """Decorator to handle network errors consistently."""
    from loguru import logger
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (NetworkError, ConnectionError, TimeoutError, APIError):
            # Re-raise network-specific errors
            raise
        except Exception as e:
            logger.error(f"Network error in {func.__name__}: {e}")
            raise NetworkError(f"Network operation failed: {str(e)}", original_exception=e)
    return wrapper


def handle_database_error(func):
    """Decorator to handle database errors consistently."""
    from loguru import logger
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (DatabaseError, DatabaseConnectionError, DatabaseQueryError):
            # Re-raise database-specific errors
            raise
        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            raise DatabaseError(f"Database operation failed: {str(e)}", original_exception=e)
    return wrapper


def handle_queue_error(func):
    """Decorator to handle queue errors consistently."""
    from loguru import logger
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (QueueError, TaskNotFoundError, TaskTimeoutError, TaskExecutionError):
            # Re-raise queue-specific errors
            raise
        except Exception as e:
            logger.error(f"Queue error in {func.__name__}: {e}")
            raise QueueError(f"Queue operation failed: {str(e)}", original_exception=e)
    return wrapper


# ============================================================================
# ERROR MAPPING UTILITIES
# ============================================================================

def map_exception_to_http_status(exception: ArchivistException) -> int:
    """Map application exceptions to appropriate HTTP status codes."""
    
    if isinstance(exception, (FileNotFoundError, TaskNotFoundError, CablecastShowNotFoundError)):
        return 404
    
    if isinstance(exception, (FilePermissionError, AuthenticationError, AuthorizationError)):
        return 403
    
    if isinstance(exception, (ValidationError, RequiredFieldError, InvalidFormatError)):
        return 400
    
    if isinstance(exception, (TimeoutError, TaskTimeoutError)):
        return 408
    
    if isinstance(exception, (ConnectionError, DatabaseConnectionError)):
        return 503
    
    if isinstance(exception, (ConfigurationError, SecurityError)):
        return 500
    
    # Default for other application errors
    return 500


def create_error_response(exception: ArchivistException) -> dict:
    """Create a standardized error response from an exception."""
    
    return {
        'success': False,
        'error': {
            'code': exception.error_code,
            'message': exception.message,
            'details': exception.details
        }
    } 