"""This module handles video and audio transcription using faster-whisper directly,
providing high-quality speech-to-text conversion with timestamp alignment.

Key Features:
- Video and audio transcription
- Timestamp alignment
- Progress tracking
- Error handling and recovery
- Support for multiple languages
- CPU-optimized processing
- Debug mode for troubleshooting

Example:
    >>> from core.transcription import run_whisper_transcription
    >>> result = run_whisper_transcription('video.mp4')
    >>> print(result['segments'])
"""

import os
import shutil
from loguru import logger
import time
import traceback
from typing import Dict, Any, Optional
import sys
import platform
import psutil
import json
from datetime import datetime

# Debug mode configuration
DEBUG_MODE = os.getenv('TRANSCRIPTION_DEBUG', 'false').lower() == 'true'
DEBUG_LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs', 'transcription')

def setup_debug_logging():
    """Set up debug logging if debug mode is enabled."""
    if DEBUG_MODE:
        os.makedirs(DEBUG_LOG_DIR, exist_ok=True)
        debug_log_file = os.path.join(DEBUG_LOG_DIR, f'transcription_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logger.add(debug_log_file, level="DEBUG", rotation="1 day", retention="7 days")
        logger.info(f"Debug logging enabled. Log file: {debug_log_file}")

def log_debug_info(context: str, data: Dict[str, Any]) -> None:
    """Log debug information if debug mode is enabled."""
    if DEBUG_MODE:
        debug_file = os.path.join(DEBUG_LOG_DIR, f'debug_{context}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        try:
            with open(debug_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"Debug info saved to {debug_file}")
        except Exception as e:
            logger.error(f"Failed to save debug info: {e}")

def get_system_info() -> Dict[str, Any]:
    """Get system information for debugging."""
    return {
        'python_version': sys.version,
        'platform': platform.platform(),
        'cpu_count': os.cpu_count(),
        'memory_available': psutil.virtual_memory().available if 'psutil' in sys.modules else None,
        'disk_usage': psutil.disk_usage('/')._asdict() if 'psutil' in sys.modules else None,
        'process_info': {
            'pid': os.getpid(),
            'ppid': os.getppid(),
            'user': os.getlogin(),
            'groups': os.getgroups()
        }
    }

# Initialize debug logging
setup_debug_logging()

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

def verify_file_operation(source_path: str, dest_path: str, operation: str = "copy") -> None:
    """Verify file operations (copy, move, write) were successful."""
    try:
        if not os.path.exists(dest_path):
            raise FileNotFoundError(f"Destination file not found after {operation}: {dest_path}")
            
        if operation in ["copy", "move"]:
            source_size = os.path.getsize(source_path)
            dest_size = os.path.getsize(dest_path)
            if source_size != dest_size:
                raise IOError(f"Size mismatch after {operation} (source: {source_size}, dest: {dest_size})")
                
            # Verify file contents if it's a text file
            if dest_path.endswith('.srt'):
                with open(source_path, 'r', encoding='utf-8') as f1, open(dest_path, 'r', encoding='utf-8') as f2:
                    source_content = f1.read()
                    dest_content = f2.read()
                    if source_content != dest_content:
                        raise IOError(f"Content mismatch after {operation}")
                        
        logger.debug(f"Successfully verified {operation} operation: {dest_path}")
    except Exception as e:
        logger.error(f"File operation verification failed: {e}")
        raise

def save_srt_file(segments: list, output_path: str) -> None:
    """Save transcription segments to an SRT file."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, segment in enumerate(segments, 1):
                start = format_timestamp(segment["start"])
                end = format_timestamp(segment["end"])
                text = segment["text"]
                f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")
        logger.info(f"Successfully wrote SRT file: {output_path}")
        
        # Verify the file was written correctly
        verify_file_operation(output_path, output_path, "write")
    except IOError as e:
        logger.error(f"Failed to write SRT file {output_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error writing SRT file {output_path}: {e}")
        raise

def ensure_directory_exists(path: str) -> None:
    """Ensure directory exists and has correct permissions."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Set group permissions if the directory is in /mnt/flex-*
    if '/mnt/flex-' in path:
        try:
            os.chmod(os.path.dirname(path), 0o775)
            # Try to set group ownership to transcription_users
            import grp
            transcription_gid = grp.getgrnam('transcription_users').gr_gid
            os.chown(os.path.dirname(path), -1, transcription_gid)
        except Exception as e:
            logger.warning(f"Could not set permissions on {path}: {e}")

def update_job_progress(current_job, progress: int, status: str, error: str = None) -> None:
    """Update job progress with error handling and validation."""
    try:
        if current_job:
            # Validate progress value
            progress = max(0, min(100, progress))
            
            # Calculate time remaining if we have start time
            time_remaining = None
            if current_job.meta.get('start_time'):
                elapsed = time.time() - current_job.meta['start_time']
                if progress > 0:
                    time_remaining = (elapsed / progress) * (100 - progress)
            
            # Update metadata
            current_job.meta.update({
                'progress': progress,
                'status_message': status,
                'last_update': time.time(),
                'time_remaining': time_remaining,
                'error': error
            })
            current_job.save_meta()
            logger.debug(f"Updated job progress: {progress}% - {status}")
    except Exception as e:
        logger.error(f"Failed to update job progress: {e}")

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
        
        # Log debug information at start
        if DEBUG_MODE:
            log_debug_info('start', {
                'video_path': video_path,
                'system_info': get_system_info(),
                'environment': dict(os.environ)
            })
        
        # Get current job for progress updates
        current_job = get_current_job()
        if current_job:
            logger.debug(f"Job ID: {current_job.id}")
            update_job_progress(current_job, 0, "Initializing transcription...")

        # Validate input file
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")
                
            # Check file size
            file_size = os.path.getsize(video_path)
            logger.debug(f"Video file size: {file_size} bytes")
            if file_size == 0:
                raise ValueError(f"Video file is empty: {video_path}")
                
            # Check file permissions
            if not os.access(video_path, os.R_OK):
                raise PermissionError(f"No read permission for file: {video_path}")
        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"File access error: {e}")
            raise
        except OSError as e:
            logger.error(f"OS error during file validation: {e}")
            raise

        # Get video directory and filename
        try:
            video_dir = os.path.dirname(video_path)
            video_name = os.path.basename(video_path)
            srt_name = f"{os.path.splitext(video_name)[0]}.srt"
            logger.debug(f"Video directory: {video_dir}")
            logger.debug(f"Video name: {video_name}")
            logger.debug(f"SRT name: {srt_name}")
        except Exception as e:
            logger.error(f"Error processing file paths: {e}")
            raise

        # Set up output paths
        local_srt_path = os.path.join(video_dir, srt_name)
        central_srt_path = os.path.join(OUTPUT_DIR, srt_name)
        logger.debug(f"Local SRT path: {local_srt_path}")
        logger.debug(f"Central SRT path: {central_srt_path}")

        # Ensure directories exist with correct permissions
        try:
            ensure_directory_exists(local_srt_path)
            ensure_directory_exists(central_srt_path)
            logger.debug("Created output directories")
        except OSError as e:
            logger.error(f"Error creating directories: {e}")
            raise

        # Update status for model loading
        if current_job:
            update_job_progress(current_job, 10, "Loading Whisper model...")

        # Set the target directory for model downloads
        try:
            target_dir = "/opt/Archivist/.venv/lib/python3.11/site-packages/faster_whisper/assets"
            os.makedirs(target_dir, exist_ok=True)
            logger.debug(f"Model target directory: {target_dir}")
        except OSError as e:
            logger.error(f"Error creating model directory: {e}")
            raise

        # Load whisper model for transcription with CPU optimizations
        try:
            logger.info("Loading Whisper model...")
            model = WhisperModel(
                WHISPER_MODEL,
                device=device,
                compute_type=compute_type,
                cpu_threads=4,
                num_workers=1,
                download_root=target_dir
            )
            logger.info(f"Successfully loaded Whisper model: {WHISPER_MODEL}")
            if current_job:
                update_job_progress(current_job, 20, "Model loaded successfully")
        except Exception as e:
            if current_job:
                update_job_progress(current_job, 0, "Failed to load model", str(e))
            raise

        # Transcribe with progress updates
        try:
            logger.info("Starting transcription...")
            if current_job:
                update_job_progress(current_job, 30, "Starting transcription...")
                
            segments, info = model.transcribe(
                video_path,
                language=LANGUAGE,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            if current_job:
                update_job_progress(current_job, 70, "Transcription completed, processing segments...")
                
            logger.info("Transcription completed")
        except Exception as e:
            if current_job:
                update_job_progress(current_job, 0, "Transcription failed", str(e))
            raise

        # Convert segments to list and format timestamps
        try:
            formatted_segments = []
            for segment in segments:
                formatted_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
            logger.debug(f"Formatted {len(formatted_segments)} segments")
            
            if current_job:
                update_job_progress(current_job, 80, "Segments formatted, saving files...")
        except Exception as e:
            if current_job:
                update_job_progress(current_job, 0, "Failed to format segments", str(e))
            raise

        # Save SRT file next to the video
        try:
            logger.info(f"Saving SRT file: {local_srt_path}")
            save_srt_file(formatted_segments, local_srt_path)
            if current_job:
                update_job_progress(current_job, 90, "Local SRT file saved, copying to central location...")
        except Exception as e:
            if current_job:
                update_job_progress(current_job, 0, "Failed to save SRT file", str(e))
            raise
        
        # Copy to central location
        try:
            logger.info(f"Copying SRT file to central location: {central_srt_path}")
            shutil.copy2(local_srt_path, central_srt_path)
            verify_file_operation(local_srt_path, central_srt_path, "copy")
            if current_job:
                update_job_progress(current_job, 100, f"Completed! Generated transcript with {len(formatted_segments)} segments")
        except Exception as e:
            if current_job:
                update_job_progress(current_job, 0, "Failed to copy to central location", str(e))
            raise

        # Set correct permissions on both files
        try:
            if '/mnt/flex-' in local_srt_path:
                import grp
                transcription_gid = grp.getgrnam('transcription_users').gr_gid
                os.chmod(local_srt_path, 0o664)
                os.chown(local_srt_path, -1, transcription_gid)
                logger.debug(f"Set permissions on {local_srt_path}")
        except (grp.KeyError, PermissionError) as e:
            logger.warning(f"Could not set permissions on {local_srt_path}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error setting permissions: {e}")

        logger.info("Transcription process completed successfully")
        
        # Log debug information at end
        if DEBUG_MODE:
            log_debug_info('end', {
                'success': True,
                'srt_path': local_srt_path,
                'central_srt_path': central_srt_path,
                'segments': len(formatted_segments),
                'duration': formatted_segments[-1]["end"] if formatted_segments else 0
            })
            
        return {
            'srt_path': local_srt_path,
            'central_srt_path': central_srt_path,
            'segments': len(formatted_segments),
            'duration': formatted_segments[-1]["end"] if formatted_segments else 0
        }

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        error_details = {
            'type': error_type,
            'message': error_msg,
            'traceback': traceback.format_exc(),
            'video_path': video_path,
            'video_size': os.path.getsize(video_path) if os.path.exists(video_path) else None,
            'video_permissions': oct(os.stat(video_path).st_mode)[-3:] if os.path.exists(video_path) else None,
            'model': WHISPER_MODEL,
            'language': LANGUAGE,
            'device': device,
            'compute_type': compute_type,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system_info': get_system_info(),
            'job_info': {
                'job_id': current_job.id if current_job else None,
                'start_time': current_job.meta.get('start_time') if current_job else None,
                'progress': current_job.meta.get('progress') if current_job else None
            } if current_job else None
        }
        
        # Log error details in debug mode
        if DEBUG_MODE:
            log_debug_info('error', error_details)
        
        logger.error(f"Transcription error ({error_type}): {error_msg}")
        logger.debug(f"Error details: {error_details}")
        
        if current_job:
            current_job.meta.update({
                'error_details': error_details,
                'status_message': f"Error ({error_type}): {error_msg}",
                'failed_at': time.time()
            })
            current_job.save_meta()
        
        return {
            'success': False,
            'error': error_msg,
            'error_details': error_details
        }