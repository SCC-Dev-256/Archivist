"""
Queue analytics service for tracking job performance and queue metrics.
"""

import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

import redis
from loguru import logger

class QueueAnalytics:
    """Track queue performance and job analytics."""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.job_history = deque(maxlen=10000)  # Store last 10,000 jobs
        self.job_durations = defaultdict(list)  # Task type -> durations
        self.success_rates = defaultdict(lambda: {'success': 0, 'total': 0})
        self.lock = threading.Lock()
        
        # Initialize Redis client if not provided
        if self.redis_client is None:
            try:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis client not available for queue analytics: {e}")
                self.redis_client = None
    
    def track_job_start(self, job_id, task_name, args=None, kwargs=None):
        """Track when a job starts."""
        with self.lock:
            job_info = {
                'job_id': job_id,
                'task_name': task_name,
                'start_time': datetime.now(),
                'args': args,
                'kwargs': kwargs,
                'status': 'started'
            }
            self.job_history.append(job_info)
            
            # Store in Redis for persistence
            if self.redis_client:
                try:
                    key = f"job:{job_id}"
                    self.redis_client.hset(key, mapping={
                        'task_name': task_name,
                        'start_time': job_info['start_time'].isoformat(),
                        'status': 'started'
                    })
                    self.redis_client.expire(key, 86400)  # Expire after 24 hours
                except Exception as e:
                    logger.warning(f"Failed to store job start in Redis: {e}")
    
    def track_job_success(self, job_id, result=None, duration=None):
        """Track when a job completes successfully."""
        with self.lock:
            # Find the job in history
            for job in self.job_history:
                if job['job_id'] == job_id:
                    job['end_time'] = datetime.now()
                    job['status'] = 'success'
                    job['result'] = result
                    
                    # Calculate duration
                    if duration is None and 'start_time' in job:
                        duration = (job['end_time'] - job['start_time']).total_seconds()
                    
                    job['duration'] = duration
                    
                    # Update analytics
                    task_name = job['task_name']
                    if duration:
                        self.job_durations[task_name].append(duration)
                        # Keep only last 1000 durations per task
                        if len(self.job_durations[task_name]) > 1000:
                            self.job_durations[task_name] = self.job_durations[task_name][-1000:]
                    
                    self.success_rates[task_name]['success'] += 1
                    self.success_rates[task_name]['total'] += 1
                    break
            
            # Update Redis
            if self.redis_client:
                try:
                    key = f"job:{job_id}"
                    self.redis_client.hset(key, mapping={
                        'end_time': datetime.now().isoformat(),
                        'status': 'success',
                        'duration': str(duration) if duration else 'unknown'
                    })
                except Exception as e:
                    logger.warning(f"Failed to update job success in Redis: {e}")
    
    def track_job_failure(self, job_id, exception=None, duration=None):
        """Track when a job fails."""
        with self.lock:
            # Find the job in history
            for job in self.job_history:
                if job['job_id'] == job_id:
                    job['end_time'] = datetime.now()
                    job['status'] = 'failed'
                    job['exception'] = str(exception) if exception else 'Unknown error'
                    
                    # Calculate duration
                    if duration is None and 'start_time' in job:
                        duration = (job['end_time'] - job['start_time']).total_seconds()
                    
                    job['duration'] = duration
                    
                    # Update analytics
                    task_name = job['task_name']
                    if duration:
                        self.job_durations[task_name].append(duration)
                        # Keep only last 1000 durations per task
                        if len(self.job_durations[task_name]) > 1000:
                            self.job_durations[task_name] = self.job_durations[task_name][-1000:]
                    
                    self.success_rates[task_name]['total'] += 1
                    break
            
            # Update Redis
            if self.redis_client:
                try:
                    key = f"job:{job_id}"
                    self.redis_client.hset(key, mapping={
                        'end_time': datetime.now().isoformat(),
                        'status': 'failed',
                        'exception': str(exception) if exception else 'Unknown error',
                        'duration': str(duration) if duration else 'unknown'
                    })
                except Exception as e:
                    logger.warning(f"Failed to update job failure in Redis: {e}")
    
    def get_queue_analytics(self):
        """Get comprehensive queue analytics."""
        with self.lock:
            now = datetime.now()
            
            # Calculate recent jobs (last 24 hours)
            one_day_ago = now - timedelta(days=1)
            recent_jobs = [job for job in self.job_history if job.get('start_time', now) > one_day_ago]
            
            # Calculate job statistics by task type
            task_stats = {}
            for task_name in set(job['task_name'] for job in self.job_history):
                task_jobs = [job for job in self.job_history if job['task_name'] == task_name]
                recent_task_jobs = [job for job in recent_jobs if job['task_name'] == task_name]
                
                # Success rate
                success_rate = self.success_rates[task_name]
                success_percentage = (success_rate['success'] / success_rate['total'] * 100) if success_rate['total'] > 0 else 0
                
                # Duration statistics
                durations = self.job_durations[task_name]
                avg_duration = sum(durations) / len(durations) if durations else 0
                max_duration = max(durations) if durations else 0
                min_duration = min(durations) if durations else 0
                
                # Calculate recent average duration
                recent_durations = [job.get('duration', 0) for job in recent_task_jobs if job.get('duration') is not None]
                recent_avg_duration = sum(recent_durations) / len(recent_durations) if recent_durations else 0
                
                task_stats[task_name] = {
                    'total_jobs': len(task_jobs),
                    'recent_jobs': len(recent_task_jobs),
                    'success_rate': round(success_percentage, 2),
                    'success_count': success_rate['success'],
                    'failure_count': success_rate['total'] - success_rate['success'],
                    'avg_duration': round(avg_duration, 2),
                    'max_duration': round(max_duration, 2),
                    'min_duration': round(min_duration, 2),
                    'recent_avg_duration': round(recent_avg_duration, 2)
                }
            
            # Overall statistics
            total_jobs = len(self.job_history)
            recent_total = len(recent_jobs)
            overall_success_rate = sum(stats['success_count'] for stats in task_stats.values())
            overall_total = sum(stats['success_count'] + stats['failure_count'] for stats in task_stats.values())
            overall_success_percentage = (overall_success_rate / overall_total * 100) if overall_total > 0 else 0
            
            return {
                'summary': {
                    'total_jobs': total_jobs,
                    'recent_jobs_24h': recent_total,
                    'overall_success_rate': round(overall_success_percentage, 2),
                    'active_task_types': len(task_stats)
                },
                'task_statistics': task_stats,
                'recent_jobs': [
                    {
                        'job_id': job['job_id'],
                        'task_name': job['task_name'],
                        'status': job['status'],
                        'start_time': job['start_time'].isoformat(),
                        'duration': job.get('duration', 0),
                        'exception': job.get('exception', None)
                    }
                    for job in recent_jobs[-50:]  # Last 50 jobs
                ]
            }
    
    def get_task_performance(self, task_name):
        """Get detailed performance metrics for a specific task."""
        with self.lock:
            task_jobs = [job for job in self.job_history if job['task_name'] == task_name]
            durations = self.job_durations[task_name]
            success_rate = self.success_rates[task_name]
            
            if not task_jobs:
                return None
            
            # Calculate percentiles
            sorted_durations = sorted(durations)
            p50 = sorted_durations[len(sorted_durations) // 2] if sorted_durations else 0
            p95 = sorted_durations[int(len(sorted_durations) * 0.95)] if sorted_durations else 0
            p99 = sorted_durations[int(len(sorted_durations) * 0.99)] if sorted_durations else 0
            
            return {
                'task_name': task_name,
                'total_executions': len(task_jobs),
                'success_rate': round((success_rate['success'] / success_rate['total'] * 100), 2) if success_rate['total'] > 0 else 0,
                'avg_duration': round(sum(durations) / len(durations), 2) if durations else 0,
                'min_duration': round(min(durations), 2) if durations else 0,
                'max_duration': round(max(durations), 2) if durations else 0,
                'p50_duration': round(p50, 2),
                'p95_duration': round(p95, 2),
                'p99_duration': round(p99, 2),
                'recent_durations': durations[-100:]  # Last 100 durations
            }

# Global instance
queue_analytics = QueueAnalytics() 