"""This module handles video and audio transcription using faster-whisper directly,
providing high-quality speech-to-text conversion with timestamp alignment.

Key Features:
- Video and audio transcription
- Timestamp alignment
- Progress tracking
- Error handling and recovery
- Support for multiple languages
- CPU-optimized processing

Example:
    >>> from core.transcription import run_whisper_transcription
    >>> result = run_whisper_transcription('video.mp4')
    >>> print(result['segments'])
"""

import os
from loguru import logger
import time
import traceback
from typing import Dict, Any

# Force CPU-only mode before importing torch
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Disable CUDA
os.environ['TORCH_USE_CUDA_DSA'] = '0'     # Disable CUDA DSA

import torch
torch.cuda.is_available = lambda: False
device = "cpu"
compute_type = "float32"

# Patch torch.load globally to set weights_only=False
_original_load = torch.load

def patched_load(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _original_load(*args, **kwargs)

torch.load = patched_load

from faster_whisper import WhisperModel
from core.config import (
    WHISPER_MODEL, COMPUTE_TYPE, OUTPUT_DIR,
    BATCH_SIZE, NUM_WORKERS, LANGUAGE, NAS_PATH
)

def get_current_job():
    try:
        from rq import get_current_job as rq_get_current_job
        return rq_get_current_job()
    except:
        return None

def format_timestamp(seconds: float) -> str:
    """Format seconds into SRT timestamp format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")

def run_whisper_transcription(video_path: str) -> Dict[str, Any]:
    """
    Transcribe video using faster-whisper with optimizations.
    
    This function provides a complete audio transcription pipeline including:
    - Audio extraction from video files
    - Speech-to-text transcription with timestamps
    - SRT subtitle generation with proper formatting
    
    Args:
        video_path (str): Absolute path to the video file to transcribe
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - success (bool): Whether transcription succeeded
            - srt_path (str): Path to generated SRT file (if successful)
            - segments (int): Number of transcription segments
            - duration (float): Total audio duration in seconds
            - error (str): Error message (if failed)
            
    Raises:
        FileNotFoundError: If video file doesn't exist
        ValueError: If video file is invalid or corrupted
        RuntimeError: If transcription process fails
    """
    try:
        logger.info(f"Starting transcription of {video_path}")
        
        # Get current job for progress updates
        current_job = get_current_job()
        if current_job:
            current_job.meta.update({
                'start_time': time.time(),
                'progress': 0,
                'status_message': 'Initializing transcription...',
                'error_details': None
            })
            current_job.save_meta()

        # Validate input file
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        # Check file size
        file_size = os.path.getsize(video_path)
        if file_size == 0:
            raise ValueError(f"Video file is empty: {video_path}")
            
        # Check file permissions
        if not os.access(video_path, os.R_OK):
            raise PermissionError(f"No read permission for file: {video_path}")

        # Use OUTPUT_DIR for output files
        if not os.access(OUTPUT_DIR, os.W_OK):
            raise PermissionError(f"No write permission for output directory: {OUTPUT_DIR}")

        # Get relative path structure
        rel_path = os.path.relpath(video_path, NAS_PATH)
        output_subdir = os.path.dirname(rel_path)
        output_path = os.path.join(OUTPUT_DIR, output_subdir)
        os.makedirs(output_path, exist_ok=True)

        # Update status
        if current_job:
            current_job.meta['status_message'] = 'Loading Whisper model...'
            current_job.save_meta()

        # Set the target directory for model downloads
        target_dir = "/opt/Archivist/.venv/lib/python3.11/site-packages/faster_whisper/assets"
        os.makedirs(target_dir, exist_ok=True)

        # Load whisper model for transcription with CPU optimizations
        model = WhisperModel(
            WHISPER_MODEL,
            device=device,
            compute_type=compute_type,
            cpu_threads=4,  # Adjust based on your CPU
            num_workers=1,  # Reduce for CPU
            download_root=target_dir
        )

        # Transcribe with progress updates
        segments, info = model.transcribe(
            video_path,
            language=LANGUAGE,
            beam_size=5,
            vad_filter=True,  # Enable VAD filtering
            vad_parameters=dict(min_silence_duration_ms=500)  # Adjust VAD parameters
        )

        # Convert segments to list and format timestamps
        formatted_segments = []
        for segment in segments:
            formatted_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            })

        # Save results
        output_file = os.path.join(output_path, f"{os.path.basename(video_path)}.srt")
        with open(output_file, "w", encoding="utf-8") as f:
            for idx, segment in enumerate(formatted_segments, 1):
                start = format_timestamp(segment["start"])
                end = format_timestamp(segment["end"])
                text = segment["text"]
                f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")

        if current_job:
            current_job.meta.update({
                'progress': 100,
                'status_message': f'Completed! Generated transcript with {len(formatted_segments)} segments',
                'time_remaining': 0
            })
            current_job.save_meta()

        return {
            'srt_path': output_file,
            'segments': len(formatted_segments),
            'duration': formatted_segments[-1]["end"] if formatted_segments else 0
        }

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        error_details = {
            'type': error_type,
            'message': error_msg,
            'traceback': traceback.format_exc()
        }
        
        logger.error(f"Transcription error ({error_type}): {error_msg}")
        if current_job:
            current_job.meta.update({
                'error_details': error_details,
                'status_message': f"Error ({error_type}): {error_msg}",
                'failed_at': time.time()
            })
            current_job.save_meta()
        raise