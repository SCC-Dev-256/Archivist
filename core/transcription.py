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
- SCC (Scenarist Closed Caption) format output

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
from typing import Dict, Any, Optional, List
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

def format_smpte_timestamp(seconds: float, is_drop_frame: bool = False) -> str:
    """Format seconds into SMPTE timestamp format for SCC files.
    
    Args:
        seconds: Time in seconds
        is_drop_frame: Whether to use drop frame format (29.97fps)
        
    Returns:
        SMPTE timestamp string in format HH:MM:SS;FF or HH:MM:SS:FF
    """
    # Use 29.97 fps for both drop and non-drop frame
    fps = 29.97
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining_seconds = seconds % 60
    
    # Extract whole seconds and fractional part
    whole_seconds = int(remaining_seconds)
    fractional_part = remaining_seconds - whole_seconds
    
    # Calculate frames
    frames = int(fractional_part * fps)
    
    # Use semicolon for drop frame, colon for non-drop frame
    separator = ";" if is_drop_frame else ":"
    
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}{separator}{frames:02d}"

def text_to_cea608_hex(text: str) -> List[str]:
    """Convert text to CEA-608 hexadecimal encoding.
    
    Args:
        text: Text to encode
        
    Returns:
        List of hex strings representing the text
    """
    # CEA-608 character mapping (simplified)
    # This is a basic mapping - full implementation would include all CEA-608 characters
    char_map = {
        ' ': '20', '!': '21', '"': '22', '#': '23', '$': '24', '%': '25', '&': '26', "'": '27',
        '(': '28', ')': '29', '*': '2A', '+': '2B', ',': '2C', '-': '2D', '.': '2E', '/': '2F',
        '0': '30', '1': '31', '2': '32', '3': '33', '4': '34', '5': '35', '6': '36', '7': '37',
        '8': '38', '9': '39', ':': '3A', ';': '3B', '<': '3C', '=': '3D', '>': '3E', '?': '3F',
        '@': '40', 'A': '41', 'B': '42', 'C': '43', 'D': '44', 'E': '45', 'F': '46', 'G': '47',
        'H': '48', 'I': '49', 'J': '4A', 'K': '4B', 'L': '4C', 'M': '4D', 'N': '4E', 'O': '4F',
        'P': '50', 'Q': '51', 'R': '52', 'S': '53', 'T': '54', 'U': '55', 'V': '56', 'W': '57',
        'X': '58', 'Y': '59', 'Z': '5A', '[': '5B', '\\': '5C', ']': '5D', '^': '5E', '_': '5F',
        '`': '60', 'a': '61', 'b': '62', 'c': '63', 'd': '64', 'e': '65', 'f': '66', 'g': '67',
        'h': '68', 'i': '69', 'j': '6A', 'k': '6B', 'l': '6C', 'm': '6D', 'n': '6E', 'o': '6F',
        'p': '70', 'q': '71', 'r': '72', 's': '73', 't': '74', 'u': '75', 'v': '76', 'w': '77',
        'x': '78', 'y': '79', 'z': '7A', '{': '7B', '|': '7C', '}': '7D', '~': '7E'
    }
    
    hex_chars = []
    for char in text:
        if char in char_map:
            hex_chars.append(char_map[char])
        else:
            # Unknown character, use space
            hex_chars.append('20')
    
    return hex_chars

def generate_pac_code(row: int, column: int = 0) -> str:
    """Generate Preamble Address Code (PAC) for SCC positioning.
    
    Args:
        row: Row number (1-15)
        column: Column number (0, 4, 8, 12, 16, 20, 24, 28)
        
    Returns:
        PAC code as hex string
    """
    # Simplified PAC generation - basic positioning
    # This is a basic implementation for common positions
    
    # PAC codes for row 15 (bottom row) at different columns
    pac_codes = {
        (15, 0): '947a',
        (15, 4): '94f2',
        (14, 0): '947a',
        (14, 4): '94f2',
        (13, 0): '947a',
        (13, 4): '94f2',
        (12, 0): '947a',
        (12, 4): '94f2',
        (11, 0): '947a',
        (11, 4): '94f2',
    }
    
    # Default to bottom row, left position
    return pac_codes.get((row, column), '947a')

