from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Literal, Union, Dict, Any
import os
from pathlib import Path
from datetime import datetime
import re

from core.database import db

# Create the declarative base
Base = db.Model

class TranscriptionJobORM(db.Model):
    __tablename__ = 'transcription_jobs'
    
    id = db.Column(db.String(36), primary_key=True)
    video_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    error = db.Column(db.Text, nullable=True)
    result_id = db.Column(db.String(36), db.ForeignKey('transcription_results.id'), nullable=True)
    
    result = db.relationship('TranscriptionResultORM', backref='job', uselist=False)

class TranscriptionResultORM(db.Model):
    __tablename__ = 'transcription_results'
    
    id = db.Column(db.String(36), primary_key=True)
    video_path = db.Column(db.String(255), nullable=False)
    output_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='completed')
    completed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    error = db.Column(db.Text, nullable=True)

# Pydantic models for request/response validation
class BrowseRequest(BaseModel):
    path: str = Field(default="", description="Path to browse, relative to NAS_PATH", max_length=500)
    
    @validator('path')
    def validate_path(cls, v):
        # Check for directory traversal attempts
        if '..' in v:
            raise ValueError('Invalid path: cannot contain ".."')
        
        # Check for suspicious characters
        suspicious_chars = ['<', '>', '"', "'", '&', '|', ';', '`', '$', '(', ')']
        if any(char in v for char in suspicious_chars):
            raise ValueError('Invalid path: contains suspicious characters')
        
        # Check for absolute paths (should be relative)
        if v.startswith('/'):
            raise ValueError('Invalid path: must be relative')
        
        # Limit path length
        if len(v) > 500:
            raise ValueError('Invalid path: too long')
        
        return v

class FileItem(BaseModel):
    name: str = Field(..., max_length=255)
    type: Literal['file', 'directory']
    path: str = Field(..., max_length=500)
    size: Optional[int] = None
    mount: bool = False
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        if len(v) > 255:
            raise ValueError('Name too long')
        return v.strip()
    
    @validator('path')
    def validate_path(cls, v):
        if '..' in v:
            raise ValueError('Invalid path: cannot contain ".."')
        return v

class ErrorResponse(BaseModel):
    error: str = Field(..., max_length=1000)
    details: Optional[dict] = None

class SuccessResponse(BaseModel):
    status: Literal['success']
    job_id: Optional[str] = Field(None, max_length=36)

class TranscribeRequest(BaseModel):
    path: str = Field(..., description="Path to video file, relative to /mnt", max_length=500)
    position: Optional[int] = Field(None, ge=0, le=1000, description="Optional position in queue")
    
    @validator('path')
    def validate_path(cls, v):
        # Check for directory traversal attempts
        if '..' in v:
            raise ValueError('Invalid path: cannot contain ".."')
        
        # Check for suspicious characters
        suspicious_chars = ['<', '>', '"', "'", '&', '|', ';', '`', '$', '(', ')']
        if any(char in v for char in suspicious_chars):
            raise ValueError('Invalid path: contains suspicious characters')
        
        # Check for absolute paths (should be relative)
        if v.startswith('/'):
            raise ValueError('Invalid path: must be relative')
        
        # Validate file extension
        allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.mpeg', '.mpg'}
        file_ext = Path(v).suffix.lower()
        if file_ext not in allowed_extensions:
            raise ValueError(f'Invalid file type: {file_ext}. Allowed: {", ".join(allowed_extensions)}')
        
        return v

class QueueReorderRequest(BaseModel):
    job_id: str = Field(..., description="ID of the job to reorder", max_length=36, min_length=1)
    position: int = Field(..., description="New position in queue (0-based)", ge=0, le=1000)
    
    @validator('job_id')
    def validate_job_id(cls, v):
        # Validate UUID format or custom job ID format
        if not re.match(r'^[a-zA-Z0-9\-_]{1,36}$', v):
            raise ValueError('Invalid job ID format')
        return v

