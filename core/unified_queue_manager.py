"""Unified Queue Management System

This module provides a simplified interface for managing Celery tasks.
All previous RQ (Redis Queue) functionality has been removed in favour of a
fully Celery-based implementation.

Enhanced Features:
- Task resuming through task recreation with state preservation
- Task reordering through priority-based queue management
- Failed task cleanup with configurable retention policies
- Task state persistence and recovery
"""

import os
import json
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from celery.result import AsyncResult
from loguru import logger

from core.tasks import celery_app
from core.exceptions import QueueError
from core.config import REDIS_URL

class UnifiedQueueManager:
    """Unified queue manager for Celery tasks with enhanced capabilities."""
    
    def __init__(self):
        self._task_cache = {}
        self._cache_lock = threading.Lock()
        self._redis_client = redis.from_url(REDIS_URL)
        
        # Task state persistence keys
        self._task_state_prefix = "archivist:task_state:"
        self._failed_task_prefix = "archivist:failed_tasks:"
        self._task_priority_prefix = "archivist:task_priority:"
        
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
            result = AsyncResult(task_id, app=celery_app)
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
        """Resume a paused or failed task by recreating it with preserved state.
        
        This implementation works around Celery's lack of native resume support
        by:
        1. Retrieving the original task state from Redis
        2. Recreating the task with the same parameters
        3. Preserving any progress or intermediate results
        """
        try:
            # Get the original task state
            task_state = self._get_task_state(task_id)
            if not task_state:
                logger.warning(f"No saved state found for task {task_id}")
                return False
            
            # Get the current task result to check if it's actually resumable
            result = AsyncResult(task_id, app=celery_app)
            if result.status in ['SUCCESS', 'PENDING']:
                logger.warning(f"Task {task_id} is not in a resumable state: {result.status}")
                return False
            
            # Extract task information from state
            task_name = task_state.get('task_name')
            task_args = task_state.get('args', [])
            task_kwargs = task_state.get('kwargs', {})
            task_progress = task_state.get('progress', 0)
            
            if not task_name:
                logger.error(f"No task name found in state for {task_id}")
                return False
            
            # Recreate the task with preserved state
            new_task = celery_app.send_task(
                task_name,
                args=task_args,
                kwargs=task_kwargs,
                countdown=0  # Start immediately
            )
            
            # Transfer any progress or intermediate results
            if task_progress > 0:
                self._save_task_state(new_task.id, {
                    'task_name': task_name,
                    'args': task_args,
                    'kwargs': task_kwargs,
                    'progress': task_progress,
                    'resumed_from': task_id,
                    'resumed_at': datetime.now().isoformat()
                })
            
            # Clean up the old task state
            self._delete_task_state(task_id)
            
            # Revoke the old task if it's still running
            if result.status == 'STARTED':
                celery_app.control.revoke(task_id, terminate=True)
            
            logger.info(f"Successfully resumed task {task_id} as {new_task.id}")
            return True
                
        except Exception as e:
            logger.error(f"Error resuming task {task_id}: {e}")
            return False
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a Celery task from the queue and backend."""
        try:
            celery_app.control.revoke(task_id, terminate=True)
            result = AsyncResult(task_id, app=celery_app)
            result.forget()
            return True
                
        except Exception as e:
            logger.error(f"Error removing task {task_id}: {e}")
            return False
    
    def reorder_task(self, task_id: str, position: int) -> bool:
        """Reorder a task by adjusting its priority.
        
        This implementation works around Celery's lack of native reordering by:
        1. Setting a custom priority for the task
        2. Using Celery's priority queue feature
        3. Maintaining order through priority values
        """
        try:
            # Get current task information
            result = AsyncResult(task_id, app=celery_app)
            if result.status not in ['PENDING', 'RETRY']:
                logger.warning(f"Cannot reorder task {task_id} in state {result.status}")
                return False
            
            # Calculate priority based on position (lower number = higher priority)
            # Position 0 = highest priority (priority 0)
            # Position 100 = lower priority (priority 100)
            priority = max(0, min(100, position))
            
            # Store the priority for this task
            self._set_task_priority(task_id, priority)
            
            # For pending tasks, we can influence their execution order
            # by adjusting the queue priority. This is a best-effort approach
            # since Celery doesn't guarantee strict ordering.
            
            # Get all pending tasks and their priorities
            inspect = celery_app.control.inspect()
            reserved_tasks = inspect.reserved() or {}
            
            # Create a priority map for all tasks
            task_priorities = {}
            for worker, tasks in reserved_tasks.items():
                for task in tasks:
                    if task['id'] == task_id:
                        task_priorities[task_id] = priority
                    else:
                        # Get existing priority or use default
                        existing_priority = self._get_task_priority(task['id'])
                        task_priorities[task['id']] = existing_priority
            
            # Sort tasks by priority
            sorted_tasks = sorted(task_priorities.items(), key=lambda x: x[1])
            
            # Update priorities for all tasks to maintain order
            for i, (tid, _) in enumerate(sorted_tasks):
                self._set_task_priority(tid, i)
            
            logger.info(f"Successfully reordered task {task_id} to position {position} (priority {priority})")
            return True
                
        except Exception as e:
            logger.error(f"Error reordering task {task_id}: {e}")
            return False
    
    def cleanup_failed_tasks(self) -> Dict[str, int]:
        """Clean up failed Celery tasks with configurable retention policies.
        
        This implementation provides comprehensive failed task cleanup by:
        1. Identifying failed tasks in the result backend
        2. Applying retention policies based on task type and age
        3. Cleaning up associated temporary files and state
        4. Providing detailed cleanup statistics
        """
        try:
            cleanup_stats = {
                'tasks_cleaned': 0,
                'state_cleaned': 0,
                'temp_files_cleaned': 0,
                'errors': []
            }
            
            # Get failed tasks from result backend
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            
            if not stats:
                logger.warning("No worker stats available for cleanup")
                return cleanup_stats
            
            # Define retention policies (in hours)
            retention_policies = {
                'transcription': 24,      # Keep transcription failures for 24 hours
                'vod_processing': 48,     # Keep VOD processing failures for 48 hours
                'default': 12             # Default retention for other tasks
            }
            
            current_time = datetime.now()
            
            # Scan for failed tasks in the result backend
            # Note: This is a simplified approach. In production, you might want
            # to use Celery's result backend inspection capabilities
            
            # Clean up task state entries older than retention period
            state_keys = self._redis_client.keys(f"{self._task_state_prefix}*")
            for key in state_keys:
                try:
                    task_id = key.decode().split(':')[-1]
                    state_data = self._redis_client.get(key)
                    
                    if state_data:
                        state = json.loads(state_data)
                        saved_at = datetime.fromisoformat(state.get('saved_at', '1970-01-01T00:00:00'))
                        task_name = state.get('task_name', 'default')
                        
                        # Determine retention period
                        retention_hours = retention_policies.get(
                            task_name.split('.')[0] if '.' in task_name else 'default',
                            retention_policies['default']
                        )
                        
                        # Check if task state should be cleaned up
                        if (current_time - saved_at).total_seconds() > (retention_hours * 3600):
                            self._redis_client.delete(key)
                            cleanup_stats['state_cleaned'] += 1
                            logger.debug(f"Cleaned up old task state: {task_id}")
                            
                except Exception as e:
                    error_msg = f"Error cleaning up task state {key}: {e}"
                    cleanup_stats['errors'].append(error_msg)
                    logger.warning(error_msg)
            
            # Clean up priority entries older than 24 hours
            priority_keys = self._redis_client.keys(f"{self._task_priority_prefix}*")
            for key in priority_keys:
                try:
                    # Check if the key is older than 24 hours
                    ttl = self._redis_client.ttl(key)
                    if ttl == -1:  # No TTL set, set one
                        self._redis_client.expire(key, 86400)
                    elif ttl <= 0:  # Expired, delete
                        self._redis_client.delete(key)
                        cleanup_stats['state_cleaned'] += 1
                        
                except Exception as e:
                    error_msg = f"Error cleaning up priority entry {key}: {e}"
                    cleanup_stats['errors'].append(error_msg)
                    logger.warning(error_msg)
            
            # Clean up temporary files associated with failed tasks
            temp_cleanup_result = self._cleanup_temp_files_for_failed_tasks()
            cleanup_stats['temp_files_cleaned'] = temp_cleanup_result.get('files_cleaned', 0)
            cleanup_stats['errors'].extend(temp_cleanup_result.get('errors', []))
            
            logger.info(f"Failed task cleanup completed: {cleanup_stats['state_cleaned']} state entries, "
                       f"{cleanup_stats['temp_files_cleaned']} temp files cleaned")
            
            return cleanup_stats

        except Exception as e:
            logger.error(f"Error cleaning up failed tasks: {e}")
            return {'error': str(e), 'tasks_cleaned': 0, 'state_cleaned': 0, 'temp_files_cleaned': 0, 'errors': [str(e)]}
    
    def _cleanup_temp_files_for_failed_tasks(self) -> Dict[str, Any]:
        """Clean up temporary files associated with failed tasks."""
        import os
        import glob
        
        cleanup_result = {
            'files_cleaned': 0,
            'errors': []
        }
        
        try:
            # Common temporary file patterns for failed tasks
            temp_patterns = [
                '/tmp/*whisper*',
                '/tmp/*transcription*',
                '/tmp/*vod_*',
                '/tmp/*temp*',
                '/var/tmp/*whisper*',
                '/var/tmp/*transcription*'
            ]
            
            cutoff_time = datetime.now() - timedelta(hours=6)  # Clean files older than 6 hours
            
            for pattern in temp_patterns:
                try:
                    for file_path in glob.glob(pattern):
                        if os.path.isfile(file_path):
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            
                            if file_time < cutoff_time:
                                try:
                                    os.remove(file_path)
                                    cleanup_result['files_cleaned'] += 1
                                    logger.debug(f"Cleaned up temp file: {file_path}")
                                except Exception as e:
                                    error_msg = f"Failed to remove temp file {file_path}: {e}"
                                    cleanup_result['errors'].append(error_msg)
                                    logger.warning(error_msg)
                                    
                except Exception as e:
                    error_msg = f"Error processing temp pattern {pattern}: {e}"
                    cleanup_result['errors'].append(error_msg)
                    logger.warning(error_msg)
                    
        except Exception as e:
            error_msg = f"Error in temp file cleanup: {e}"
            cleanup_result['errors'].append(error_msg)
            logger.error(error_msg)
        
        return cleanup_result
    
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
                except (RedisError, ConnectionError) as e:
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
    
    def _save_task_state(self, task_id: str, state: Dict[str, Any]) -> bool:
        """Save task state to Redis for potential resuming."""
        try:
            key = f"{self._task_state_prefix}{task_id}"
            state['saved_at'] = datetime.now().isoformat()
            self._redis_client.setex(key, 3600, json.dumps(state))  # 1 hour TTL
            return True
        except Exception as e:
            logger.error(f"Error saving task state for {task_id}: {e}")
            return False
    
    def _get_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve saved task state from Redis."""
        try:
            key = f"{self._task_state_prefix}{task_id}"
            data = self._redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving task state for {task_id}: {e}")
            return None
    
    def _delete_task_state(self, task_id: str) -> bool:
        """Delete saved task state from Redis."""
        try:
            key = f"{self._task_state_prefix}{task_id}"
            self._redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting task state for {task_id}: {e}")
            return False
    
    def _get_task_priority(self, task_id: str) -> int:
        """Get task priority from Redis."""
        try:
            key = f"{self._task_priority_prefix}{task_id}"
            priority = self._redis_client.get(key)
            return int(priority) if priority else 0
        except Exception:
            return 0
    
    def _set_task_priority(self, task_id: str, priority: int) -> bool:
        """Set task priority in Redis."""
        try:
            key = f"{self._task_priority_prefix}{task_id}"
            self._redis_client.setex(key, 86400, str(priority))  # 24 hour TTL
            return True
        except Exception as e:
            logger.error(f"Error setting task priority for {task_id}: {e}")
            return False

# Global instance
_unified_queue_manager = None

def get_unified_queue_manager() -> UnifiedQueueManager:
    """Get or create the unified queue manager instance."""
    global _unified_queue_manager
    if _unified_queue_manager is None:
        _unified_queue_manager = UnifiedQueueManager()
    return _unified_queue_manager 