def save_scc_file(segments: List[Dict], output_path: str) -> None:
    """Save transcription segments to an SCC file.
    
    Args:
        segments: List of segment dictionaries with 'start', 'end', 'text' keys
        output_path: Path to output SCC file
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            # Write SCC header
            f.write("Scenarist_SCC V1.0\n\n")
            
            for segment in segments:
                start_time = segment["start"]
                end_time = segment["end"]
                text = segment["text"].strip()
                
                # Skip empty segments
                if not text:
                    continue
                
                # Format timestamps (using non-drop frame format)
                start_timecode = format_smpte_timestamp(start_time, is_drop_frame=False)
                end_timecode = format_smpte_timestamp(end_time, is_drop_frame=False)
                
                # Split text into lines if it's too long (32 char limit per line)
                lines = []
                words = text.split()
                current_line = ""
                
                for word in words:
                    if len(current_line + " " + word) <= 32:
                        current_line += (" " + word) if current_line else word
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                
                if current_line:
                    lines.append(current_line)
                
                # Ensure we don't exceed 4 lines
                lines = lines[:4]
                
                # Generate SCC data for pop-on caption
                scc_data = []
                
                # ENM (Erase Non-displayed Memory) - doubled for redundancy
                scc_data.extend(['94ae', '94ae'])
                
                # RCL (Resume Caption Loading) - doubled for redundancy
                scc_data.extend(['9420', '9420'])
                
                # Generate PAC (Preamble Address Code) for positioning
                # Start at bottom row and work up
                start_row = 15 - len(lines) + 1
                
                for i, line in enumerate(lines):
                    row = start_row + i
                    pac_code = generate_pac_code(row, 0)
                    scc_data.extend([pac_code, pac_code])  # Double for redundancy
                    
                    # Convert text to hex
                    hex_chars = text_to_cea608_hex(line)
                    
                    # Group hex chars into pairs for 2-byte words
                    for j in range(0, len(hex_chars), 2):
                        if j + 1 < len(hex_chars):
                            word = hex_chars[j] + hex_chars[j + 1]
                        else:
                            word = hex_chars[j] + '80'  # Pad with 80 for odd number of chars
                        scc_data.append(word)
                
                # EDM (Erase Displayed Memory) - doubled for redundancy
                scc_data.extend(['942c', '942c'])
                
                # Filler - doubled for redundancy
                scc_data.extend(['8080', '8080'])
                
                # EOC (End Of Caption) - doubled for redundancy
                scc_data.extend(['942f', '942f'])
                
                # Write the caption start timecode and data
                f.write(f"{start_timecode}\t{' '.join(scc_data)}\n\n")
                
                # Write the caption end timecode with clear command
                f.write(f"{end_timecode}\t942c 942c\n\n")
        
        logger.info(f"Successfully wrote SCC file: {output_path}")
        
        # Verify the file was written correctly
        verify_file_operation(output_path, output_path, "write")
    except IOError as e:
        logger.error(f"Failed to write SCC file {output_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error writing SCC file {output_path}: {e}")
        raise

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
            if dest_path.endswith('.scc'):
                with open(source_path, 'r', encoding='utf-8') as f1, open(dest_path, 'r', encoding='utf-8') as f2:
                    source_content = f1.read()
                    dest_content = f2.read()
                    if source_content != dest_content:
                        raise IOError(f"Content mismatch after {operation}")
                        
        logger.debug(f"Successfully verified {operation} operation: {dest_path}")
    except Exception as e:
        logger.error(f"File operation verification failed: {e}")
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
    - SCC (Scenarist Closed Caption) file generation with proper formatting
    
    Args:
        video_path (str): Absolute path to the video file to transcribe
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - success (bool): Whether transcription succeeded
            - scc_path (str): Path to generated SCC file (if successful)
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
            scc_name = f"{os.path.splitext(video_name)[0]}.scc"
            logger.debug(f"Video directory: {video_dir}")
            logger.debug(f"Video name: {video_name}")
            logger.debug(f"SCC name: {scc_name}")
        except Exception as e:
            logger.error(f"Error processing file paths: {e}")
            raise

        # Set up output paths
        local_scc_path = os.path.join(video_dir, scc_name)
        central_scc_path = os.path.join(OUTPUT_DIR, scc_name)
        logger.debug(f"Local SCC path: {local_scc_path}")
        logger.debug(f"Central SCC path: {central_scc_path}")

        # Ensure directories exist with correct permissions
        try:
            ensure_directory_exists(local_scc_path)
            ensure_directory_exists(central_scc_path)
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

        # Convert segments to list and format for SCC
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

        # Save SCC file next to the video
        try:
            logger.info(f"Saving SCC file: {local_scc_path}")
            save_scc_file(formatted_segments, local_scc_path)
            if current_job:
                update_job_progress(current_job, 90, "Local SCC file saved, copying to central location...")
        except Exception as e:
            if current_job:
                update_job_progress(current_job, 0, "Failed to save SCC file", str(e))
            raise
        
        # Copy to central location
        try:
            logger.info(f"Copying SCC file to central location: {central_scc_path}")
            shutil.copy2(local_scc_path, central_scc_path)
            verify_file_operation(local_scc_path, central_scc_path, "copy")
            if current_job:
                update_job_progress(current_job, 100, f"Completed! Generated transcript with {len(formatted_segments)} segments")
        except Exception as e:
            if current_job:
                update_job_progress(current_job, 0, "Failed to copy to central location", str(e))
            raise

        # Set correct permissions on both files
        try:
            if '/mnt/flex-' in local_scc_path:
                import grp
                transcription_gid = grp.getgrnam('transcription_users').gr_gid
                os.chmod(local_scc_path, 0o664)
                os.chown(local_scc_path, -1, transcription_gid)
                logger.debug(f"Set permissions on {local_scc_path}")
        except (grp.KeyError, PermissionError) as e:
            logger.warning(f"Could not set permissions on {local_scc_path}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error setting permissions: {e}")

        logger.info("Transcription process completed successfully")
        
        # Save transcription result to database
        try:
            from core.models import TranscriptionResultORM
            from core.app import db
            import uuid
            
            result = TranscriptionResultORM(
                id=str(uuid.uuid4()),
                video_path=video_path,
                output_path=central_scc_path,
                status='completed',
                completed_at=datetime.utcnow()
            )
            db.session.add(result)
            db.session.commit()
            logger.info(f"Saved transcription result to database with ID: {result.id}")
        except Exception as e:
            logger.error(f"Failed to save transcription result to database: {e}")
            # Don't raise the error since the transcription itself was successful
        
        # Log debug information at end
        if DEBUG_MODE:
            log_debug_info('end', {
                'success': True,
                'scc_path': local_scc_path,
                'central_scc_path': central_scc_path,
                'segments': len(formatted_segments),
                'duration': formatted_segments[-1]["end"] if formatted_segments else 0
            })
            
        # Auto-link to Cablecast show if enabled
        if os.getenv('AUTO_LINK_TO_CABLECAST', 'false').lower() == 'true':
            try:
                from core.task_queue import queue_manager
                from core.vod_automation import auto_link_transcription_to_show
                queue_manager.enqueue_task(auto_link_transcription_to_show, result.id)
                logger.info(f"Queued auto-link to Cablecast show for transcription {result.id}")
            except Exception as e:
                logger.error(f"Failed to queue auto-link to Cablecast show: {e}")
        
        return {
            'scc_path': local_scc_path,
            'central_scc_path': central_scc_path,
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