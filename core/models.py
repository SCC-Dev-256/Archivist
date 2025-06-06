from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
import os
from pathlib import Path
from datetime import datetime

from core.app import db

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
    path: str = Field(default="", description="Path to browse, relative to NAS_PATH")
    
    @validator('path')
    def validate_path(cls, v):
        if '..' in v:
            raise ValueError('Invalid path: cannot contain ".."')
        return v

class FileItem(BaseModel):
    name: str
    type: Literal['file', 'directory']
    path: str
    size: Optional[int] = None
    mount: bool = False

class ErrorResponse(BaseModel):
    error: str

class SuccessResponse(BaseModel):
    status: Literal['success']
    job_id: Optional[str] = None

class TranscribeRequest(BaseModel):
    path: str

class QueueReorderRequest(BaseModel):
    job_id: str
    position: int

class JobStatus(BaseModel):
    id: str
    status: str
    video_path: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    progress: Optional[float] = 0
    status_message: Optional[str] = None
    error_details: Optional[dict] = None
    start_time: Optional[float] = None
    time_remaining: Optional[float] = None
    transcribed_duration: Optional[float] = None
    total_duration: Optional[float] = None
    position: Optional[int] = 0
    error: Optional[str] = None
    result: Optional[dict] = None 