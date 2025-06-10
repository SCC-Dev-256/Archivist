"""Task queue management module for the Archivist application.

This module provides a robust task queue system for handling asynchronous
operations like transcription and video processing. It supports job prioritization,
status tracking, and automatic cleanup of failed jobs.

Key Features:
- Asynchronous job processing
- Job prioritization and reordering
- Status tracking and monitoring
- Failed job cleanup
- Job pause/resume functionality
- Progress tracking

Example:
    >>> from core.task_queue import QueueManager
    >>> queue = QueueManager()
    >>> job_id = queue.enqueue_transcription('video.mp4')
    >>> status = queue.get_job_status(job_id)
    >>> print(status['progress'])
"""

from loguru import logger
from typing import List, Dict, Optional
import time
import redis
from rq import Queue, Worker
import sys

# Initialize queue instance
_queue_instance = None

def get_queue():
    """Get or create the queue instance."""
    global _queue_instance
    if _queue_instance is None:
        from core.config import REDIS_URL
        try:
            logger.info(f"Initializing Redis connection to {REDIS_URL}")
            # Configure Redis connection with retry and timeout settings
            redis_conn = redis.from_url(
                REDIS_URL,
                socket_timeout=30,  # Increase timeout
                socket_connect_timeout=30,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test the connection with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    redis_conn.ping()
                    logger.info("Successfully connected to Redis")
                    break
                except redis.ConnectionError as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                    time.sleep(1)
            
            # Initialize queue with default timeout and result_ttl
            _queue_instance = Queue('transcription', 
                        connection=redis_conn,
                        default_timeout=3600,  # 1 hour timeout
                        result_ttl=86400)      # Keep results for 24 hours
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing queue: {e}")
            raise
    return _queue_instance

class QueueManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QueueManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self._queue = get_queue()
    
    @property
    def queue(self):
        return self._queue

    def get_all_jobs(self) -> List[Dict]:
        """Get all jobs in the queue with their metadata"""
        try:
            jobs = []
            for job in self.queue.jobs:
                if job.is_finished:
                    status = 'finished'
                elif job.is_failed:
                    status = 'failed'
                elif job.is_started:
                    status = 'started'
                else:
                    status = 'queued'
                
                jobs.append({
                    'id': job.id,
                    'status': status,
                    'position': job.meta.get('position', 0),
                    'progress': job.meta.get('progress', 0),
                    'status_message': job.meta.get('status_message', ''),
                    'error_details': job.meta.get('error_details'),
                    'created_at': job.created_at,
                    'started_at': job.started_at,
                    'ended_at': job.ended_at,
                    'video_path': job.meta.get('video_path', '')  # Add video_path to returned data
                })
            return sorted(jobs, key=lambda x: x['position'])
        except Exception as e:
            logger.error(f"Error getting jobs: {e}")
            return []

    def enqueue_transcription(self, video_path: str, position: Optional[int] = None) -> str:
        """Enqueue a transcription job with optional position."""
        try:
            # Get current max position if none specified
            if position is None:
                current_jobs = self.get_all_jobs()
                position = max([job['position'] for job in current_jobs], default=0) + 1
            
            # Calculate priority (lower number = higher priority)
            # Use position as priority, but invert it so lower position = higher priority
            priority = 100 - position  # This ensures position 0 has highest priority
            
            job = self.queue.enqueue(
                'core.transcription.run_whisperx',
                video_path,
                job_timeout='1h',
                meta={
                    'position': position,
                    'status': 'queued',
                    'progress': 0,
                    'status_message': 'Waiting to start...',
                    'video_path': video_path  # Add video_path to metadata
                }
            )
            
            logger.info(f"Enqueued job {job.id} with priority {priority} (position {position})")
            return job.id
        except Exception as e:
            logger.error(f"Error enqueueing transcription job: {e}")
            raise

    def reorder_job(self, job_id: str, position: int) -> bool:
        """Change the position of a job in the queue."""
        try:
            job = self.queue.fetch_job(job_id)
            if not job:
                return False
                
            # Update position in job metadata
            job.meta['position'] = position
            job.save_meta()
            
            # Reorder other jobs if needed
            all_jobs = self.get_all_jobs()
            for other_job in all_jobs:
                if other_job['id'] != job_id:
                    other_job_obj = self.queue.fetch_job(other_job['id'])
                    if other_job_obj:
                        if other_job['position'] >= position:
                            other_job_obj.meta['position'] = other_job['position'] + 1
                            other_job_obj.save_meta()
            
            return True
        except Exception as e:
            logger.error(f"Error reordering job: {e}")
            return False

    def stop_job(self, job_id: str) -> bool:
        """Stop a running job."""
        try:
            job = self.queue.fetch_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return False
            
            current_status = job.get_status()
            logger.info(f"Stopping job {job_id} with status {current_status}")
            
            if current_status == 'queued':
                # For queued jobs, remove from queue
                self.queue.remove(job)
                job.meta['status'] = 'cancelled'
                job.meta['status_message'] = 'Job cancelled by user'
                job.save_meta()
                logger.info(f"Removed queued job {job_id}")
                return True
                
            elif current_status == 'started':
                # For running jobs, cancel and delete
                job.cancel()
                job.meta['status'] = 'cancelled'
                job.meta['status_message'] = 'Job cancelled by user'
                job.save_meta()
                job.delete()
                logger.info(f"Cancelled running job {job_id}")
                return True
            
            logger.warning(f"Job {job_id} cannot be cancelled in status {current_status}")
            return False
        except Exception as e:
            logger.error(f"Error stopping job {job_id}: {e}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a running job."""
        try:
            job = self.queue.fetch_job(job_id)
            if not job:
                return False
            
            # Store pause state in job metadata
            if job.get_status() == 'started':
                job.meta['paused'] = True
                job.save_meta()
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error pausing job: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        try:
            job = self.queue.fetch_job(job_id)
            if not job:
                return False
            
            # Remove pause state from job metadata
            if job.meta.get('paused', False):
                job.meta['paused'] = False
                job.save_meta()
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error resuming job: {e}")
            return False

    def _get_job_status(self, job) -> str:
        """Get detailed status of a job."""
        if job.is_failed:
            return 'failed'
        if job.is_finished:
            return 'completed'
        if job.is_started:
            return 'paused' if job.meta.get('paused', False) else 'processing'
        if job.meta.get('status') == 'cancelled':
            return 'cancelled'
        return 'queued'

    def get_job_status(self, job_id: str) -> dict:
        """Get the status of a job by its ID."""
        try:
            job = self.queue.fetch_job(job_id)
            if job is None:
                return {"status": "unknown", "error": "Job not found"}
            
            status = self._get_job_status(job)
            
            response = {
                "status": status,
                "progress": job.meta.get('progress', 0),
                "status_message": job.meta.get('status_message', ''),
                "position": job.meta.get('position', 0)
            }
            
            if status == 'failed':
                response["error"] = str(job.exc_info)
            elif status == 'completed' and job.result:
                response.update(job.result)
                
            return response
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {"status": "error", "error": str(e)}

    def get_current_job(self):
        """Get the currently running job."""
        try:
            # Get the first started job
            started_jobs = self.queue.started_job_registry.get_job_ids()
            if started_jobs:
                return self.queue.fetch_job(started_jobs[0])
            return None
        except Exception as e:
            logger.error(f"Error getting current job: {e}")
            return None

    def remove_job(self, job_id: str) -> bool:
        """Remove a job from the queue, regardless of status."""
        try:
            job = self.queue.fetch_job(job_id)
            if not job:
                return False
            job.delete()
            return True
        except Exception as e:
            logger.error(f"Error removing job: {e}")
            return False

    def cleanup_failed_jobs(self):
        """Clean up failed jobs older than 24 hours"""
        try:
            registry = self.queue.failed_job_registry
            for job_id in registry.get_job_ids():
                job = self.queue.fetch_job(job_id)
                if job and job.ended_at:
                    if time.time() - job.ended_at.timestamp() > 86400:  # 24 hours
                        registry.remove(job_id)
                        logger.info(f"Cleaned up failed job {job_id}")
        except Exception as e:
            logger.error(f"Error cleaning up failed jobs: {e}")

# Create singleton instance
queue_manager = QueueManager()

# Module-level functions that use the singleton instance
def enqueue_transcription(video_path: str, position: Optional[int] = None) -> str:
    """Enqueue a transcription job with optional position."""
    return queue_manager.enqueue_transcription(video_path, position)

def get_job_status(job_id: str) -> dict:
    """Get the status of a job."""
    return queue_manager.get_job_status(job_id)

def get_all_jobs() -> List[Dict]:
    """Get all jobs in the queue with their metadata."""
    return queue_manager.get_all_jobs()

def reorder_job(job_id: str, position: int) -> bool:
    """Change the position of a job in the queue."""
    return queue_manager.reorder_job(job_id, position)

def stop_job(job_id: str) -> bool:
    """Stop a running job."""
    return queue_manager.stop_job(job_id)

def pause_job(job_id: str) -> bool:
    """Pause a running job."""
    return queue_manager.pause_job(job_id)

def resume_job(job_id: str) -> bool:
    """Resume a paused job."""
    return queue_manager.resume_job(job_id)

def remove_job(job_id: str) -> bool:
    """Remove a job from the queue."""
    return queue_manager.remove_job(job_id)

def cleanup_failed_jobs():
    """Clean up failed jobs."""
    return queue_manager.cleanup_failed_jobs()

def get_current_job():
    """Get the currently running job."""
    return queue_manager.get_current_job()

if __name__ == '__main__':
    try:
        # Start RQ worker with error handling
        worker = Worker([queue_manager.queue], connection=queue_manager.queue.connection)
        logger.info("Starting worker...")
        worker.work()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1) 