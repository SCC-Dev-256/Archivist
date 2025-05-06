from loguru import logger
from typing import List, Dict, Optional
from core.config import REDIS_HOST, REDIS_PORT, REDIS_DB

class QueueManager:
    _instance = None
    _queue = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QueueManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._queue is None:
            self._queue = self._init_queue()
    
    def _init_queue(self):
        import redis
        from rq import Queue
        redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        return Queue('transcription', connection=redis_conn)
    
    @property
    def queue(self):
        return self._queue

    def get_all_jobs(self) -> List[Dict]:
        """Get all jobs in the queue and their status."""
        jobs = []
        # Get started jobs
        started_job_ids = self.queue.started_job_registry.get_job_ids()
        # Get queued jobs
        queued_job_ids = self.queue.get_job_ids()
        # Get finished jobs
        finished_job_ids = self.queue.finished_job_registry.get_job_ids()
        # Get failed jobs
        failed_job_ids = self.queue.failed_job_registry.get_job_ids()
        
        all_jobs = []
        for job_id in started_job_ids + queued_job_ids + finished_job_ids + failed_job_ids:
            job = self.queue.fetch_job(job_id)
            if job:
                all_jobs.append({
                    'id': job.id,
                    'status': self._get_job_status(job),
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'video_path': job.args[0] if job.args else None,
                    'position': job.meta.get('position', 0),
                    'progress': job.meta.get('progress', 0),
                    'status_message': job.meta.get('status_message', '')
                })
        
        return sorted(all_jobs, key=lambda x: x['position'])

    def enqueue_transcription(self, video_path: str, position: Optional[int] = None) -> str:
        """Enqueue a transcription job with optional position."""
        try:
            # Get current max position if none specified
            if position is None:
                current_jobs = self.get_all_jobs()
                position = max([job['position'] for job in current_jobs], default=0) + 1
            
            job = self.queue.enqueue(
                'core.web_app.process_video_task',
                video_path,
                job_timeout='1h',
                meta={'position': position}
            )
            
            return job.id
        except Exception as e:
            logger.error(f"Error enqueueing transcription job: {e}")
            raise

    def reorder_job(self, job_id: str, new_position: int) -> bool:
        """Change the position of a job in the queue."""
        try:
            job = self.queue.fetch_job(job_id)
            if not job:
                return False
                
            # Update position in job metadata
            job.meta['position'] = new_position
            job.save_meta()
            
            # Reorder other jobs if needed
            all_jobs = self.get_all_jobs()
            for other_job in all_jobs:
                if other_job['id'] != job_id:
                    other_job_obj = self.queue.fetch_job(other_job['id'])
                    if other_job_obj:
                        if other_job['position'] >= new_position:
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
                return False
            
            # Cancel the job if it's still in queue
            if job.get_status() == 'queued':
                self.queue.remove(job)
                return True
                
            # Stop the job if it's running
            if job.get_status() == 'started':
                job.cancel()
                job.delete()
                return True
                
            return False
        except Exception as e:
            logger.error(f"Error stopping job: {e}")
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

# Create global queue manager instance
queue_manager = QueueManager()

if __name__ == '__main__':
    # Start RQ worker
    from rq import Worker
    worker = Worker([queue_manager.queue], connection=queue_manager.queue.connection)
    worker.work() 