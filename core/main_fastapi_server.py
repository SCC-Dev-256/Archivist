from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
from loguru import logger
from core.config import NAS_PATH, OUTPUT_DIR
import sys

from core.transcription import run_whisperx
from core.scc_summarizer import summarize_srt
from core.task_queue import enqueue_transcription, get_job_status
from core.check_mounts import verify_critical_mounts

app = FastAPI(
    title="Video Transcription API",
    description="API for video transcription and summarization using WhisperX",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranscriptionRequest(BaseModel):
    video_path: str

@app.get("/files", response_model=List[str])
async def list_videos():
    """List all MP4 files in the configured NAS directory."""
    try:
        return [f for f in os.listdir(NAS_PATH) if f.endswith(".mp4")]
    except Exception as e:
        logger.error(f"Error listing videos: {e}")
        raise HTTPException(status_code=500, detail="Error accessing NAS directory")

@app.post("/transcribe")
async def transcribe(request: TranscriptionRequest):
    """Start a transcription job for the given video file."""
    try:
        video_path = os.path.join(NAS_PATH, request.video_path)
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Video file not found")
        
        job_id = enqueue_transcription(video_path)
        return {"job_id": job_id}
    except Exception as e:
        logger.error(f"Error starting transcription: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get the status of a transcription job."""
    try:
        return get_job_status(job_id)
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/summary/{video_id}")
async def get_summary(video_id: str):
    """Get the meeting minutes summary for a video."""
    try:
        summary_path = os.path.join(OUTPUT_DIR, f"{video_id}_minutes.json")
        if not os.path.exists(summary_path):
            raise HTTPException(status_code=404, detail="Summary not found")
        return FileResponse(summary_path, media_type='application/json')
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    if not verify_critical_mounts():
        logger.critical("Critical mounts missing - preventing startup!")
        sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT, API_WORKERS
    
    uvicorn.run(
        "main_fastapi_server:app",
        host=API_HOST,
        port=API_PORT,
        workers=API_WORKERS,
        reload=True
    )
