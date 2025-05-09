import subprocess
import os
from loguru import logger
from typing import Tuple
import time
import re
import traceback
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

def run_whisperx(video_path: str):
    """Run WhisperX transcription on a video file"""
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

        # Build WhisperX command with compatibility flags
        cmd = f"whisperx {video_path} --model {WHISPER_MODEL} --output_dir {output_path} " \
              f"--output_format srt --compute_type {COMPUTE_TYPE} --batch_size {BATCH_SIZE} " \
              f"--language {LANGUAGE} --device cpu --threads {NUM_WORKERS} " \
              f"--model_dir {OUTPUT_DIR}/models --no_speaker_diarization"
        
        logger.info(f"Using command: {cmd}")
        
        # Start the process
        try:
            process = subprocess.Popen(
                cmd.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
        except subprocess.SubprocessError as e:
            raise RuntimeError(f"Failed to start WhisperX process: {str(e)}")
        
        # Track progress
        transcript_lines = 0
        total_duration = 0
        current_time = 0
        last_activity = time.time()
        
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
                
            if line:
                last_activity = time.time()
                
            # Check for process timeout (no activity for 5 minutes)
            if time.time() - last_activity > 300:
                process.terminate()
                raise TimeoutError("No transcription progress for 5 minutes")
                
            if current_job and not current_job.meta.get('paused', False):
                if "Detecting speakers" in line:
                    current_job.meta['status_message'] = 'Detecting speakers in audio...'
                    current_job.save_meta()
                elif "Error:" in line or "ERROR:" in line:
                    error_msg = line.strip()
                    current_job.meta.update({
                        'error_details': error_msg,
                        'status_message': f'Error encountered: {error_msg}'
                    })
                    current_job.save_meta()
                elif "Transcript:" in line:
                    # Extract timestamp from transcript line
                    match = re.search(r'\[(\d+\.\d+)\s*-->\s*(\d+\.\d+)\]', line)
                    if match:
                        start_time, end_time = float(match.group(1)), float(match.group(2))
                        if end_time > total_duration:
                            total_duration = end_time
                        current_time = end_time
                        
                        # Update progress
                        if total_duration > 0:
                            progress = min(95, (current_time / total_duration) * 100)
                            transcript_lines += 1
                            
                            # Calculate time remaining
                            elapsed_time = time.time() - current_job.meta.get('start_time', time.time())
                            if progress > 0:
                                total_estimated_time = (elapsed_time / progress) * 100
                                time_remaining = max(0, total_estimated_time - elapsed_time)
                                
                                # Format time remaining
                                if time_remaining > 3600:
                                    time_str = f"{time_remaining/3600:.1f} hours"
                                elif time_remaining > 60:
                                    time_str = f"{time_remaining/60:.0f} minutes"
                                else:
                                    time_str = f"{time_remaining:.0f} seconds"
                                
                                current_job.meta.update({
                                    'progress': progress,
                                    'status_message': f'Transcribed {transcript_lines} segments ({current_time:.1f} sec / {total_duration:.1f} sec) - {time_str} remaining',
                                    'time_remaining': time_remaining,
                                    'transcribed_duration': current_time,
                                    'total_duration': total_duration
                                })
                                current_job.save_meta()
                elif ">>Performing transcription" in line:
                    current_job.meta['status_message'] = 'Processing audio...'
                    current_job.save_meta()
            
            logger.info(line.strip())
            
        # Process complete
        if current_job:
            current_job.meta.update({
                'progress': 100,
                'status_message': f'Completed! Generated transcript with {transcript_lines} segments',
                'time_remaining': 0
            })
            current_job.save_meta()
            
        return {
            'srt_path': f"{video_path}.srt",
            'segments': transcript_lines,
            'duration': total_duration
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