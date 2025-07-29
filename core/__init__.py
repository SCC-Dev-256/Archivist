"""
Core package for the Archivist application.

Centralizes main classes, singletons, and helpers for easy import.
This is the single source of truth for all core imports.
"""

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

# Import file manager (depends on exceptions)
from .file_manager import FileManager, file_manager

# Import security (depends on models and exceptions)
from .security import SecurityManager, security_manager, require_csrf_token, validate_json_input, sanitize_output, get_csrf_token

# Import VOD content manager (depends on exceptions and models)
from .vod_content_manager import VODContentManager

# Import unified queue manager (depends on tasks)
from .unified_queue_manager import UnifiedQueueManager

# Import monitoring dashboard (depends on tasks)
from .monitoring.integrated_dashboard import IntegratedDashboard

# Import tasks (depends on services)
from .tasks import celery_app

# Import config constants
from .config import MEMBER_CITIES

# Import admin UI (depends on security)
from .admin_ui import AdminUI, start_admin_ui

# Import individual services directly to avoid circular imports
from .services.transcription import TranscriptionService
from .services.vod import VODService
from .services.file import FileService
from .services.queue import QueueService

# Create singleton instances for services
transcription_service = TranscriptionService()
vod_service = VODService()
file_service = FileService()
queue_service = QueueService()

# Import app last (depends on everything above)
from .app import app, create_app, create_app_with_config

__all__ = [
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
    
    # Managers and Services
    "FileManager", "file_manager", "VODContentManager", "UnifiedQueueManager",
    "TranscriptionService", "VODService", "FileService", "QueueService",
    "transcription_service", "vod_service", "file_service", "queue_service",
    
    # Monitoring and Tasks
    "IntegratedDashboard", "celery_app",
    
    # Configuration
    "MEMBER_CITIES",
    
    # Security
    "SecurityManager", "security_manager", "require_csrf_token", "validate_json_input", "sanitize_output", "get_csrf_token",
    
    # Admin UI
    "AdminUI", "start_admin_ui",
    
    # App
    "app", "create_app", "create_app_with_config"
] 