class JobStatus(BaseModel):
    id: str = Field(..., max_length=36)
    status: str = Field(..., pattern='^(queued|processing|paused|completed|failed)$')
    video_path: str = Field(..., max_length=500)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    progress: Optional[float] = Field(None, ge=0, le=100)
    status_message: Optional[str] = Field(None, max_length=1000)
    error_details: Optional[dict] = None
    start_time: Optional[float] = Field(None, ge=0)
    time_remaining: Optional[float] = Field(None, ge=0)
    transcribed_duration: Optional[float] = Field(None, ge=0)
    total_duration: Optional[float] = Field(None, ge=0)
    position: Optional[int] = Field(0, ge=0, le=1000)
    error: Optional[str] = Field(None, max_length=1000)
    result: Optional[dict] = None
    
    @validator('video_path')
    def validate_video_path(cls, v):
        if '..' in v:
            raise ValueError('Invalid video path: cannot contain ".."')
        return v
    
    @validator('status_message', 'error')
    def validate_text_fields(cls, v):
        if v is not None:
            # Remove any potential HTML/script tags
            v = re.sub(r'<[^>]*>', '', v)
            # Limit length
            if len(v) > 1000:
                v = v[:997] + '...'
        return v

class BatchTranscribeRequest(BaseModel):
    paths: List[str] = Field(..., description="List of video file paths", min_items=1, max_items=100)
    
    @validator('paths')
    def validate_paths(cls, v):
        if len(v) > 100:
            raise ValueError('Too many files in batch request (max 100)')
        
        for path in v:
            # Validate each path
            if '..' in path:
                raise ValueError(f'Invalid path: cannot contain ".." - {path}')
            
            suspicious_chars = ['<', '>', '"', "'", '&', '|', ';', '`', '$', '(', ')']
            if any(char in path for char in suspicious_chars):
                raise ValueError(f'Invalid path: contains suspicious characters - {path}')
            
            if path.startswith('/'):
                raise ValueError(f'Invalid path: must be relative - {path}')
            
            # Validate file extension
            allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.mpeg', '.mpg'}
            file_ext = Path(path).suffix.lower()
            if file_ext not in allowed_extensions:
                raise ValueError(f'Invalid file type: {file_ext} - {path}')
        
        return v

class SecurityConfig(BaseModel):
    """Security configuration model"""
    max_file_size: int = Field(10 * 1024 * 1024 * 1024, description="Maximum file size in bytes")
    allowed_extensions: List[str] = Field(['.mp4', '.avi', '.mov', '.mkv', '.mpeg', '.mpg'])
    max_batch_size: int = Field(100, description="Maximum files per batch request")
    rate_limit_requests: int = Field(200, description="Rate limit requests per day")
    rate_limit_window: int = Field(3600, description="Rate limit window in seconds")
    
    @validator('allowed_extensions')
    def validate_extensions(cls, v):
        for ext in v:
            if not ext.startswith('.') or len(ext) < 2:
                raise ValueError(f'Invalid extension format: {ext}')
        return v

class AuditLogEntry(BaseModel):
    """Audit log entry model for security events"""
    timestamp: datetime
    event_type: str = Field(..., pattern='^(login|logout|file_access|file_upload|file_delete|admin_action)$')
    user_id: Optional[str] = Field(None, max_length=36)
    ip_address: str = Field(..., max_length=45)  # IPv6 compatible
    user_agent: Optional[str] = Field(None, max_length=500)
    resource: Optional[str] = Field(None, max_length=500)
    action: str = Field(..., max_length=100)
    status: Literal['success', 'failure', 'error']
    details: Optional[dict] = None
    
    @validator('ip_address')
    def validate_ip_address(cls, v):
        # Basic IP address validation
        if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$|^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$', v):
            raise ValueError('Invalid IP address format')
        return v 

class CablecastShowORM(db.Model):
    __tablename__ = 'cablecast_shows'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration = db.Column(db.Integer, nullable=True)  # in seconds
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    cablecast_id = db.Column(db.Integer, unique=True, nullable=False)
    transcription_id = db.Column(db.String(36), db.ForeignKey('transcription_results.id'), nullable=True)
    
    transcription = db.relationship('TranscriptionResultORM', backref='cablecast_shows')

