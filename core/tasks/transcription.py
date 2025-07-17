"""Celery transcription tasks for Archivist application.

This module provides Celery tasks for transcription operations, migrating
from the RQ system to a unified Celery-based architecture.

Key Features:
- WhisperX transcription via Celery
- Progress tracking and status updates
- Error handling and retry mechanisms
- Integration with VOD processing pipeline
"""

from celery import current_task
from loguru import logger
from typing import Dict, Optional
import os
import time

from core.tasks import celery_app
from core.services.transcription import TranscriptionService


@celery_app.task(name="transcription.run_whisper", bind=True)
def run_whisper_transcription(self, video_path: str) -> Dict:
    """
    Transcribe a video file using WhisperX via Celery.
    
    This task replaces the RQ transcription job with a Celery-based implementation
    that provides better progress tracking, error handling, and integration with
    the VOD processing pipeline.
    
    Args:
        video_path: Path to the video file to transcribe
        
    Returns:
        Dictionary containing transcription results:
        {
            'output_path': str,      # Path to generated SCC file
            'status': str,           # 'completed', 'failed', etc.
            'segments': int,         # Number of transcription segments
            'duration': float,       # Video duration in seconds
            'error': str,            # Error message if failed
            'task_id': str           # Celery task ID
        }
        
    Raises:
        Exception: If transcription fails
    """
    task_id = self.request.id
    logger.info(f"Starting Celery transcription task {task_id} for {video_path}")
    
    try:
        # Validate input file
        if not os.path.exists(video_path):
            error_msg = f"Video file not found: {video_path}"
            logger.error(f"Task {task_id}: {error_msg}")
            self.update_state(
                state='FAILURE',
                meta={'error': error_msg, 'video_path': video_path}
            )
            raise FileNotFoundError(error_msg)
        
        # Update task state to processing
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 0,
                'status_message': 'Initializing transcription...',
                'video_path': video_path
            }
        )
        
        # Initialize transcription service
        transcription_service = TranscriptionService()
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 10,
                'status_message': 'Loading WhisperX model...',
                'video_path': video_path
            }
        )
        
        # Perform transcription
        logger.info(f"Task {task_id}: Starting transcription of {video_path}")
        result = transcription_service.transcribe_file(video_path)
        
        # Update progress to completion
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 90,
                'status_message': 'Finalizing transcription...',
                'video_path': video_path
            }
        )
        
        # Prepare final result
        final_result = {
            'output_path': result.get('output_path', ''),
            'status': 'completed',
            'segments': result.get('segments', 0),
            'duration': result.get('duration', 0),
            'video_path': video_path,
            'task_id': task_id,
            'progress': 100,
            'status_message': 'Transcription completed successfully'
        }
        
        logger.info(f"Task {task_id}: Transcription completed successfully")
        logger.info(f"Task {task_id}: Output saved to {final_result['output_path']}")
        
        return final_result
        
    except Exception as e:
        error_msg = f"Transcription failed for {video_path}: {str(e)}"
        logger.error(f"Task {task_id}: {error_msg}")
        
        # Update task state to failure
        self.update_state(
            state='FAILURE',
            meta={
                'error': error_msg,
                'video_path': video_path,
                'task_id': task_id,
                'status': 'failed'
            }
        )
        
        # Re-raise the exception for Celery to handle
        raise


@celery_app.task(name="transcription.batch_process")
def batch_transcription(video_paths: list, priority: Optional[int] = None) -> Dict:
    """
    Process multiple video files for transcription.
    
    This task allows for batch processing of multiple videos, which is useful
    for VOD processing pipelines that need to transcribe multiple files.
    
    Args:
        video_paths: List of video file paths to transcribe
        priority: Optional priority level for the batch
        
    Returns:
        Dictionary containing batch processing results
    """
    logger.info(f"Starting batch transcription for {len(video_paths)} videos")
    
    results = {
        'total_videos': len(video_paths),
        'completed': 0,
        'failed': 0,
        'results': [],
        'errors': []
    }
    
    # Process videos sequentially to avoid overwhelming the system
    for i, video_path in enumerate(video_paths):
        try:
            logger.info(f"Processing video {i+1}/{len(video_paths)}: {video_path}")
            
            # Submit individual transcription task
            task = run_whisper_transcription.delay(video_path)
            
            # Wait for completion (with timeout)
            result = task.get(timeout=3600)  # 1 hour timeout
            
            results['results'].append({
                'video_path': video_path,
                'task_id': task.id,
                'status': 'completed',
                'result': result
            })
            results['completed'] += 1
            
            logger.info(f"Completed transcription for {video_path}")
            
        except Exception as e:
            error_msg = f"Failed to transcribe {video_path}: {str(e)}"
            logger.error(error_msg)
            
            results['errors'].append({
                'video_path': video_path,
                'error': error_msg
            })
            results['failed'] += 1
    
    logger.info(f"Batch transcription completed: {results['completed']} successful, {results['failed']} failed")
    return results


@celery_app.task(name="transcription.cleanup_temp_files")
def cleanup_transcription_temp_files(temp_dir: Optional[str] = None) -> Dict:
    """
    Clean up temporary files from transcription processes.
    
    Args:
        temp_dir: Optional directory to clean (defaults to system temp)
        
    Returns:
        Dictionary with cleanup results
    """
    import tempfile
    import shutil
    from datetime import datetime, timedelta
    
    if temp_dir is None:
        temp_dir = tempfile.gettempdir()
    
    logger.info(f"Cleaning up temporary transcription files in {temp_dir}")
    
    results = {
        'directory': temp_dir,
        'files_removed': 0,
        'bytes_freed': 0,
        'errors': []
    }
    
    try:
        # Find temporary files older than 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                # Look for transcription-related temp files
                if any(pattern in file.lower() for pattern in ['whisper', 'transcription', 'audio', 'temp']):
                    file_path = os.path.join(root, file)
                    
                    try:
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_time < cutoff_time:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            
                            results['files_removed'] += 1
                            results['bytes_freed'] += file_size
                            
                            logger.debug(f"Removed temp file: {file_path}")
                            
                    except Exception as e:
                        error_msg = f"Failed to remove {file_path}: {str(e)}"
                        results['errors'].append(error_msg)
                        logger.warning(error_msg)
        
        logger.info(f"Cleanup completed: {results['files_removed']} files removed, {results['bytes_freed']} bytes freed")
        return results
        
    except Exception as e:
        error_msg = f"Cleanup failed: {str(e)}"
        logger.error(error_msg)
        results['errors'].append(error_msg)
        return results


# Helper function for backward compatibility
def enqueue_transcription(video_path: str, position: Optional[int] = None) -> str:
    """
    Enqueue a transcription job (backward compatibility with RQ system).
    
    This function provides a drop-in replacement for the RQ enqueue_transcription
    function, allowing for seamless migration from RQ to Celery.
    
    Args:
        video_path: Path to the video file
        position: Ignored (Celery doesn't support position-based queuing)
        
    Returns:
        Celery task ID
    """
    logger.info(f"Enqueueing transcription for {video_path} via Celery")
    
    # Submit Celery task
    task = run_whisper_transcription.delay(video_path)
    
    logger.info(f"Transcription task submitted: {task.id}")
    return task.id


# Export for backward compatibility
__all__ = [
    'run_whisper_transcription',
    'batch_transcription', 
    'cleanup_transcription_temp_files',
    'enqueue_transcription'
] 