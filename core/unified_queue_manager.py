"""Unified Queue Management System

This module provides a simplified interface for managing Celery tasks.
All previous RQ (Redis Queue) functionality has been removed in favour of a
fully Celery-based implementation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import time
import threading
from loguru import logger

from core.tasks import celery_app

class UnifiedQueueManager:
    """Unified queue manager for Celery tasks."""
    
    def __init__(self):
        self._task_cache = {}
        self._cache_lock = threading.Lock()
        
        # Start background cache refresh
        self._start_cache_refresh()
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from Celery."""
        try:
            tasks = []
            
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
        """Get summary statistics for Celery tasks."""
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
    
    def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific Celery task."""
        try:
            result = celery_app.AsyncResult(task_id)
            return {
                'id': task_id,
                'queue_type': 'celery',
                'status': result.status,
                'result': result.result if result.ready() else None,
                'error': str(result.info) if result.failed() else None,
                'created_at': None,
                'started_at': None,
                'ended_at': None
            }
                
        except Exception as e:
            logger.error(f"Error getting task details for {task_id}: {e}")
            return None
    
    def stop_task(self, task_id: str) -> bool:
        """Stop a running Celery task."""
        try:
            celery_app.control.revoke(task_id, terminate=True)
            return True
                
        except Exception as e:
            logger.error(f"Error stopping task {task_id}: {e}")
            return False
    
    def pause_task(self, task_id: str) -> bool:
        """Attempt to pause a Celery task.

        Celery does not natively support pausing tasks so this method issues a
        revoke without terminating the running process. It will effectively
        prevent the task from executing if it has not yet started.
        """
        try:
            celery_app.control.revoke(task_id, terminate=False)
            return True
                
        except Exception as e:
            logger.error(f"Error pausing task {task_id}: {e}")
            return False
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a task.

        Celery does not have a built in resume capability, so this method simply
        returns ``False`` to indicate the operation is not supported.
        """
        try:
            logger.warning("Celery doesn't support resuming tasks")
            return False
                
        except Exception as e:
            logger.error(f"Error resuming task {task_id}: {e}")
            return False
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a Celery task from the queue and backend."""
        try:
            celery_app.control.revoke(task_id, terminate=True)
            result = celery_app.AsyncResult(task_id)
            result.forget()
            return True
                
        except Exception as e:
            logger.error(f"Error removing task {task_id}: {e}")
            return False
    
    def reorder_task(self, task_id: str, position: int) -> bool:
        """Reorder a task.

        Celery does not provide task reordering, so this always returns ``False``.
        """
        try:
            logger.warning("Celery doesn't support reordering tasks")
            return False
                
        except Exception as e:
            logger.error(f"Error reordering task {task_id}: {e}")
            return False
    
    def cleanup_failed_tasks(self) -> Dict[str, int]:
        """Clean up failed Celery tasks."""
        try:
            # Celery relies on the result backend TTL for failed task cleanup.
            # This method is retained for API compatibility and returns an empty result.
            return {}

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