class CablecastVODORM(db.Model):
    __tablename__ = 'cablecast_vods'
    
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('cablecast_shows.id'), nullable=False)
    quality = db.Column(db.Integer, nullable=False)  # VODTranscodeQuality ID
    file_name = db.Column(db.String(255), nullable=False)
    length = db.Column(db.Integer, nullable=True)  # in seconds
    url = db.Column(db.String(500), nullable=True)
    embed_code = db.Column(db.Text, nullable=True)
    web_vtt_url = db.Column(db.String(500), nullable=True)  # for chapters
    vod_state = db.Column(db.String(50), nullable=False, default='processing')
    percent_complete = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    show = db.relationship('CablecastShowORM', backref='vods')

class CablecastVODChapterORM(db.Model):
    __tablename__ = 'cablecast_vod_chapters'
    
    id = db.Column(db.Integer, primary_key=True)
    vod_id = db.Column(db.Integer, db.ForeignKey('cablecast_vods.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    start_time = db.Column(db.Float, nullable=False)  # in seconds
    end_time = db.Column(db.Float, nullable=True)  # in seconds
    description = db.Column(db.Text, nullable=True)
    
    vod = db.relationship('CablecastVODORM', backref='chapters')

# VOD Integration Pydantic Models
class VODContentRequest(BaseModel):
    title: str = Field(..., max_length=255, description="Content title")
    description: Optional[str] = Field(None, max_length=2000, description="Content description")
    file_path: str = Field(..., max_length=500, description="Path to video file")
    auto_transcribe: bool = Field(True, description="Automatically transcribe the video")
    
    @validator('file_path')
    def validate_file_path(cls, v):
        if '..' in v:
            raise ValueError('Invalid path: cannot contain ".."')
        return v

class VODContentResponse(BaseModel):
    id: str = Field(..., max_length=36)
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    file_path: str = Field(..., max_length=500)
    duration: Optional[float] = None
    resolution: Optional[str] = None
    status: str = Field(..., pattern='^(processing|ready|error)$')
    created_at: datetime
    updated_at: datetime
    transcription_available: bool = False
    stream_url: Optional[str] = None

class VODPlaylistRequest(BaseModel):
    name: str = Field(..., max_length=255, description="Playlist name")
    description: Optional[str] = Field(None, max_length=2000, description="Playlist description")
    is_public: bool = Field(False, description="Whether playlist is public")
    content_ids: List[str] = Field(default=[], description="List of content IDs to add")

class VODStreamRequest(BaseModel):
    content_id: str = Field(..., max_length=36, description="Content ID to stream")
    quality: Optional[str] = Field(None, pattern='^(low|medium|high|original)$', description="Stream quality")
    start_time: Optional[float] = Field(None, ge=0, description="Start time in seconds")

class VODPublishRequest(BaseModel):
    quality: Optional[int] = Field(1, ge=1, le=10, description="VOD quality setting")
    auto_transcribe: bool = Field(True, description="Automatically transcribe if not already done")

class VODBatchPublishRequest(BaseModel):
    transcription_ids: List[str] = Field(..., min_items=1, max_items=100, description="List of transcription IDs to publish")
    quality: Optional[int] = Field(1, ge=1, le=10, description="VOD quality setting")

class VODSyncStatusResponse(BaseModel):
    total_transcriptions: int = Field(..., ge=0)
    synced_transcriptions: int = Field(..., ge=0)
    sync_percentage: float = Field(..., ge=0, le=100)
    recent_syncs: List[Dict[str, Any]] = Field(default=[])

class CablecastShowResponse(BaseModel):
    id: int = Field(..., description="Cablecast show ID")
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    duration: Optional[int] = None
    created_at: datetime
    transcription_available: bool = False
    vod_count: int = Field(0, ge=0) 