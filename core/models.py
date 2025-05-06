from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
import os
from pathlib import Path

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