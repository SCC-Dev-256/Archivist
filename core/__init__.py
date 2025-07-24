"""
Core package for the Archivist application.

Centralizes main classes, singletons, and helpers for easy import.

Note: For configuration constants, always use 'from core.config import ...' directly to avoid circular imports.
"""

from .app import app, create_app, create_app_with_config
from .exceptions import (
    ArchivistException, TranscriptionError, WhisperModelError, FileError, FileNotFoundError,
    FilePermissionError, FileFormatError, NetworkError, APIError, DatabaseError,
    DatabaseConnectionError, DatabaseQueryError, VODError, ConfigurationError,
    SecurityError, AuthenticationError, AuthorizationError, ValidationError,
    RequiredFieldError, handle_transcription_error, handle_vod_error, handle_file_error,
    handle_network_error, handle_database_error, handle_queue_error
)
from .file_manager import FileManager, file_manager
from .models import (
    TranscriptionJobORM, TranscriptionResultORM, BrowseRequest, FileItem, ErrorResponse,
    SuccessResponse, TranscribeRequest, QueueReorderRequest, JobStatus, BatchTranscribeRequest,
    SecurityConfig, AuditLogEntry, CablecastShowORM, CablecastVODORM, CablecastVODChapterORM,
    VODContentRequest, VODContentResponse, VODPlaylistRequest, VODStreamRequest,
    VODPublishRequest, VODBatchPublishRequest, VODSyncStatusResponse, CablecastShowResponse
)
from .security import SecurityManager, security_manager, require_csrf_token, validate_json_input, sanitize_output, get_csrf_token
from .admin_ui import AdminUI, start_admin_ui
from .vod_content_manager import VODContentManager

__all__ = [
    "app", "create_app", "create_app_with_config",
    "ArchivistException", "TranscriptionError", "WhisperModelError", "FileError", "FileNotFoundError",
    "FilePermissionError", "FileFormatError", "NetworkError", "APIError", "DatabaseError",
    "DatabaseConnectionError", "DatabaseQueryError", "VODError", "ConfigurationError",
    "SecurityError", "AuthenticationError", "AuthorizationError", "ValidationError",
    "RequiredFieldError", "handle_transcription_error", "handle_vod_error", "handle_file_error",
    "handle_network_error", "handle_database_error", "handle_queue_error",
    "FileManager", "file_manager",
    "TranscriptionJobORM", "TranscriptionResultORM", "BrowseRequest", "FileItem", "ErrorResponse",
    "SuccessResponse", "TranscribeRequest", "QueueReorderRequest", "JobStatus", "BatchTranscribeRequest",
    "SecurityConfig", "AuditLogEntry", "CablecastShowORM", "CablecastVODORM", "CablecastVODChapterORM",
    "VODContentRequest", "VODContentResponse", "VODPlaylistRequest", "VODStreamRequest",
    "VODPublishRequest", "VODBatchPublishRequest", "VODSyncStatusResponse", "CablecastShowResponse",
    "SecurityManager", "security_manager", "require_csrf_token", "validate_json_input", "sanitize_output", "get_csrf_token",
    "AdminUI", "start_admin_ui",
    "VODContentManager"
] 