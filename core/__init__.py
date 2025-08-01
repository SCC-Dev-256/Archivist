"""
Core package for the Archivist application.

Centralizes main classes, singletons, and helpers for easy import.
This is the single source of truth for all core imports.
"""

# Import lightweight modules immediately (no external dependencies)
from .database import db

# Import exceptions first (no dependencies)
from .exceptions import (
    ArchivistException, TranscriptionError, WhisperModelError, FileError, FileNotFoundError,
    FilePermissionError, FileFormatError, NetworkError, APIError, DatabaseError,
    DatabaseConnectionError, DatabaseQueryError, VODError, ConfigurationError,
    SecurityError, AuthenticationError, AuthorizationError, ValidationError,
    RequiredFieldError, handle_transcription_error, handle_vod_error, handle_file_error,
    handle_network_error, handle_database_error, handle_queue_error
)

# Import models (depends on exceptions)
from .models import (
    TranscriptionJobORM, TranscriptionResultORM, BrowseRequest, FileItem, ErrorResponse,
    SuccessResponse, TranscribeRequest, QueueReorderRequest, JobStatus, BatchTranscribeRequest,
    SecurityConfig, AuditLogEntry, CablecastShowORM, CablecastVODORM, CablecastVODChapterORM,
    VODContentRequest, VODContentResponse, VODPlaylistRequest, VODStreamRequest,
    VODPublishRequest, VODBatchPublishRequest, VODSyncStatusResponse, CablecastShowResponse
)

# Import config constants
from .config import MEMBER_CITIES

# Import lazy loading utilities for heavy modules
from .lazy_imports import (
    get_celery_app, get_integrated_dashboard, get_admin_ui, get_start_admin_ui,
    get_transcription_service, get_vod_service, get_file_service, get_queue_service,
    get_unified_queue_manager, get_vod_content_manager
)

# Import security functions (lightweight)
from .security import get_csrf_token, require_csrf_token, validate_json_input, sanitize_output, security_manager

__all__ = [
    # Database
    "db",
    
    # Exceptions
    "ArchivistException", "TranscriptionError", "WhisperModelError", "FileError", "FileNotFoundError",
    "FilePermissionError", "FileFormatError", "NetworkError", "APIError", "DatabaseError",
    "DatabaseConnectionError", "DatabaseQueryError", "VODError", "ConfigurationError",
    "SecurityError", "AuthenticationError", "AuthorizationError", "ValidationError",
    "RequiredFieldError", "handle_transcription_error", "handle_vod_error", "handle_file_error",
    "handle_network_error", "handle_database_error", "handle_queue_error",
    
    # Models
    "TranscriptionJobORM", "TranscriptionResultORM", "BrowseRequest", "FileItem", "ErrorResponse",
    "SuccessResponse", "TranscribeRequest", "QueueReorderRequest", "JobStatus", "BatchTranscribeRequest",
    "SecurityConfig", "AuditLogEntry", "CablecastShowORM", "CablecastVODORM", "CablecastVODChapterORM",
    "VODContentRequest", "VODContentResponse", "VODPlaylistRequest", "VODStreamRequest",
    "VODPublishRequest", "VODBatchPublishRequest", "VODSyncStatusResponse", "CablecastShowResponse",
    
    # Configuration
    "MEMBER_CITIES",
    
    # Lazy Loading Functions
    "get_celery_app", "get_integrated_dashboard", "get_admin_ui", "get_start_admin_ui",
    "get_transcription_service", "get_vod_service", "get_file_service", "get_queue_service",
    "get_unified_queue_manager", "get_vod_content_manager",
    
    # Security Functions
    "get_csrf_token", "require_csrf_token", "validate_json_input", "sanitize_output", "security_manager"
] 