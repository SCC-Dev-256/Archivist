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
from typing import Dict, List, Optional

from celery.result import AsyncResult
from core.exceptions import QueueError
from core.tasks import celery_app
from core.tasks.transcription import run_whisper_transcription
from loguru import logger


class QueueService:
    """Service for handling queue operations."""

    def __init__(self):
        """Initialise the queue service with Celery."""
        self.queue_manager = celery_app

    def enqueue_transcription(
        self, video_path: str, position: Optional[int] = None
    ) -> str:
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

            # Submit Celery task directly
            task = run_whisper_transcription.delay(video_path)
            job_id = task.id
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
            result = AsyncResult(job_id, app=self.queue_manager)
            info = result.info if isinstance(result.info, dict) else {}

            status = info.get("status", result.status.lower())
            response = {
                'id': job_id,
                'status': status,
                'progress': info.get('progress', 0),
                'status_message': info.get('status_message', ''),
                'video_path': info.get('video_path', ''),
                'created_at': info.get('created_at'),
                'started_at': info.get('started_at'),
                'ended_at': info.get('ended_at')
            }

            if result.failed():
                response['error'] = str(result.info)
            elif result.successful() and isinstance(result.result, dict):
                response.update(result.result)

            logger.debug(f"Retrieved status for job {job_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            raise QueueError(f"Status retrieval failed: {str(e)}")

    def get_queue_status(self) -> Dict:
        """Get current queue status.
        
        Returns:
            Dictionary with queue status information
        """
        try:
            # Simple queue status without signal-based timeout
            inspect = self.queue_manager.control.inspect()
            stats = inspect.stats()
            ping = inspect.ping()
            
            active_workers = len(ping) if ping else 0
            total_workers = len(stats) if stats else 0
            
            return {
                'active_workers': active_workers,
                'total_workers': total_workers,
                'worker_status': 'healthy' if active_workers > 0 else 'unhealthy',
                'queue_length': 0,  # Will be calculated from get_all_jobs
                'completed_jobs': 0,
                'status': 'operational'
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            raise QueueError(f"Queue status retrieval failed: {str(e)}")
    
    def get_all_jobs(self) -> List[Dict]:
        """Get all jobs in the queue.
        
        Returns:
            List of job dictionaries
        """
        try:
            # Simple job retrieval without signal-based timeout
            inspect = self.queue_manager.control.inspect()
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            scheduled = inspect.scheduled() or {}
            
            jobs = []
            
            # Process active jobs
            for worker_name, worker_tasks in active.items():
                for task in worker_tasks:
                    jobs.append({
                        'id': task['id'],
                        'name': task['name'],
                        'status': 'processing',
                        'progress': 0,  # Celery doesn't provide progress by default
                        'status_message': 'Processing...',
                        'video_path': task.get('args', [''])[0] if task.get('args') else '',
                        'worker': worker_name,
                        'created_at': task.get('time_start'),
                        'started_at': task.get('time_start')
                    })
            
            # Process reserved jobs
            for worker_name, worker_tasks in reserved.items():
                for task in worker_tasks:
                    jobs.append({
                        'id': task['id'],
                        'name': task['name'],
                        'status': 'queued',
                        'progress': 0,
                        'status_message': 'Waiting to start...',
                        'video_path': task.get('args', [''])[0] if task.get('args') else '',
                        'worker': worker_name,
                        'created_at': task.get('time_start')
                    })
            
            # Process scheduled jobs
            for worker_name, worker_tasks in scheduled.items():
                for task in worker_tasks:
                    jobs.append({
                        'id': task['id'],
                        'name': task['name'],
                        'status': 'scheduled',
                        'progress': 0,
                        'status_message': 'Scheduled for later...',
                        'video_path': task.get('args', [''])[0] if task.get('args') else '',
                        'worker': worker_name,
                        'created_at': task.get('eta')
                    })
            
            # Get additional status info for each job (without timeouts)
            for job in jobs:
                try:
                    result = AsyncResult(job['id'], app=self.queue_manager)
                    if result.info and isinstance(result.info, dict):
                        job['progress'] = result.info.get('progress', job['progress'])
                        job['status_message'] = result.info.get('status_message', job['status_message'])
                        job['video_path'] = result.info.get('video_path', job['video_path'])
                except Exception as e:
                    logger.debug(f"Could not get additional info for job {job['id']}: {e}")
            
            logger.info(f"Retrieved {len(jobs)} jobs from queue")
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to get all jobs: {e}")
            return []
    
    def reorder_job(self, job_id: str, new_position: int) -> bool:
        """Reorder a job in the queue.

        Args:
            job_id: ID of the job to reorder
            new_position: New position in the queue

        Returns:
            True if reorder was successful
        """
        logger.warning("Celery does not support reordering tasks")
        return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a job.

        Args:
            job_id: ID of the job to pause

        Returns:
            True if pause was successful
        """
        logger.warning("Celery does not support pausing tasks")
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job.

        Args:
            job_id: ID of the job to resume

        Returns:
            True if resume was successful
        """
        logger.warning("Celery does not support resuming tasks")
        return False

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job.

        Args:
            job_id: ID of the job to cancel

        Returns:
            True if cancel was successful
        """
        try:
            self.queue_manager.control.revoke(job_id, terminate=True)
            logger.info(f"Cancelled job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            raise QueueError(f"Job cancellation failed: {str(e)}")

    def get_failed_jobs(self) -> List[Dict]:
        """Get list of failed jobs.

        Returns:
            List of failed job dictionaries
        """
        logger.warning("Retrieving failed jobs is not supported with Celery")
        return []

    def get_job_progress(self, job_id: str) -> Dict:
        """Get the progress of a job.

        Args:
            job_id: ID of the job

        Returns:
            Dictionary containing job progress
        """
        try:
            result = AsyncResult(job_id, app=self.queue_manager)
            info = result.info if isinstance(result.info, dict) else {}

            progress = {
                "progress": info.get("progress", 0),
                "status_message": info.get("status_message", ""),
                "status": info.get("status", result.status.lower()),
            }

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
            inspect = self.queue_manager.control.inspect(timeout=5)
            stats = inspect.stats() or {}
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
            self.queue_manager.control.purge()
            logger.info("Cleared all jobs from queue")
            return True

        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            raise QueueError(f"Queue clear failed: {str(e)}")

    def get_worker_status(self) -> Dict:
        """Get the status of queue workers.

        Returns:
            Dictionary containing worker status
        """
        try:
            inspect = self.queue_manager.control.inspect(timeout=5)
            stats = inspect.stats() or {}
            ping = inspect.ping() or {}
            worker_status = {
                worker: {"online": worker in ping, "stats": data}
                for worker, data in stats.items()
            }
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
        logger.warning("Restarting workers is not supported via QueueService")
        return False
