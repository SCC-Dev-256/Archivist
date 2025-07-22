"""
Integrated Monitoring Dashboard with Queue Management

This module provides a comprehensive web-based monitoring dashboard that integrates:
- VOD processing monitoring
- Queue management (RQ + Celery)
- Real-time metrics and health checks
- Unified task management interface
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Flask, render_template, jsonify, request, Blueprint
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import threading

from loguru import logger
from core.monitoring.metrics import get_metrics_collector
from core.monitoring.health_checks import get_health_manager
from core.task_queue import QueueManager
from core.tasks import celery_app

class IntegratedDashboard:
    """Integrated monitoring dashboard with queue management."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5051):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'archivist-integrated-dashboard-2025'
        
        # Initialize SocketIO for real-time updates
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')
        
        self.metrics_collector = get_metrics_collector()
        self.health_manager = get_health_manager()
        self.queue_manager = QueueManager()
        
        # Task history storage for analytics
        self.task_history = []
        self.max_history_size = 1000
        
        # Enable CORS
        CORS(self.app)
        
        # Register routes and SocketIO events
        self._register_routes()
        self._register_socketio_events()
        
        # Start background metrics collection and real-time monitoring
        self._start_background_collection()
        self._start_realtime_monitoring()
    
    def _register_socketio_events(self):
        """Register SocketIO event handlers for real-time updates."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info(f"Client connected: {request.sid}")
            emit('connected', {'status': 'connected', 'timestamp': datetime.now().isoformat()})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('join_task_monitoring')
        def handle_join_task_monitoring(data):
            """Join task monitoring room."""
            room = 'task_monitoring'
            join_room(room)
            emit('joined_room', {'room': room, 'status': 'joined'})
            logger.info(f"Client {request.sid} joined task monitoring room")
        
        @self.socketio.on('request_task_updates')
        def handle_request_task_updates(data):
            """Send current task status on request."""
            try:
                task_data = self._get_realtime_task_data()
                emit('task_updates', task_data)
            except Exception as e:
                logger.error(f"Error sending task updates: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('filter_tasks')
        def handle_filter_tasks(data):
            """Filter tasks by type and send filtered results."""
            try:
                task_type = data.get('type', 'all')
                filtered_data = self._get_filtered_task_data(task_type)
                emit('filtered_tasks', filtered_data)
            except Exception as e:
                logger.error(f"Error filtering tasks: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('request_system_metrics')
        def handle_system_metrics_request():
            """Send system metrics to client (from web_interface)."""
            try:
                import psutil
                import redis as redis_lib
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                # Celery
                inspect = celery_app.control.inspect()
                active_workers = inspect.stats() if inspect else {}
                # Redis
                try:
                    redis_client = redis_lib.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                    redis_client.ping()
                    redis_info = redis_client.info()
                    redis_status = {
                        'status': 'connected',
                        'version': redis_info.get('redis_version', 'unknown'),
                        'connected_clients': redis_info.get('connected_clients', 0),
                        'used_memory_human': redis_info.get('used_memory_human', 'unknown'),
                    }
                except Exception as e:
                    redis_status = {'status': 'disconnected', 'error': str(e)}
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'system': {
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'memory_available': memory.available // (1024**3),
                        'disk_percent': disk.percent,
                        'disk_free': disk.free // (1024**3),
                    },
                    'celery': {
                        'active_workers': list(active_workers.keys()) if active_workers else [],
                        'worker_count': len(active_workers) if active_workers else 0,
                    },
                    'redis': redis_status
                }
                emit('system_metrics', metrics)
            except Exception as e:
                logger.error(f"Error sending system metrics: {e}")
                emit('error', {'message': str(e)})
    
    def _register_routes(self):
        """Register all dashboard routes."""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page."""
            return self._render_dashboard()
        
        @self.app.route('/api/metrics')
        def api_metrics():
            """Get current metrics data."""
            return jsonify(self.metrics_collector.export_metrics())
        
        @self.app.route('/api/health')
        def api_health():
            """Get health check data."""
            return jsonify(self.health_manager.get_health_status())
        
        @self.app.route('/api/queue/jobs')
        def api_queue_jobs():
            """Get all queue jobs."""
            try:
                jobs = self.queue_manager.get_all_jobs()
                return jsonify({
                    'jobs': jobs,
                    'total': len(jobs),
                    'status_counts': self._count_job_statuses(jobs)
                })
            except Exception as e:
                logger.error(f"Error getting queue jobs: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>')
        def api_queue_job_detail(job_id):
            """Get specific job details."""
            try:
                job_status = self.queue_manager.get_job_status(job_id)
                return jsonify(job_status)
            except Exception as e:
                logger.error(f"Error getting job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/reorder', methods=['POST'])
        def api_queue_reorder_job(job_id):
            """Reorder a job in the queue."""
            try:
                data = request.get_json()
                position = data.get('position', 0)
                success = self.queue_manager.reorder_job(job_id, position)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error reordering job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/stop', methods=['POST'])
        def api_queue_stop_job(job_id):
            """Stop a running job."""
            try:
                success = self.queue_manager.stop_job(job_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error stopping job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/pause', methods=['POST'])
        def api_queue_pause_job(job_id):
            """Pause a job."""
            try:
                success = self.queue_manager.pause_job(job_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error pausing job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/resume', methods=['POST'])
        def api_queue_resume_job(job_id):
            """Resume a paused job."""
            try:
                success = self.queue_manager.resume_job(job_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error resuming job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/remove', methods=['DELETE'])
        def api_queue_remove_job(job_id):
            """Remove a job from the queue."""
            try:
                success = self.queue_manager.remove_job(job_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error removing job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/celery/tasks')
        def api_celery_tasks():
            """Get Celery task statistics with real-time updates."""
            try:
                # Get Celery task stats
                inspect = celery_app.control.inspect()
                stats = inspect.stats()
                active = inspect.active()
                reserved = inspect.reserved()
                
                # Get real-time task data
                realtime_data = self._get_realtime_task_data()
                
                return jsonify({
                    'stats': stats,
                    'active': active,
                    'reserved': reserved,
                    'summary': self._summarize_celery_tasks(stats, active, reserved),
                    'realtime': realtime_data,
                    'task_history': self._get_task_analytics()
                })
            except Exception as e:
                logger.error(f"Error getting Celery tasks: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/tasks/realtime')
        def api_tasks_realtime():
            """Get real-time task monitoring data."""
            try:
                return jsonify(self._get_realtime_task_data())
            except Exception as e:
                logger.error(f"Error getting real-time task data: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/tasks/analytics')
        def api_tasks_analytics():
            """Get task performance analytics."""
            try:
                return jsonify(self._get_task_analytics())
            except Exception as e:
                logger.error(f"Error getting task analytics: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/celery/workers')
        def api_celery_workers():
            """Get Celery worker status."""
            try:
                inspect = celery_app.control.inspect()
                stats = inspect.stats()
                ping = inspect.ping()
                
                return jsonify({
                    'workers': stats,
                    'ping': ping,
                    'summary': self._summarize_celery_workers(stats, ping)
                })
            except Exception as e:
                logger.error(f"Error getting Celery workers: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/unified/tasks')
        def api_unified_tasks():
            """Get unified task view (RQ + Celery)."""
            try:
                # Get RQ jobs
                rq_jobs = self.queue_manager.get_all_jobs()
                
                # Get Celery tasks
                inspect = celery_app.control.inspect()
                celery_active = inspect.active() or {}
                celery_reserved = inspect.reserved() or {}
                
                # Combine into unified view
                unified_tasks = []
                
                # Add RQ jobs
                for job in rq_jobs:
                    unified_tasks.append({
                        'id': job['id'],
                        'type': 'rq',
                        'name': 'Transcription Job',
                        'status': job['status'],
                        'progress': job.get('progress', 0),
                        'created_at': job.get('created_at'),
                        'started_at': job.get('started_at'),
                        'video_path': job.get('video_path', ''),
                        'position': job.get('position', 0)
                    })
                
                # Add Celery tasks
                for worker, tasks in celery_active.items():
                    for task in tasks:
                        unified_tasks.append({
                            'id': task['id'],
                            'type': 'celery',
                            'name': task['name'],
                            'status': 'active',
                            'progress': 0,  # Celery doesn't provide progress
                            'created_at': task.get('time_start'),
                            'started_at': task.get('time_start'),
                            'worker': worker,
                            'args': task.get('args', [])
                        })
                
                # Add reserved Celery tasks
                for worker, tasks in celery_reserved.items():
                    for task in tasks:
                        unified_tasks.append({
                            'id': task['id'],
                            'type': 'celery',
                            'name': task['name'],
                            'status': 'reserved',
                            'progress': 0,
                            'created_at': task.get('time_start'),
                            'started_at': None,
                            'worker': worker,
                            'args': task.get('args', [])
                        })
                
                return jsonify({
                    'tasks': unified_tasks,
                    'total': len(unified_tasks),
                    'rq_count': len(rq_jobs),
                    'celery_active_count': sum(len(tasks) for tasks in celery_active.values()),
                    'celery_reserved_count': sum(len(tasks) for tasks in celery_reserved.values())
                })
            except Exception as e:
                logger.error(f"Error getting unified tasks: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/vod/sync-status')
        def api_vod_sync_status():
            """Get VOD sync monitor status."""
            try:
                from scripts.monitoring.vod_sync_monitor import VODSyncMonitor
                monitor = VODSyncMonitor()
                if monitor.initialize_components():
                    health_report = monitor.generate_health_report()
                    return jsonify(health_report)
                else:
                    return jsonify({'error': 'VOD sync monitor not initialized'}), 500
            except Exception as e:
                logger.error(f"Error getting VOD sync status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/vod/automation/status')
        def api_vod_automation_status():
            """Get VOD automation status."""
            try:
                from core.vod_automation import get_transcription_link_status
                
                # Get recent transcriptions and their link status
                from core.models import TranscriptionResultORM
                recent_transcriptions = TranscriptionResultORM.query.order_by(
                    TranscriptionResultORM.completed_at.desc()
                ).limit(20).all()
                
                automation_status = {
                    'recent_transcriptions': [],
                    'linked_count': 0,
                    'unlinked_count': 0
                }
                
                for transcription in recent_transcriptions:
                    link_status = get_transcription_link_status(transcription.id)
                    automation_status['recent_transcriptions'].append({
                        'id': transcription.id,
                        'video_path': transcription.video_path,
                        'completed_at': transcription.completed_at.isoformat(),
                        'linked': link_status.get('linked', False),
                        'show_id': link_status.get('show_id'),
                        'show_title': link_status.get('show_title')
                    })
                    
                    if link_status.get('linked'):
                        automation_status['linked_count'] += 1
                    else:
                        automation_status['unlinked_count'] += 1
                
                return jsonify(automation_status)
            except Exception as e:
                logger.error(f"Error getting VOD automation status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/vod/automation/link/<transcription_id>', methods=['POST'])
        def api_vod_automation_link(transcription_id):
            """Link transcription to show."""
            try:
                from core.vod_automation import auto_link_transcription_to_show
                result = auto_link_transcription_to_show(transcription_id)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Error linking transcription {transcription_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/vod/automation/manual-link/<transcription_id>/<int:show_id>', methods=['POST'])
        def api_vod_automation_manual_link(transcription_id, show_id):
            """Manually link transcription to show."""
            try:
                from core.vod_automation import manual_link_transcription_to_show
                result = manual_link_transcription_to_show(transcription_id, show_id)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Error manually linking transcription {transcription_id} to show {show_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/vod/automation/suggestions/<transcription_id>')
        def api_vod_automation_suggestions(transcription_id):
            """Get show suggestions for transcription."""
            try:
                from core.vod_automation import get_show_suggestions
                result = get_show_suggestions(transcription_id)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Error getting suggestions for transcription {transcription_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/vod/automation/process-queue', methods=['POST'])
        def api_vod_automation_process_queue():
            """Process transcription linking queue."""
            try:
                from core.vod_automation import process_transcription_queue
                result = process_transcription_queue()
                return jsonify(result)
            except Exception as e:
                logger.error(f"Error processing transcription queue: {e}")
                return jsonify({'error': str(e)}), 500
                
                # Add Celery tasks
                for worker, tasks in celery_active.items():
                    for task in tasks:
                        unified_tasks.append({
                            'id': task['id'],
                            'type': 'celery',
                            'name': task['name'],
                            'status': 'active',
                            'progress': 0,  # Celery doesn't provide progress
                            'created_at': task.get('time_start'),
                            'started_at': task.get('time_start'),
                            'ended_at': None,
                            'video_path': '',
                            'worker': worker
                        })
                
                for worker, tasks in celery_reserved.items():
                    for task in tasks:
                        unified_tasks.append({
                            'id': task['id'],
                            'type': 'celery',
                            'name': task['name'],
                            'status': 'reserved',
                            'progress': 0,
                            'created_at': task.get('time_start'),
                            'started_at': None,
                            'ended_at': None,
                            'video_path': '',
                            'worker': worker
                        })
                
                return jsonify({
                    'tasks': unified_tasks,
                    'summary': {
                        'total': len(unified_tasks),
                        'rq_count': len(rq_jobs),
                        'celery_active': sum(len(tasks) for tasks in celery_active.values()),
                        'celery_reserved': sum(len(tasks) for tasks in celery_reserved.values())
                    }
                })
            except Exception as e:
                logger.error(f"Error getting unified tasks: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/tasks/trigger_vod_processing', methods=['POST'])
        def trigger_vod_processing():
            """Trigger VOD processing manually (from web_interface)."""
            try:
                from core.tasks.vod_processing import process_recent_vods
                result = process_recent_vods.delay()
                return jsonify({
                    'success': True,
                    'task_id': result.id,
                    'message': 'VOD processing triggered successfully'
                })
            except Exception as e:
                logger.error(f"Error triggering VOD processing: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/tasks/trigger_transcription', methods=['POST'])
        def trigger_transcription():
            """Trigger transcription for a specific file (from web_interface)."""
            try:
                from core.tasks.transcription import run_whisper_transcription
                data = request.get_json()
                file_path = data.get('file_path')
                if not file_path:
                    return jsonify({
                        'success': False,
                        'error': 'file_path is required'
                    }), 400
                result = run_whisper_transcription.delay(file_path)
                return jsonify({
                    'success': True,
                    'task_id': result.id,
                    'message': f'Transcription triggered for {file_path}'
                })
            except Exception as e:
                logger.error(f"Error triggering transcription: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/status')
        def api_status():
            """Alias for system metrics (from web_interface)."""
            try:
                # Compose system metrics (CPU, memory, disk, Redis, Celery)
                import psutil
                import redis as redis_lib
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                # Celery
                inspect = celery_app.control.inspect()
                active_workers = inspect.stats() if inspect else {}
                # Redis
                try:
                    redis_client = redis_lib.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                    redis_client.ping()
                    redis_info = redis_client.info()
                    redis_status = {
                        'status': 'connected',
                        'version': redis_info.get('redis_version', 'unknown'),
                        'connected_clients': redis_info.get('connected_clients', 0),
                        'used_memory_human': redis_info.get('used_memory_human', 'unknown'),
                    }
                except Exception as e:
                    redis_status = {'status': 'disconnected', 'error': str(e)}
                return jsonify({
                    'timestamp': datetime.now().isoformat(),
                    'system': {
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'memory_available': memory.available // (1024**3),
                        'disk_percent': disk.percent,
                        'disk_free': disk.free // (1024**3),
                    },
                    'celery': {
                        'active_workers': list(active_workers.keys()) if active_workers else [],
                        'worker_count': len(active_workers) if active_workers else 0,
                    },
                    'redis': redis_status
                })
            except Exception as e:
                logger.error(f"Error in /api/status: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _count_job_statuses(self, jobs: List[Dict]) -> Dict[str, int]:
        """Count jobs by status."""
        counts = {}
        for job in jobs:
            status = job.get('status', 'unknown')
            counts[status] = counts.get(status, 0) + 1
        return counts
    
    def _summarize_celery_tasks(self, stats: Dict, active: Dict, reserved: Dict) -> Dict[str, Any]:
        """Summarize Celery task statistics."""
        total_tasks = 0
        active_tasks = 0
        reserved_tasks = 0
        
        if stats:
            for worker_stats in stats.values():
                total_tasks += worker_stats.get('total', {})
        
        if active:
            for worker_tasks in active.values():
                active_tasks += len(worker_tasks)
        
        if reserved:
            for worker_tasks in reserved.values():
                reserved_tasks += len(worker_tasks)
        
        return {
            'total_tasks': total_tasks,
            'active_tasks': active_tasks,
            'reserved_tasks': reserved_tasks,
            'worker_count': len(stats) if stats else 0
        }
    
    def _summarize_celery_workers(self, stats: Dict, ping: Dict) -> Dict[str, Any]:
        """Summarize Celery worker statistics."""
        if not stats:
            return {'active_workers': 0, 'total_workers': 0}
        
        active_workers = len(ping) if ping else 0
        total_workers = len(stats)
        
        return {
            'active_workers': active_workers,
            'total_workers': total_workers,
            'worker_status': 'healthy' if active_workers > 0 else 'unhealthy'
        }
    
    def _get_realtime_task_data(self) -> Dict[str, Any]:
        """Get real-time task monitoring data."""
        try:
            # Get current task status
            inspect = celery_app.control.inspect()
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            stats = inspect.stats() or {}
            
            # Get RQ jobs
            rq_jobs = self.queue_manager.get_all_jobs()
            
            # Combine into real-time view
            realtime_tasks = []
            
            # Add active Celery tasks with progress tracking
            for worker, tasks in active.items():
                for task in tasks:
                    task_info = {
                        'id': task['id'],
                        'type': 'celery',
                        'name': task['name'],
                        'status': 'active',
                        'worker': worker,
                        'started_at': task.get('time_start'),
                        'args': task.get('args', []),
                        'progress': self._get_task_progress(task['id']),
                        'duration': time.time() - task.get('time_start', time.time()) if task.get('time_start') else 0
                    }
                    realtime_tasks.append(task_info)
            
            # Add reserved Celery tasks
            for worker, tasks in reserved.items():
                for task in tasks:
                    task_info = {
                        'id': task['id'],
                        'type': 'celery',
                        'name': task['name'],
                        'status': 'reserved',
                        'worker': worker,
                        'created_at': task.get('time_start'),
                        'args': task.get('args', []),
                        'progress': 0,
                        'duration': 0
                    }
                    realtime_tasks.append(task_info)
            
            # Add RQ jobs
            for job in rq_jobs:
                task_info = {
                    'id': job['id'],
                    'type': 'rq',
                    'name': 'Transcription Job',
                    'status': job['status'],
                    'progress': job.get('progress', 0),
                    'created_at': job.get('created_at'),
                    'started_at': job.get('started_at'),
                    'video_path': job.get('video_path', ''),
                    'duration': self._calculate_job_duration(job)
                }
                realtime_tasks.append(task_info)
            
            return {
                'tasks': realtime_tasks,
                'summary': {
                    'total': len(realtime_tasks),
                    'active': len([t for t in realtime_tasks if t['status'] == 'active']),
                    'reserved': len([t for t in realtime_tasks if t['status'] == 'reserved']),
                    'queued': len([t for t in realtime_tasks if t['status'] == 'queued']),
                    'celery_active': sum(len(tasks) for tasks in active.values()),
                    'celery_reserved': sum(len(tasks) for tasks in reserved.values()),
                    'rq_jobs': len(rq_jobs)
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting real-time task data: {e}")
            return {'error': str(e)}
    
    def _get_filtered_task_data(self, task_type: str) -> Dict[str, Any]:
        """Get filtered task data by type."""
        realtime_data = self._get_realtime_task_data()
        if 'error' in realtime_data:
            return realtime_data
        
        if task_type == 'all':
            return realtime_data
        
        filtered_tasks = []
        for task in realtime_data['tasks']:
            if task_type == 'vod' and 'vod' in task['name'].lower():
                filtered_tasks.append(task)
            elif task_type == 'transcription' and ('transcription' in task['name'].lower() or task['type'] == 'rq'):
                filtered_tasks.append(task)
            elif task_type == 'cleanup' and 'cleanup' in task['name'].lower():
                filtered_tasks.append(task)
        
        return {
            'tasks': filtered_tasks,
            'summary': {
                'total': len(filtered_tasks),
                'type': task_type
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_task_progress(self, task_id: str) -> float:
        """Get task progress from Celery result backend."""
        try:
            result = celery_app.AsyncResult(task_id)
            if result.state == 'PROGRESS':
                return result.info.get('progress', 0)
            elif result.state == 'SUCCESS':
                return 100.0
            elif result.state == 'FAILURE':
                return 0.0
            else:
                return 0.0
        except Exception as e:
            logger.debug(f"Error getting progress for task {task_id}: {e}")
            return 0.0
    
    def _calculate_job_duration(self, job: Dict) -> float:
        """Calculate job duration in seconds."""
        try:
            if job.get('started_at') and job.get('ended_at'):
                return (job['ended_at'] - job['started_at']).total_seconds()
            elif job.get('started_at'):
                return (datetime.now() - job['started_at']).total_seconds()
            else:
                return 0.0
        except Exception:
            return 0.0
    
    def _get_task_analytics(self) -> Dict[str, Any]:
        """Get task performance analytics."""
        try:
            # Calculate analytics from task history
            if not self.task_history:
                return {
                    'average_completion_time': 0,
                    'success_rate': 0,
                    'total_tasks': 0,
                    'task_types': {},
                    'recent_performance': []
                }
            
            completed_tasks = [t for t in self.task_history if t.get('status') in ['SUCCESS', 'FAILURE']]
            successful_tasks = [t for t in completed_tasks if t.get('status') == 'SUCCESS']
            
            # Calculate average completion time
            completion_times = []
            for task in completed_tasks:
                if task.get('duration'):
                    completion_times.append(task['duration'])
            
            avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
            
            # Calculate success rate
            success_rate = (len(successful_tasks) / len(completed_tasks) * 100) if completed_tasks else 0
            
            # Task type distribution
            task_types = {}
            for task in self.task_history:
                task_type = task.get('type', 'unknown')
                task_types[task_type] = task_types.get(task_type, 0) + 1
            
            # Recent performance (last 24 hours)
            recent_tasks = [t for t in self.task_history 
                          if t.get('timestamp') and 
                          datetime.fromisoformat(t['timestamp']) > datetime.now() - timedelta(hours=24)]
            
            return {
                'average_completion_time': round(avg_completion_time, 2),
                'success_rate': round(success_rate, 2),
                'total_tasks': len(self.task_history),
                'completed_tasks': len(completed_tasks),
                'task_types': task_types,
                'recent_performance': {
                    'last_24h': len(recent_tasks),
                    'successful_24h': len([t for t in recent_tasks if t.get('status') == 'SUCCESS'])
                }
            }
        except Exception as e:
            logger.error(f"Error calculating task analytics: {e}")
            return {'error': str(e)}
    
    def _update_task_history(self, task_data: Dict):
        """Update task history for analytics."""
        try:
            # Add timestamp if not present
            if 'timestamp' not in task_data:
                task_data['timestamp'] = datetime.now().isoformat()
            
            # Add to history
            self.task_history.append(task_data)
            
            # Maintain history size
            if len(self.task_history) > self.max_history_size:
                self.task_history = self.task_history[-self.max_history_size:]
                
        except Exception as e:
            logger.error(f"Error updating task history: {e}")
    
    def _broadcast_task_updates(self):
        """Broadcast task updates to all connected clients."""
        try:
            task_data = self._get_realtime_task_data()
            self.socketio.emit('task_updates', task_data, room='task_monitoring')
            
            # Update task history for completed tasks
            for task in task_data.get('tasks', []):
                if task.get('status') in ['SUCCESS', 'FAILURE']:
                    self._update_task_history(task)
                    
        except Exception as e:
            logger.error(f"Error broadcasting task updates: {e}")
    
    def _start_realtime_monitoring(self):
        """Start real-time task monitoring."""
        def monitor_tasks():
            while True:
                try:
                    self._broadcast_task_updates()
                    time.sleep(5)  # Update every 5 seconds
                except Exception as e:
                    logger.error(f"Error in real-time monitoring: {e}")
                    time.sleep(10)  # Wait longer on error
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_tasks, daemon=True)
        monitor_thread.start()
        logger.info("Real-time task monitoring started")
    
    def _render_dashboard(self) -> str:
        """Render the integrated dashboard HTML."""
        import json
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Integrated VOD Processing Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .nav-tabs {{
            display: flex;
            background: white;
            border-radius: 10px 10px 0 0;
            overflow: hidden;
            margin-bottom: 0;
        }}
        .nav-tab {{
            flex: 1;
            padding: 15px;
            text-align: center;
            background: #f8f9fa;
            border: none;
            cursor: pointer;
            transition: background 0.3s;
        }}
        .nav-tab.active {{
            background: white;
            font-weight: bold;
        }}
        .nav-tab:hover {{
            background: #e9ecef;
        }}
        .tab-content {{
            background: white;
            padding: 20px;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            min-height: 600px;
        }}
        .tab-pane {{
            display: none;
        }}
        .tab-pane.active {{
            display: block;
        }}
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .status-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .status-card h3 {{
            margin-top: 0;
            color: #333;
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        .status-healthy {{ background-color: #28a745; }}
        .status-degraded {{ background-color: #ffc107; }}
        .status-unhealthy {{ background-color: #dc3545; }}
        
        /* Real-time Task Monitoring Styles */
        .realtime-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        
        .task-filters {{
            display: flex;
            gap: 10px;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .filter-btn.active {{
            background: #007bff;
            color: white;
            border-color: #007bff;
        }}
        
        .connection-status {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .task-summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .summary-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .summary-value {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        
        .realtime-tasks-container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .task-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #eee;
            transition: background 0.3s;
        }}
        
        .task-item:hover {{
            background: #f8f9fa;
        }}
        
        .task-info {{
            flex: 1;
        }}
        
        .task-name {{
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .task-details {{
            font-size: 0.9em;
            color: #666;
        }}
        
        .task-progress {{
            width: 200px;
            margin: 0 15px;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #007bff, #0056b3);
            transition: width 0.3s;
        }}
        
        .task-status {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        
        .status-active {{ background: #d4edda; color: #155724; }}
        .status-reserved {{ background: #fff3cd; color: #856404; }}
        .status-queued {{ background: #d1ecf1; color: #0c5460; }}
        .status-success {{ background: #d4edda; color: #155724; }}
        .status-failure {{ background: #f8d7da; color: #721c24; }}
        
        .task-analytics {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .analytics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        
        .analytics-card {{
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 6px;
            text-align: center;
        }}
        
        .analytics-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #007bff;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        .refresh-button {{
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 20px;
        }}
        .refresh-button:hover {{
            background: #5a6fd8;
        }}
        .task-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .task-table th, .task-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .task-table th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .task-table tr:hover {{
            background-color: #f5f5f5;
        }}
        .action-button {{
            background: #007bff;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
            cursor: pointer;
            margin: 2px;
            font-size: 12px;
        }}
        .action-button:hover {{
            background: #0056b3;
        }}
        .action-button.danger {{
            background: #dc3545;
        }}
        .action-button.danger:hover {{
            background: #c82333;
        }}
        .action-button.warning {{
            background: #ffc107;
            color: #333;
        }}
        .action-button.warning:hover {{
            background: #e0a800;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Integrated VOD Processing Monitor</h1>
            <p>Unified monitoring for VOD processing, queue management, and system health</p>
            <button class="refresh-button" onclick="refreshAllData()">🔄 Refresh All</button>
        </div>
        
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="showTab('overview')">📊 Overview</button>
            <button class="nav-tab" onclick="showTab('realtime')">⚡ Real-time Tasks</button>
            <button class="nav-tab" onclick="showTab('queue')">📋 Queue Management</button>
            <button class="nav-tab" onclick="showTab('celery')">⚡ Celery Tasks</button>
            <button class="nav-tab" onclick="showTab('health')">🏥 Health Checks</button>
            <button class="nav-tab" onclick="showTab('metrics')">📈 Metrics</button>
        </div>
        
        <div class="tab-content">
            <!-- Overview Tab -->
            <div id="overview" class="tab-pane active">
                <div class="status-grid">
                    <div class="status-card">
                        <h3>💻 System Health</h3>
                        <div id="system-health">Loading...</div>
                    </div>
                    <div class="status-card">
                        <h3>📋 Queue Status</h3>
                        <div id="queue-overview">Loading...</div>
                    </div>
                    <div class="status-card">
                        <h3>⚡ Celery Workers</h3>
                        <div id="celery-overview">Loading...</div>
                    </div>
                    <div class="status-card">
                        <h3>📈 Recent Activity</h3>
                        <div id="recent-activity">Loading...</div>
                    </div>
                </div>
            </div>
            
            <!-- Real-time Tasks Tab -->
            <div id="realtime" class="tab-pane">
                <div class="realtime-header">
                    <h2>⚡ Real-time Task Monitoring</h2>
                    <div class="task-filters">
                        <button class="filter-btn active" onclick="filterTasks('all')">All Tasks</button>
                        <button class="filter-btn" onclick="filterTasks('vod')">VOD Processing</button>
                        <button class="filter-btn" onclick="filterTasks('transcription')">Transcription</button>
                        <button class="filter-btn" onclick="filterTasks('cleanup')">Cleanup</button>
                    </div>
                    <div class="connection-status">
                        <span id="socket-status" class="status-indicator status-unhealthy"></span>
                        <span id="socket-text">Disconnected</span>
                    </div>
                </div>
                
                <div class="task-summary">
                    <div class="summary-card">
                        <h3>Total Tasks</h3>
                        <div id="total-tasks" class="summary-value">0</div>
                    </div>
                    <div class="summary-card">
                        <h3>Active</h3>
                        <div id="active-tasks" class="summary-value">0</div>
                    </div>
                    <div class="summary-card">
                        <h3>Reserved</h3>
                        <div id="reserved-tasks" class="summary-value">0</div>
                    </div>
                    <div class="summary-card">
                        <h3>Queued</h3>
                        <div id="queued-tasks" class="summary-value">0</div>
                    </div>
                </div>
                
                <div class="realtime-tasks-container">
                    <div id="realtime-tasks-list">Loading real-time tasks...</div>
                </div>
                
                <div class="task-analytics">
                    <h3>Task Performance Analytics</h3>
                    <div id="task-analytics-data">Loading analytics...</div>
                </div>
            </div>
            
            <!-- Queue Management Tab -->
            <div id="queue" class="tab-pane">
                <h2>Queue Management</h2>
                <div id="queue-jobs">Loading...</div>
            </div>
            
            <!-- Celery Tasks Tab -->
            <div id="celery" class="tab-pane">
                <h2>Celery Task Management</h2>
                <div id="celery-tasks">Loading...</div>
            </div>
            
            <!-- Health Checks Tab -->
            <div id="health" class="tab-pane">
                <h2>System Health Checks</h2>
                <div id="health-checks">Loading...</div>
            </div>
            
            <!-- Metrics Tab -->
            <div id="metrics" class="tab-pane">
                <h2>Performance Metrics</h2>
                <div id="performance-metrics">Loading...</div>
            </div>
        </div>
    </div>

    <script>
        let currentTab = 'overview';
        
        function showTab(tabName) {{
            // Hide all tab panes
            document.querySelectorAll('.tab-pane').forEach(pane => {{
                pane.classList.remove('active');
            }});
            
            // Remove active class from all tabs
            document.querySelectorAll('.nav-tab').forEach(tab => {{
                tab.classList.remove('active');
            }});
            
            // Show selected tab pane
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to selected tab
            event.target.classList.add('active');
            
            currentTab = tabName;
            
            // Refresh data for the selected tab
            refreshTabData(tabName);
        }}
        
        function refreshAllData() {{
            refreshTabData(currentTab);
        }}
        
        function refreshTabData(tabName) {{
            switch(tabName) {{
                case 'overview':
                    refreshOverviewData();
                    break;
                case 'realtime':
                    refreshRealtimeData();
                    break;
                case 'queue':
                    refreshQueueData();
                    break;
                case 'celery':
                    refreshCeleryData();
                    break;
                case 'health':
                    refreshHealthData();
                    break;
                case 'metrics':
                    refreshMetricsData();
                    break;
            }}
        }}
        
        // SocketIO connection and real-time task monitoring
        let socket = null;
        let currentTaskFilter = 'all';
        
        function initializeSocketIO() {{
            socket = io();
            
            socket.on('connect', function() {{
                console.log('Connected to SocketIO server');
                updateSocketStatus(true);
                socket.emit('join_task_monitoring');
            }});
            
            socket.on('disconnect', function() {{
                console.log('Disconnected from SocketIO server');
                updateSocketStatus(false);
            }});
            
            socket.on('task_updates', function(data) {{
                updateRealtimeTasks(data);
            }});
            
            socket.on('filtered_tasks', function(data) {{
                updateRealtimeTasks(data);
            }});
            
            socket.on('system_metrics', function(data) {{
                updateSystemHealth(data);
            }});
            
            socket.on('error', function(data) {{
                console.error('SocketIO error:', data);
            }});
        }}
        
        function updateSocketStatus(connected) {{
            const statusIndicator = document.getElementById('socket-status');
            const statusText = document.getElementById('socket-text');
            
            if (connected) {{
                statusIndicator.className = 'status-indicator status-healthy';
                statusText.textContent = 'Connected';
            }} else {{
                statusIndicator.className = 'status-indicator status-unhealthy';
                statusText.textContent = 'Disconnected';
            }}
        }}
        
        function refreshRealtimeData() {{
            // Load initial real-time data
            fetch('/api/tasks/realtime')
                .then(response => response.json())
                .then(data => {{
                    updateRealtimeTasks(data);
                }});
            
            // Load task analytics
            fetch('/api/tasks/analytics')
                .then(response => response.json())
                .then(data => {{
                    updateTaskAnalytics(data);
                }});
        }}
        
        function updateRealtimeTasks(data) {{
            if (data.error) {{
                document.getElementById('realtime-tasks-list').innerHTML = 
                    `<div style="color: red; padding: 20px;">Error: ${{data.error}}</div>`;
                return;
            }}
            
            // Update summary values
            const summary = data.summary || {{}};
            document.getElementById('total-tasks').textContent = summary.total || 0;
            document.getElementById('active-tasks').textContent = summary.active || 0;
            document.getElementById('reserved-tasks').textContent = summary.reserved || 0;
            document.getElementById('queued-tasks').textContent = summary.queued || 0;
            
            // Update task list
            const tasks = data.tasks || [];
            const tasksContainer = document.getElementById('realtime-tasks-list');
            
            if (tasks.length === 0) {{
                tasksContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">No tasks found</div>';
                return;
            }}
            
            let html = '';
            tasks.forEach(task => {{
                const statusClass = `status-${{task.status}}`;
                const progressPercent = task.progress || 0;
                const duration = task.duration ? Math.round(task.duration) : 0;
                
                html += `
                    <div class="task-item">
                        <div class="task-info">
                            <div class="task-name">${{task.name}}</div>
                            <div class="task-details">
                                ID: ${{task.id}} | Type: ${{task.type}} | Worker: ${{task.worker || 'N/A'}} | Duration: ${{duration}}s
                                ${{task.video_path ? '| File: ' + task.video_path : ''}}
                            </div>
                        </div>
                        <div class="task-progress">
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${{progressPercent}}%"></div>
                            </div>
                            <div style="text-align: center; font-size: 0.8em; margin-top: 2px;">${{progressPercent}}%</div>
                        </div>
                        <span class="task-status ${{statusClass}}">${{task.status}}</span>
                    </div>
                `;
            }});
            
            tasksContainer.innerHTML = html;
        }}
        
        function updateTaskAnalytics(data) {{
            if (data.error) {{
                document.getElementById('task-analytics-data').innerHTML = 
                    `<div style="color: red;">Error: ${{data.error}}</div>`;
                return;
            }}
            
            const analyticsContainer = document.getElementById('task-analytics-data');
            let html = '<div class="analytics-grid">';
            
            html += `
                <div class="analytics-card">
                    <div class="analytics-value">${{data.average_completion_time || 0}}s</div>
                    <div>Average Completion Time</div>
                </div>
                <div class="analytics-card">
                    <div class="analytics-value">${{data.success_rate || 0}}%</div>
                    <div>Success Rate</div>
                </div>
                <div class="analytics-card">
                    <div class="analytics-value">${{data.total_tasks || 0}}</div>
                    <div>Total Tasks</div>
                </div>
                <div class="analytics-card">
                    <div class="analytics-value">${{data.completed_tasks || 0}}</div>
                    <div>Completed Tasks</div>
                </div>
                <div class="analytics-card">
                    <div class="analytics-value">${{data.recent_performance?.last_24h || 0}}</div>
                    <div>Tasks (24h)</div>
                </div>
                <div class="analytics-card">
                    <div class="analytics-value">${{data.recent_performance?.successful_24h || 0}}</div>
                    <div>Successful (24h)</div>
                </div>
            `;
            
            html += '</div>';
            
            // Add task type distribution
            if (data.task_types && Object.keys(data.task_types).length > 0) {{
                html += '<h4 style="margin-top: 20px;">Task Type Distribution</h4><div class="analytics-grid">';
                Object.entries(data.task_types).forEach(([type, count]) => {{
                    html += `
                        <div class="analytics-card">
                            <div class="analytics-value">${{count}}</div>
                            <div>${{type.charAt(0).toUpperCase() + type.slice(1)}}</div>
                        </div>
                    `;
                }});
                html += '</div>';
            }}
            
            analyticsContainer.innerHTML = html;
        }}
        
        function filterTasks(taskType) {{
            currentTaskFilter = taskType;
            
            // Update filter button states
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');
            
            // Request filtered data from server
            if (socket && socket.connected) {{
                socket.emit('filter_tasks', {{ type: taskType }});
            }} else {{
                // Fallback to HTTP request
                fetch(`/api/tasks/realtime?filter=${{taskType}}`)
                    .then(response => response.json())
                    .then(data => {{
                        updateRealtimeTasks(data);
                    }});
            }}
        }}
        
        function refreshOverviewData() {{
            // Load system health
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {{
                    updateSystemHealth(data);
                }});
            
            // Load queue overview
            fetch('/api/queue/jobs')
                .then(response => response.json())
                .then(data => {{
                    updateQueueOverview(data);
                }});
            
            // Load Celery overview
            fetch('/api/celery/workers')
                .then(response => response.json())
                .then(data => {{
                    updateCeleryOverview(data);
                }});
            
            // Load recent activity
            fetch('/api/unified/tasks')
                .then(response => response.json())
                .then(data => {{
                    updateRecentActivity(data);
                }});
        }}
        
        function refreshQueueData() {{
            fetch('/api/queue/jobs')
                .then(response => response.json())
                .then(data => {{
                    updateQueueJobs(data);
                }});
        }}
        
        function refreshCeleryData() {{
            fetch('/api/celery/tasks')
                .then(response => response.json())
                .then(data => {{
                    updateCeleryTasks(data);
                }});
        }}
        
        function refreshHealthData() {{
            fetch('/api/health')
                .then(response => response.json())
                .then(data => {{
                    updateHealthChecks(data);
                }});
        }}
        
        function refreshMetricsData() {{
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => {{
                    updatePerformanceMetrics(data);
                }});
        }}
        
        function updateSystemHealth(data) {{
            const div = document.getElementById('system-health');
            const overallStatus = data.system?.overall_status || 'unknown';
            const statusClass = overallStatus === 'healthy' ? 'healthy' : 
                              overallStatus === 'degraded' ? 'degraded' : 'unhealthy';
            
            div.innerHTML = `
                <div><span class="status-indicator status-${{statusClass}}"></span>Overall: ${{overallStatus.toUpperCase()}}</div>
                <div>CPU: ${{data.system?.cpu_percent || 0}}%</div>
                <div>Memory: ${{data.system?.memory_percent || 0}}%</div>
                <div>Disk: ${{data.system?.disk_percent || 0}}%</div>
                <div>Redis: ${{data.redis?.status || 'Disconnected'}}</div>
                <div>Celery Workers: ${{data.celery?.active_workers?.length || 0}} active</div>
            `;
        }}
        
        function updateQueueOverview(data) {{
            const div = document.getElementById('queue-overview');
            const summary = data.summary || {{}};
            
            div.innerHTML = `
                <div class="metric-value">${{data.total || 0}}</div>
                <div class="metric-label">Total Jobs</div>
                <div>Queued: ${{summary.queued || 0}}</div>
                <div>Started: ${{summary.started || 0}}</div>
                <div>Finished: ${{summary.finished || 0}}</div>
                <div>Failed: ${{summary.failed || 0}}</div>
            `;
        }}
        
        function updateCeleryOverview(data) {{
            const div = document.getElementById('celery-overview');
            const summary = data.summary || {{}};
            
            div.innerHTML = `
                <div class="metric-value">${{summary.active_workers || 0}}</div>
                <div class="metric-label">Active Workers</div>
                <div>Total Workers: ${{summary.total_workers || 0}}</div>
                <div>Status: ${{summary.worker_status || 'unknown'}}</div>
            `;
        }}
        
        function updateRecentActivity(data) {{
            const div = document.getElementById('recent-activity');
            const tasks = data.tasks || [];
            const summary = data.summary || {{}};
            
            let html = `
                <div class="metric-value">${{summary.total || 0}}</div>
                <div class="metric-label">Total Tasks</div>
                <div>RQ Jobs: ${{summary.rq_count || 0}}</div>
                <div>Celery Active: ${{summary.celery_active || 0}}</div>
                <div>Celery Reserved: ${{summary.celery_reserved || 0}}</div>
            `;
            
            if (tasks.length > 0) {{
                html += '<div style="margin-top: 15px;"><strong>Recent Tasks:</strong></div>';
                tasks.slice(0, 5).forEach(task => {{
                    const statusClass = task.status === 'finished' ? 'healthy' : 
                                      task.status === 'failed' ? 'unhealthy' : 'degraded';
                    html += `
                        <div style="margin: 5px 0; padding: 5px; border-bottom: 1px solid #eee;">
                            <div><strong>${{task.name}}</strong> (${{task.type}})</div>
                            <div>Status: <span class="status-indicator status-${{statusClass}}"></span>${{task.status}}</div>
                        </div>
                    `;
                }});
            }}
            
            div.innerHTML = html;
        }}
        
        function updateQueueJobs(data) {{
            const div = document.getElementById('queue-jobs');
            const jobs = data.jobs || [];
            
            if (jobs.length === 0) {{
                div.innerHTML = '<p>No jobs in queue</p>';
                return;
            }}
            
            let html = `
                <table class="task-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Status</th>
                            <th>Progress</th>
                            <th>Video Path</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            jobs.forEach(job => {{
                const statusClass = job.status === 'finished' ? 'healthy' : 
                                  job.status === 'failed' ? 'unhealthy' : 'degraded';
                const progress = job.progress || 0;
                
                html += `
                    <tr>
                        <td>${{job.id}}</td>
                        <td><span class="status-indicator status-${{statusClass}}"></span>${{job.status}}</td>
                        <td>${{progress}}%</td>
                        <td>${{job.video_path || 'N/A'}}</td>
                        <td>${{new Date(job.created_at).toLocaleString()}}</td>
                        <td>
                            ${{job.status === 'queued' ? '<button class="action-button" onclick="stopJob(\'' + job.id + '\')">Stop</button>' : ''}}
                            ${{job.status === 'started' ? '<button class="action-button warning" onclick="pauseJob(\'' + job.id + '\')">Pause</button>' : ''}}
                            ${{job.status === 'paused' ? '<button class="action-button" onclick="resumeJob(\'' + job.id + '\')">Resume</button>' : ''}}
                            <button class="action-button danger" onclick="removeJob(\'' + job.id + '\')">Remove</button>
                        </td>
                    </tr>
                `;
            }});
            
            html += '</tbody></table>';
            div.innerHTML = html;
        }}
        
        function updateCeleryTasks(data) {{
            const div = document.getElementById('celery-tasks');
            const summary = data.summary || {{}};
            
            let html = `
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">${{summary.total_tasks || 0}}</div>
                        <div class="metric-label">Total Tasks</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${{summary.active_tasks || 0}}</div>
                        <div class="metric-label">Active Tasks</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${{summary.reserved_tasks || 0}}</div>
                        <div class="metric-label">Reserved Tasks</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${{summary.worker_count || 0}}</div>
                        <div class="metric-label">Workers</div>
                    </div>
                </div>
            `;
            
            if (data.active) {{
                html += '<h3>Active Tasks</h3>';
                Object.entries(data.active).forEach(([worker, tasks]) => {{
                    html += `<h4>Worker: ${{worker}}</h4>`;
                    if (tasks.length > 0) {{
                        html += '<table class="task-table"><thead><tr><th>Task ID</th><th>Name</th><th>Started</th></tr></thead><tbody>';
                        tasks.forEach(task => {{
                            html += `
                                <tr>
                                    <td>${{task.id}}</td>
                                    <td>${{task.name}}</td>
                                    <td>${{new Date(task.time_start * 1000).toLocaleString()}}</td>
                                </tr>
                            `;
                        }});
                        html += '</tbody></table>';
                    }} else {{
                        html += '<p>No active tasks</p>';
                    }}
                }});
            }}
            
            div.innerHTML = html;
        }}
        
        function updateHealthChecks(data) {{
            const div = document.getElementById('health-checks');
            const checks = data.checks || {{}};
            
            let html = '';
            Object.entries(checks).forEach(([category, categoryChecks]) => {{
                html += `<h3>${{category.charAt(0).toUpperCase() + category.slice(1)}} Health</h3>`;
                if (Array.isArray(categoryChecks)) {{
                    categoryChecks.forEach(check => {{
                        const statusClass = check.status === 'healthy' ? 'healthy' : 
                                          check.status === 'degraded' ? 'degraded' : 'unhealthy';
                        html += `
                            <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                                <div><strong>${{check.name}}</strong> <span class="status-indicator status-${{statusClass}}"></span>${{check.status}}</div>
                                <div>${{check.message || ''}}</div>
                                ${{check.details ? '<div><small>Details: ' + JSON.stringify(check.details) + '</small></div>' : ''}}
                            </div>
                        `;
                    }});
                }}
            }});
            
            div.innerHTML = html;
        }}
        
        function updatePerformanceMetrics(data) {{
            const div = document.getElementById('performance-metrics');
            
            let html = '<div class="metrics-grid">';
            Object.entries(data.counters || {{}}).forEach(([name, value]) => {{
                html += `
                    <div class="metric-card">
                        <div class="metric-value">${{value}}</div>
                        <div class="metric-label">${{name}}</div>
                    </div>
                `;
            }});
            html += '</div>';
            
            if (data.timers && Object.keys(data.timers).length > 0) {{
                html += '<h3>Performance Timers</h3><div class="metrics-grid">';
                Object.entries(data.timers).forEach(([name, stats]) => {{
                    html += `
                        <div class="metric-card">
                            <div class="metric-value">${{stats.avg ? stats.avg.toFixed(2) : 0}}ms</div>
                            <div class="metric-label">${{name}} (avg)</div>
                            <div>Min: ${{stats.min || 0}}ms</div>
                            <div>Max: ${{stats.max || 0}}ms</div>
                        </div>
                    `;
                }});
                html += '</div>';
            }}
            
            div.innerHTML = html;
        }}
        
        // Queue management functions
        function stopJob(jobId) {{
            fetch(`/api/queue/jobs/${{jobId}}/stop`, {{method: 'POST'}})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        refreshQueueData();
                    }} else {{
                        alert('Failed to stop job');
                    }}
                }});
        }}
        
        function pauseJob(jobId) {{
            fetch(`/api/queue/jobs/${{jobId}}/pause`, {{method: 'POST'}})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        refreshQueueData();
                    }} else {{
                        alert('Failed to pause job');
                    }}
                }});
        }}
        
        function resumeJob(jobId) {{
            fetch(`/api/queue/jobs/${{jobId}}/resume`, {{method: 'POST'}})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        refreshQueueData();
                    }} else {{
                        alert('Failed to resume job');
                    }}
                }});
        }}
        
        function removeJob(jobId) {{
            if (confirm('Are you sure you want to remove this job?')) {{
                fetch(`/api/queue/jobs/${{jobId}}/remove`, {{method: 'DELETE'}})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            refreshQueueData();
                        }} else {{
                            alert('Failed to remove job');
                        }}
                    }});
            }}
        }}
        
        // Initial load
        refreshOverviewData();
        
        // Initialize SocketIO for real-time monitoring
        initializeSocketIO();
        
        // Auto-refresh every 30 seconds
        setInterval(() => refreshTabData(currentTab), 30000);
    </script>
    <div class='manual-controls' style='margin-bottom: 20px;'>
        <h2>Manual Task Controls</h2>
        <button onclick="triggerVODProcessing()">🎬 Trigger VOD Processing</button>
        <button onclick="showTranscriptionDialog()">🎤 Trigger Transcription</button>
    </div>
    <div id="transcription-dialog" style="display:none; position:fixed; top:30%; left:50%; transform:translate(-50%,-50%); background:white; border:1px solid #ccc; padding:20px; z-index:1000;">
        <h3>Trigger Transcription</h3>
        <input type="text" id="transcription-file-path" placeholder="Enter file path..." style="width:300px;" />
        <button onclick="triggerTranscription()">Start</button>
        <button onclick="closeTranscriptionDialog()">Cancel</button>
    </div>
    <script>
        function triggerVODProcessing() {{
            fetch('/api/tasks/trigger_vod_processing', {{method: 'POST'}})
                .then(response => response.json())
                .then(data => {{
                    alert(data.message || (data.success ? 'Triggered!' : 'Failed: ' + data.error));
                }});
        }}
        function showTranscriptionDialog() {{
            document.getElementById('transcription-dialog').style.display = 'block';
        }}
        function closeTranscriptionDialog() {{
            document.getElementById('transcription-dialog').style.display = 'none';
        }}
        function triggerTranscription() {{
            const filePath = document.getElementById('transcription-file-path').value;
            fetch('/api/tasks/trigger_transcription', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{file_path: filePath}})
            }})
            .then(response => response.json())
            .then(data => {{
                alert(data.message || (data.success ? 'Triggered!' : 'Failed: ' + data.error));
                closeTranscriptionDialog();
            }});
        }}
    </script>
</body>
</html>
        """
    
    def _start_background_collection(self):
        """Start background metrics collection."""
        def background_collector():
            while True:
                try:
                    # Collect metrics every 30 seconds
                    self.metrics_collector.collect_system_metrics()
                    time.sleep(30)
                except Exception as e:
                    logger.error(f"Background metrics collection error: {e}")
                    time.sleep(60)
    
    def run(self):
        """Run the dashboard server with SocketIO support."""
        logger.info(f"Starting integrated monitoring dashboard with SocketIO on {self.host}:{self.port}")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=False, allow_unsafe_werkzeug=True)

def start_integrated_dashboard(host: str = "0.0.0.0", port: int = 5051):
    """Start the integrated monitoring dashboard."""
    dashboard = IntegratedDashboard(host, port)
    dashboard.run()

if __name__ == "__main__":
    start_integrated_dashboard() 