"""Queue service for Archivist application.

This service provides a clean interface for all queue-related operations,
including job management, status tracking, and queue monitoring.

Key Features:
- Job queue management
- Status tracking
- Job prioritization
- Failed job cleanup
- Queue monitoring

Example:
    >>> from core.services import QueueService
    >>> service = QueueService()
    >>> job_id = service.enqueue_transcription("video.mp4")
"""

import os
from typing import Dict, Optional, List
from loguru import logger
from core.exceptions import QueueError
from core.task_queue import queue_manager

class QueueService:
    """Service for handling queue operations."""
    
    def __init__(self):
        self.queue_manager = queue_manager
    
    def enqueue_transcription(self, video_path: str, position: Optional[int] = None) -> str:
        """Enqueue a transcription job.
        
        Args:
            video_path: Path to the video file
            position: Optional position in queue (None for end)
            
        Returns:
            Job ID
        """
        try:
            if not os.path.exists(video_path):
                raise QueueError(f"Video file not found: {video_path}")
            
            job_id = self.queue_manager.enqueue_transcription(video_path, position)
            logger.info(f"Enqueued transcription job {job_id} for {video_path}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue transcription for {video_path}: {e}")
            raise QueueError(f"Job enqueue failed: {str(e)}")
    
    def get_job_status(self, job_id: str) -> Dict:
        """Get the status of a job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            Dictionary containing job status
        """
        try:
            status = self.queue_manager.get_job_status(job_id)
            logger.debug(f"Retrieved status for job {job_id}")
            return status
            
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            raise QueueError(f"Status retrieval failed: {str(e)}")
    
    def get_queue_status(self) -> Dict:
        """Get the overall status of the queue.
        
        Returns:
            Dictionary containing queue status
        """
        try:
            # Get all jobs and calculate status
            all_jobs = self.queue_manager.get_all_jobs()
            
            total_jobs = len(all_jobs)
            running_jobs = sum(1 for job in all_jobs if job.get('status') == 'running')
            queued_jobs = sum(1 for job in all_jobs if job.get('status') == 'queued')
            failed_jobs = sum(1 for job in all_jobs if job.get('status') == 'failed')
            completed_jobs = sum(1 for job in all_jobs if job.get('status') == 'completed')
            
            status = {
                'total_jobs': total_jobs,
                'running_jobs': running_jobs,
                'queued_jobs': queued_jobs,
                'failed_jobs': failed_jobs,
                'completed_jobs': completed_jobs
            }
            
            logger.info(f"Retrieved queue status: {total_jobs} total jobs")
            return status
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            raise QueueError(f"Queue status retrieval failed: {str(e)}")
    
    def reorder_job(self, job_id: str, new_position: int) -> bool:
        """Reorder a job in the queue.
        
        Args:
            job_id: ID of the job to reorder
            new_position: New position in the queue
            
        Returns:
            True if reorder was successful
        """
        try:
            success = self.queue_manager.reorder_job(job_id, new_position)
            if success:
                logger.info(f"Reordered job {job_id} to position {new_position}")
            else:
                logger.warning(f"Failed to reorder job {job_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to reorder job {job_id}: {e}")
            raise QueueError(f"Job reorder failed: {str(e)}")
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a job.
        
        Args:
            job_id: ID of the job to pause
            
        Returns:
            True if pause was successful
        """
        try:
            success = self.queue_manager.pause_job(job_id)
            if success:
                logger.info(f"Paused job {job_id}")
            else:
                logger.warning(f"Failed to pause job {job_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")
            raise QueueError(f"Job pause failed: {str(e)}")
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job.
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            True if resume was successful
        """
        try:
            success = self.queue_manager.resume_job(job_id)
            if success:
                logger.info(f"Resumed job {job_id}")
            else:
                logger.warning(f"Failed to resume job {job_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
            raise QueueError(f"Job resume failed: {str(e)}")
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job.
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            True if cancel was successful
        """
        try:
            success = self.queue_manager.cancel_job(job_id)
            if success:
                logger.info(f"Cancelled job {job_id}")
            else:
                logger.warning(f"Failed to cancel job {job_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            raise QueueError(f"Job cancellation failed: {str(e)}")
    
    def get_failed_jobs(self) -> List[Dict]:
        """Get list of failed jobs.
        
        Returns:
            List of failed job dictionaries
        """
        try:
            failed_jobs = self.queue_manager.get_failed_jobs()
            logger.info(f"Retrieved {len(failed_jobs)} failed jobs")
            return failed_jobs
            
        except Exception as e:
            logger.error(f"Failed to get failed jobs: {e}")
            raise QueueError(f"Failed jobs retrieval failed: {str(e)}")
    
    def get_job_progress(self, job_id: str) -> Dict:
        """Get the progress of a job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            Dictionary containing job progress
        """
        try:
            progress = self.queue_manager.get_job_progress(job_id)
            logger.debug(f"Retrieved progress for job {job_id}")
            return progress
            
        except Exception as e:
            logger.error(f"Failed to get job progress for {job_id}: {e}")
            raise QueueError(f"Progress retrieval failed: {str(e)}")
    
    def get_queue_statistics(self) -> Dict:
        """Get queue statistics.
        
        Returns:
            Dictionary containing queue statistics
        """
        try:
            stats = self.queue_manager.get_queue_statistics()
            logger.info("Retrieved queue statistics")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue statistics: {e}")
            raise QueueError(f"Statistics retrieval failed: {str(e)}")
    
    def clear_queue(self) -> bool:
        """Clear all jobs from the queue.
        
        Returns:
            True if queue was cleared successfully
        """
        try:
            success = self.queue_manager.clear_queue()
            if success:
                logger.info("Cleared all jobs from queue")
            else:
                logger.warning("Failed to clear queue")
            return success
            
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            raise QueueError(f"Queue clear failed: {str(e)}")
    
    def get_worker_status(self) -> Dict:
        """Get the status of queue workers.
        
        Returns:
            Dictionary containing worker status
        """
        try:
            worker_status = self.queue_manager.get_worker_status()
            logger.info("Retrieved worker status")
            return worker_status
            
        except Exception as e:
            logger.error(f"Failed to get worker status: {e}")
            raise QueueError(f"Worker status retrieval failed: {str(e)}")
    
    def restart_workers(self) -> bool:
        """Restart queue workers.
        
        Returns:
            True if workers were restarted successfully
        """
        try:
            success = self.queue_manager.restart_workers()
            if success:
                logger.info("Restarted queue workers")
            else:
                logger.warning("Failed to restart workers")
            return success
            
        except Exception as e:
            logger.error(f"Failed to restart workers: {e}")
            raise QueueError(f"Worker restart failed: {str(e)}") 