"""
Unified Queue Management System

This module provides a unified interface for managing both RQ (Redis Queue) and Celery tasks,
offering a single point of control for all asynchronous job processing in the VOD system.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import time
import threading
from loguru import logger

from core.task_queue import QueueManager
from core.tasks import celery_app

class UnifiedQueueManager:
    """Unified queue manager for RQ and Celery tasks."""
    
    def __init__(self):
        self.rq_manager = QueueManager()
        self._task_cache = {}
        self._cache_lock = threading.Lock()
        
        # Start background cache refresh
        self._start_cache_refresh()
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from both RQ and Celery queues."""
        try:
            tasks = []
            
            # Get RQ jobs
            rq_jobs = self.rq_manager.get_all_jobs()
            for job in rq_jobs:
                tasks.append({
                    'id': job['id'],
                    'queue_type': 'rq',
                    'name': 'Transcription Job',
                    'status': job['status'],
                    'progress': job.get('progress', 0),
                    'created_at': job.get('created_at'),
                    'started_at': job.get('started_at'),
                    'ended_at': job.get('ended_at'),
                    'video_path': job.get('video_path', ''),
                    'worker': 'RQ Worker',
                    'error': job.get('error_details'),
                    'position': job.get('position', 0)
                })
            
            # Get Celery tasks
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active() or {}
            reserved_tasks = inspect.reserved() or {}
            
            # Process active tasks
            for worker, worker_tasks in active_tasks.items():
                for task in worker_tasks:
                    tasks.append({
                        'id': task['id'],
                        'queue_type': 'celery',
                        'name': task['name'],
                        'status': 'active',
                        'progress': 0,  # Celery doesn't provide progress
                        'created_at': task.get('time_start'),
                        'started_at': task.get('time_start'),
                        'ended_at': None,
                        'video_path': '',
                        'worker': worker,
                        'error': None,
                        'position': 0
                    })
            
            # Process reserved tasks
            for worker, worker_tasks in reserved_tasks.items():
                for task in worker_tasks:
                    tasks.append({
                        'id': task['id'],
                        'queue_type': 'celery',
                        'name': task['name'],
                        'status': 'reserved',
                        'progress': 0,
                        'created_at': task.get('time_start'),
                        'started_at': None,
                        'ended_at': None,
                        'video_path': '',
                        'worker': worker,
                        'error': None,
                        'position': 0
                    })
            
            # Sort by creation time (newest first)
            tasks.sort(key=lambda x: x.get('created_at', 0) or 0, reverse=True)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting all tasks: {e}")
            return []
    
    def get_task_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all queues."""
        try:
            tasks = self.get_all_tasks()
            
            # Count by queue type
            rq_tasks = [t for t in tasks if t['queue_type'] == 'rq']
            celery_tasks = [t for t in tasks if t['queue_type'] == 'celery']
            
            # Count by status
            status_counts = {}
            for task in tasks:
                status = task['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Get worker information
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            ping = inspect.ping()
            
            return {
                'total_tasks': len(tasks),
                'rq_tasks': len(rq_tasks),
                'celery_tasks': len(celery_tasks),
                'status_counts': status_counts,
                'workers': {
                    'active_workers': len(ping) if ping else 0,
                    'total_workers': len(stats) if stats else 0,
                    'worker_status': 'healthy' if (ping and len(ping) > 0) else 'unhealthy'
                },
                'queue_health': {
                    'rq_healthy': len([t for t in rq_tasks if t['status'] == 'failed']) == 0,
                    'celery_healthy': len([t for t in celery_tasks if t['status'] == 'failed']) == 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting task summary: {e}")
            return {
                'error': str(e),
                'total_tasks': 0,
                'rq_tasks': 0,
                'celery_tasks': 0,
                'status_counts': {},
                'workers': {'active_workers': 0, 'total_workers': 0, 'worker_status': 'unhealthy'},
                'queue_health': {'rq_healthy': False, 'celery_healthy': False}
            }
    
    def get_task_details(self, task_id: str, queue_type: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific task."""
        try:
            if queue_type == 'rq':
                return self.rq_manager.get_job_status(task_id)
            elif queue_type == 'celery':
                # Get task result from Celery
                result = celery_app.AsyncResult(task_id)
                return {
                    'id': task_id,
                    'queue_type': 'celery',
                    'status': result.status,
                    'result': result.result if result.ready() else None,
                    'error': str(result.info) if result.failed() else None,
                    'created_at': None,  # Celery doesn't provide this easily
                    'started_at': None,
                    'ended_at': None
                }
            else:
                logger.error(f"Unknown queue type: {queue_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting task details for {task_id}: {e}")
            return None
    
    def stop_task(self, task_id: str, queue_type: str) -> bool:
        """Stop a running task."""
        try:
            if queue_type == 'rq':
                return self.rq_manager.stop_job(task_id)
            elif queue_type == 'celery':
                # Revoke Celery task
                celery_app.control.revoke(task_id, terminate=True)
                return True
            else:
                logger.error(f"Unknown queue type: {queue_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping task {task_id}: {e}")
            return False
    
    def pause_task(self, task_id: str, queue_type: str) -> bool:
        """Pause a task (RQ only, Celery doesn't support pausing)."""
        try:
            if queue_type == 'rq':
                return self.rq_manager.pause_job(task_id)
            elif queue_type == 'celery':
                logger.warning("Celery doesn't support pausing tasks")
                return False
            else:
                logger.error(f"Unknown queue type: {queue_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error pausing task {task_id}: {e}")
            return False
    
    def resume_task(self, task_id: str, queue_type: str) -> bool:
        """Resume a paused task (RQ only)."""
        try:
            if queue_type == 'rq':
                return self.rq_manager.resume_job(task_id)
            elif queue_type == 'celery':
                logger.warning("Celery doesn't support resuming tasks")
                return False
            else:
                logger.error(f"Unknown queue type: {queue_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error resuming task {task_id}: {e}")
            return False
    
    def remove_task(self, task_id: str, queue_type: str) -> bool:
        """Remove a task from the queue."""
        try:
            if queue_type == 'rq':
                return self.rq_manager.remove_job(task_id)
            elif queue_type == 'celery':
                # Revoke and purge Celery task
                celery_app.control.revoke(task_id, terminate=True)
                result = celery_app.AsyncResult(task_id)
                result.forget()  # Remove from result backend
                return True
            else:
                logger.error(f"Unknown queue type: {queue_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing task {task_id}: {e}")
            return False
    
    def reorder_task(self, task_id: str, position: int, queue_type: str) -> bool:
        """Reorder a task in the queue (RQ only)."""
        try:
            if queue_type == 'rq':
                return self.rq_manager.reorder_job(task_id, position)
            elif queue_type == 'celery':
                logger.warning("Celery doesn't support reordering tasks")
                return False
            else:
                logger.error(f"Unknown queue type: {queue_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error reordering task {task_id}: {e}")
            return False
    
    def cleanup_failed_tasks(self) -> Dict[str, int]:
        """Clean up failed tasks from both queues."""
        try:
            results = {}
            
            # Clean up RQ failed jobs
            try:
                self.rq_manager.cleanup_failed_jobs()
                results['rq_cleaned'] = 1
            except Exception as e:
                logger.error(f"Error cleaning up RQ failed jobs: {e}")
                results['rq_error'] = 1
            
            # For Celery, we can't easily clean up failed tasks
            # They are typically handled by result backend TTL
            results['celery_note'] = 'Celery failed tasks are handled by result backend TTL'
            
            return results
            
        except Exception as e:
            logger.error(f"Error cleaning up failed tasks: {e}")
            return {'error': str(e)}
    
    def trigger_celery_task(self, task_name: str, **kwargs) -> Dict[str, Any]:
        """Trigger a Celery task."""
        try:
            # Map task names to actual Celery task names
            task_mapping = {
                'process_recent_vods': 'vod_processing.process_recent_vods',
                'cleanup_temp_files': 'vod_processing.cleanup_temp_files',
                'check_captions': 'caption_checks.check_latest_vod_captions',
                'process_single_vod': 'vod_processing.process_single_vod',
                'download_vod_content': 'vod_processing.download_vod_content_task',
                'generate_vod_captions': 'vod_processing.generate_vod_captions',
                'retranscode_vod_with_captions': 'vod_processing.retranscode_vod_with_captions',
                'upload_captioned_vod': 'vod_processing.upload_captioned_vod',
                'validate_vod_quality': 'vod_processing.validate_vod_quality'
            }
            
            actual_task_name = task_mapping.get(task_name, task_name)
            
            # Send task to Celery
            task = celery_app.send_task(actual_task_name, kwargs=kwargs)
            
            return {
                'success': True,
                'task_id': task.id,
                'task_name': task_name,
                'actual_task_name': actual_task_name,
                'message': f'Task {task_name} triggered successfully'
            }
            
        except Exception as e:
            logger.error(f"Error triggering Celery task {task_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'task_name': task_name
            }
    
    def enqueue_transcription(self, video_path: str, position: Optional[int] = None) -> Dict[str, Any]:
        """Enqueue a transcription job (RQ)."""
        try:
            job_id = self.rq_manager.enqueue_transcription(video_path, position)
            return {
                'success': True,
                'job_id': job_id,
                'queue_type': 'rq',
                'video_path': video_path,
                'message': 'Transcription job enqueued successfully'
            }
        except Exception as e:
            logger.error(f"Error enqueueing transcription: {e}")
            return {
                'success': False,
                'error': str(e),
                'video_path': video_path
            }
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get detailed worker status information."""
        try:
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            ping = inspect.ping()
            active = inspect.active()
            reserved = inspect.reserved()
            
            workers = {}
            if stats:
                for worker_name, worker_stats in stats.items():
                    workers[worker_name] = {
                        'status': 'online' if ping and worker_name in ping else 'offline',
                        'stats': worker_stats,
                        'active_tasks': len(active.get(worker_name, [])),
                        'reserved_tasks': len(reserved.get(worker_name, []))
                    }
            
            return {
                'workers': workers,
                'summary': {
                    'total_workers': len(workers),
                    'online_workers': len([w for w in workers.values() if w['status'] == 'online']),
                    'offline_workers': len([w for w in workers.values() if w['status'] == 'offline']),
                    'total_active_tasks': sum(len(tasks) for tasks in active.values()) if active else 0,
                    'total_reserved_tasks': sum(len(tasks) for tasks in reserved.values()) if reserved else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting worker status: {e}")
            return {
                'error': str(e),
                'workers': {},
                'summary': {
                    'total_workers': 0,
                    'online_workers': 0,
                    'offline_workers': 0,
                    'total_active_tasks': 0,
                    'total_reserved_tasks': 0
                }
            }
    
    def _start_cache_refresh(self):
        """Start background cache refresh thread."""
        def refresh_cache():
            while True:
                try:
                    with self._cache_lock:
                        self._task_cache = {
                            'tasks': self.get_all_tasks(),
                            'summary': self.get_task_summary(),
                            'workers': self.get_worker_status(),
                            'timestamp': datetime.now()
                        }
                    time.sleep(30)  # Refresh every 30 seconds
                except Exception as e:
                    logger.error(f"Error refreshing cache: {e}")
                    time.sleep(60)  # Wait longer on error
        
        thread = threading.Thread(target=refresh_cache, daemon=True)
        thread.start()
    
    def get_cached_data(self) -> Dict[str, Any]:
        """Get cached data for quick access."""
        with self._cache_lock:
            cached_data = self._task_cache.copy()
            
            # Convert datetime objects to ISO format strings for JSON serialization
            if 'timestamp' in cached_data and isinstance(cached_data['timestamp'], datetime):
                cached_data['timestamp'] = cached_data['timestamp'].isoformat()
            
            # Convert datetime objects in tasks
            if 'tasks' in cached_data:
                for task in cached_data['tasks']:
                    for key, value in task.items():
                        if isinstance(value, datetime):
                            task[key] = value.isoformat()
            
            return cached_data

# Global instance
_unified_queue_manager = None

def get_unified_queue_manager() -> UnifiedQueueManager:
    """Get or create the unified queue manager instance."""
    global _unified_queue_manager
    if _unified_queue_manager is None:
        _unified_queue_manager = UnifiedQueueManager()
    return _unified_queue_manager 