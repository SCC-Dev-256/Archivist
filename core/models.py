from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
import os
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

Base = db.Model

class BrowseRequest(BaseModel):
    path: str = Field(default="", description="Path to browse, relative to NAS_PATH")
    
    @validator('path')
    def validate_path(cls, v):
        if '..' in v or v.startswith('/'):
            raise ValueError('Invalid path: cannot contain ".." or start with "/"')
        return v

class TranscribeRequest(BaseModel):
    path: str = Field(..., description="Path to video file, relative to /mnt")
    position: Optional[int] = Field(None, description="Optional position in queue")
    
    @validator('path')
    def validate_path(cls, v):
        if '..' in v or v.startswith('/'):
            raise ValueError('Invalid path: cannot contain ".." or start with "/"')
        if not v.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.mpeg', '.mpg')):
            raise ValueError('Invalid file type: must be a video file')
        return v

class QueueReorderRequest(BaseModel):
    job_id: str = Field(..., description="ID of the job to reorder")
    position: int = Field(..., ge=0, description="New position in queue (0-based)")

class JobStatus(BaseModel):
    id: str
    video_path: str
    status: Literal['queued', 'processing', 'paused', 'completed', 'failed']
    progress: Optional[float] = Field(None, ge=0, le=100)
    status_message: Optional[str]
    error_details: Optional[dict]
    start_time: Optional[float]
    time_remaining: Optional[float]
    transcribed_duration: Optional[float]
    total_duration: Optional[float]

class FileItem(BaseModel):
    name: str
    type: Literal['directory', 'file']
    path: str
    size: Optional[str]
    mount: Optional[bool] = False

class ErrorResponse(BaseModel):
    error: str
    details: Optional[dict] = None

class SuccessResponse(BaseModel):
    status: Literal['success']
    job_id: Optional[str] = None

class TranscriptionJob(BaseModel):
    id: str
    video_path: str
    status: Literal['queued', 'processing', 'paused', 'completed', 'failed']
    progress: Optional[float] = Field(None, ge=0, le=100)
    status_message: Optional[str]
    error_details: Optional[dict]
    start_time: Optional[float]
    time_remaining: Optional[float]
    transcribed_duration: Optional[float]
    total_duration: Optional[float]
    position: Optional[int]

class TranscriptionResult(BaseModel):
    id: str
    video_path: str
    completed_at: str  # ISO format string
    status: Literal['completed', 'failed']
    output_path: Optional[str]
    error_details: Optional[dict] = None

class TranscriptionJobORM(db.Model):
    __tablename__ = 'transcription_jobs'
    id = db.Column(db.String, primary_key=True)
    video_path = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)
    progress = db.Column(db.Float)
    status_message = db.Column(db.String)
    error_details = db.Column(db.JSON)
    start_time = db.Column(db.Float)
    time_remaining = db.Column(db.Float)
    transcribed_duration = db.Column(db.Float)
    total_duration = db.Column(db.Float)
    position = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TranscriptionResultORM(db.Model):
    __tablename__ = 'transcription_results'
    id = db.Column(db.String, primary_key=True)
    video_path = db.Column(db.String, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String, nullable=False)
    output_path = db.Column(db.String)
    error_details = db.Column(db.JSON) 