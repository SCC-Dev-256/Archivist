"""
Production-Grade VOD Processing Dashboard

This module provides a comprehensive web-based monitoring dashboard that integrates:
- Real-time VOD processing monitoring with SocketIO
- Unified queue management (RQ + Celery) with full CRUD operations
- System health monitoring with Prometheus metrics
- Task performance analytics and historical data
- Manual controls for VOD processing and transcription
- Production-ready architecture with security and scalability

Architecture:
- Flask REST API with Flask-SocketIO for real-time updates
- Service layer pattern for clean separation of concerns
- Redis-backed caching and session management
- PostgreSQL integration for persistent analytics
- Docker-ready deployment configuration
"""

import json
import time
import psutil
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from flask import Flask, render_template, jsonify, request, Blueprint, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading
import os

from loguru import logger
from core.monitoring.metrics import get_metrics_collector
from core.monitoring.health_checks import get_health_manager
from core.task_queue import QueueManager
from core.tasks import celery_app

@dataclass
class DashboardConfig:
    """Configuration for the dashboard."""
    host: str = "0.0.0.0"
    port: int = 5051
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    max_history_size: int = 1000
    refresh_interval: int = 30
    socketio_ping_timeout: int = 60
    socketio_ping_interval: int = 25

class IntegratedDashboard:
    """Production-grade integrated monitoring dashboard with queue management."""
    
    def __init__(self, config: Optional[DashboardConfig] = None):
        self.config = config or DashboardConfig()
        self.host = self.config.host
        self.port = self.config.port
        
        # Initialize Flask app with production settings
        self.app = Flask(__name__)
        self.app.config.update({
            'SECRET_KEY': os.environ.get('DASHBOARD_SECRET_KEY', 'archivist-integrated-dashboard-2025'),
            'SESSION_COOKIE_SECURE': True,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': timedelta(hours=24)
        })
        
        # Initialize rate limiting
        self.limiter = Limiter(
            app=self.app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"]
        )
        
        # Initialize SocketIO with production settings
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins="*",
            async_mode='threading',
            ping_timeout=self.config.socketio_ping_timeout,
            ping_interval=self.config.socketio_ping_interval,
            logger=True,
            engineio_logger=True
        )
        
        # Initialize Redis connection
        self.redis_client = redis.Redis(
            host=self.config.redis_host,
            port=self.config.redis_port,
            db=self.config.redis_db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # Initialize core services
        self.metrics_collector = get_metrics_collector()
        self.health_manager = get_health_manager()
        self.queue_manager = QueueManager()
        
        # Task history storage for analytics
        self.task_history = []
        self.max_history_size = self.config.max_history_size
        
        # Performance tracking
        self.performance_metrics = {
            'api_response_times': {},
            'socket_connections': 0,
            'active_tasks': 0,
            'system_load': 0.0
        }
        
        # Enable CORS with security headers
        CORS(self.app, resources={
            r"/api/*": {"origins": ["http://localhost:3000", "http://localhost:8080"]},
            r"/static/*": {"origins": "*"}
        })
        
        # Register routes and SocketIO events
        self._register_routes()
        self._register_socketio_events()
        self._register_error_handlers()
        
        # Start background services
        self._start_background_collection()
        self._start_realtime_monitoring()
        self._start_performance_monitoring()
        
        logger.info(f"Dashboard initialized with config: {self.config}")
    
    def _start_performance_monitoring(self):
        """Start performance monitoring thread."""
        def monitor_performance():
            while True:
                try:
                    # Update system load
                    self.performance_metrics['system_load'] = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
                    
                    # Update active tasks count
                    inspect = celery_app.control.inspect()
                    active_tasks = inspect.active() if inspect else {}
                    self.performance_metrics['active_tasks'] = sum(len(tasks) for tasks in active_tasks.values())
                    
                    # Store performance metrics in Redis for persistence
                    self.redis_client.hset(
                        'dashboard:performance',
                        mapping={
                            'system_load': self.performance_metrics['system_load'],
                            'active_tasks': self.performance_metrics['active_tasks'],
                            'socket_connections': self.performance_metrics['socket_connections'],
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                    
                    # Update metrics collector
                    self.metrics_collector.gauge('system_load', self.performance_metrics['system_load'])
                    self.metrics_collector.gauge('active_tasks', self.performance_metrics['active_tasks'])
                    
                    time.sleep(30)  # Update every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Error in performance monitoring: {e}")
                    time.sleep(60)  # Wait longer on error
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_performance, daemon=True)
        monitor_thread.start()
        logger.info("Performance monitoring started")
    
    def _register_socketio_events(self):
        """Register SocketIO event handlers for real-time updates."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            self.performance_metrics['socket_connections'] += 1
            logger.info(f"Client connected: {request.sid} (Total: {self.performance_metrics['socket_connections']})")
            self.metrics_collector.increment('socket_connections')
            emit('connected', {
                'status': 'connected', 
                'timestamp': datetime.now().isoformat(),
                'client_id': request.sid
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            self.performance_metrics['socket_connections'] = max(0, self.performance_metrics['socket_connections'] - 1)
            logger.info(f"Client disconnected: {request.sid} (Total: {self.performance_metrics['socket_connections']})")
            self.metrics_collector.increment('socket_disconnections')
        
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
            """Send comprehensive system metrics to client."""
            try:
                start_time = time.time()
                
                # System metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                network = psutil.net_io_counters()
                
                # Celery metrics
                inspect = celery_app.control.inspect()
                active_workers = inspect.stats() if inspect else {}
                active_tasks = inspect.active() if inspect else {}
                reserved_tasks = inspect.reserved() if inspect else {}
                
                # Redis metrics
                try:
                    redis_info = self.redis_client.info()
                    redis_status = {
                        'status': 'connected',
                        'version': redis_info.get('redis_version', 'unknown'),
                        'connected_clients': redis_info.get('connected_clients', 0),
                        'used_memory_human': redis_info.get('used_memory_human', 'unknown'),
                        'total_commands_processed': redis_info.get('total_commands_processed', 0),
                        'keyspace_hits': redis_info.get('keyspace_hits', 0),
                        'keyspace_misses': redis_info.get('keyspace_misses', 0)
                    }
                except Exception as e:
                    redis_status = {'status': 'disconnected', 'error': str(e)}
                
                # Performance metrics
                response_time = time.time() - start_time
                self.performance_metrics['api_response_times']['system_metrics'] = response_time
                
                metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'system': {
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'memory_available_gb': round(memory.available / (1024**3), 2),
                        'memory_used_gb': round(memory.used / (1024**3), 2),
                        'disk_percent': disk.percent,
                        'disk_free_gb': round(disk.free / (1024**3), 2),
                        'disk_used_gb': round(disk.used / (1024**3), 2),
                        'network_bytes_sent': network.bytes_sent,
                        'network_bytes_recv': network.bytes_recv,
                        'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
                    },
                    'celery': {
                        'active_workers': list(active_workers.keys()) if active_workers else [],
                        'worker_count': len(active_workers) if active_workers else 0,
                        'active_tasks': sum(len(tasks) for tasks in active_tasks.values()),
                        'reserved_tasks': sum(len(tasks) for tasks in reserved_tasks.values()),
                        'total_tasks': sum(len(tasks) for tasks in active_tasks.values()) + 
                                     sum(len(tasks) for tasks in reserved_tasks.values())
                    },
                    'redis': redis_status,
                    'dashboard': {
                        'socket_connections': self.performance_metrics['socket_connections'],
                        'active_tasks': self.performance_metrics['active_tasks'],
                        'response_time_ms': round(response_time * 1000, 2)
                    }
                }
                
                emit('system_metrics', metrics)
                self.metrics_collector.increment('system_metrics_requests')
                
            except Exception as e:
                logger.error(f"Error sending system metrics: {e}")
                emit('error', {'message': str(e)})
                self.metrics_collector.increment('system_metrics_errors')
    
    def _register_error_handlers(self):
        """Register error handlers for production-grade error handling."""
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                'error': 'Resource not found',
                'message': 'The requested resource does not exist',
                'status_code': 404
            }), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            logger.error(f"Internal server error: {error}")
            return jsonify({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred',
                'status_code': 500
            }), 500
        
        @self.app.errorhandler(429)
        def rate_limit_exceeded(error):
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests, please try again later',
                'status_code': 429
            }), 429
    
    def _register_routes(self):
        """Register all dashboard routes."""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page."""
            return self._render_dashboard()
        
        @self.app.route('/favicon.ico')
        def favicon():
            """Serve favicon to prevent 404 errors."""
            from flask import Response
            # Return a minimal 1x1 transparent PNG
            import base64
            favicon_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
            return Response(favicon_data, mimetype='image/x-icon')
        
        @self.app.route('/static/dashboard.css')
        def dashboard_css():
            """Serve the dashboard CSS file."""
            return self._render_dashboard_css()
        
        @self.app.route('/static/dashboard.js')
        def dashboard_js():
            """Serve the dashboard JavaScript file."""
            return self._render_dashboard_js()
        
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
                if success:
                    self.metrics_collector.increment('queue_jobs_removed')
                    logger.info(f"Job {job_id} removed from queue")
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error removing job {job_id}: {e}")
                self.metrics_collector.increment('queue_operation_errors')
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/retry', methods=['POST'])
        def api_queue_retry_job(job_id):
            """Retry a failed job."""
            try:
                success = self.queue_manager.retry_job(job_id)
                if success:
                    self.metrics_collector.increment('queue_jobs_retried')
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error retrying job {job_id}: {e}")
                self.metrics_collector.increment('queue_operation_errors')
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/cancel', methods=['POST'])
        def api_queue_cancel_job(job_id):
            """Cancel a running job."""
            try:
                success = self.queue_manager.cancel_job(job_id)
                if success:
                    self.metrics_collector.increment('queue_jobs_cancelled')
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error cancelling job {job_id}: {e}")
                self.metrics_collector.increment('queue_operation_errors')
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/stats')
        def api_queue_stats():
            """Get comprehensive queue statistics."""
            try:
                jobs = self.queue_manager.get_all_jobs()
                stats = {
                    'total_jobs': len(jobs),
                    'status_counts': self._count_job_statuses(jobs),
                    'average_wait_time': self._calculate_average_wait_time(jobs),
                    'success_rate': self._calculate_success_rate(jobs),
                    'recent_activity': self._get_recent_queue_activity(),
                    'performance_metrics': {
                        'jobs_per_hour': self._calculate_jobs_per_hour(),
                        'average_processing_time': self._calculate_average_processing_time(jobs)
                    }
                }
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Error getting queue stats: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/cleanup', methods=['POST'])
        def api_queue_cleanup():
            """Clean up completed and failed jobs."""
            try:
                data = request.get_json() or {}
                max_age_hours = data.get('max_age_hours', 24)
                success = self.queue_manager.cleanup_old_jobs(max_age_hours)
                if success:
                    self.metrics_collector.increment('queue_cleanup_operations')
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error cleaning up queue: {e}")
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
    
    def _calculate_average_wait_time(self, jobs: List[Dict]) -> float:
        """Calculate average wait time for jobs."""
        try:
            wait_times = []
            for job in jobs:
                if job.get('created_at') and job.get('started_at'):
                    wait_time = (job['started_at'] - job['created_at']).total_seconds()
                    wait_times.append(wait_time)
            
            return sum(wait_times) / len(wait_times) if wait_times else 0.0
        except Exception as e:
            logger.error(f"Error calculating average wait time: {e}")
            return 0.0
    
    def _calculate_success_rate(self, jobs: List[Dict]) -> float:
        """Calculate success rate of completed jobs."""
        try:
            completed_jobs = [j for j in jobs if j.get('status') in ['finished', 'failed']]
            if not completed_jobs:
                return 0.0
            
            successful_jobs = [j for j in completed_jobs if j.get('status') == 'finished']
            return (len(successful_jobs) / len(completed_jobs)) * 100
        except Exception as e:
            logger.error(f"Error calculating success rate: {e}")
            return 0.0
    
    def _get_recent_queue_activity(self) -> Dict[str, Any]:
        """Get recent queue activity for the last 24 hours."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_jobs = [j for j in self.task_history 
                          if j.get('timestamp') and 
                          datetime.fromisoformat(j['timestamp']) > cutoff_time]
            
            return {
                'jobs_created': len([j for j in recent_jobs if j.get('action') == 'created']),
                'jobs_completed': len([j for j in recent_jobs if j.get('action') == 'completed']),
                'jobs_failed': len([j for j in recent_jobs if j.get('action') == 'failed']),
                'average_processing_time': self._calculate_average_processing_time(recent_jobs)
            }
        except Exception as e:
            logger.error(f"Error getting recent queue activity: {e}")
            return {}
    
    def _calculate_jobs_per_hour(self) -> float:
        """Calculate jobs processed per hour."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=1)
            recent_jobs = [j for j in self.task_history 
                          if j.get('timestamp') and 
                          datetime.fromisoformat(j['timestamp']) > cutoff_time]
            
            return len(recent_jobs)
        except Exception as e:
            logger.error(f"Error calculating jobs per hour: {e}")
            return 0.0
    
    def _calculate_average_processing_time(self, jobs: List[Dict]) -> float:
        """Calculate average processing time for jobs."""
        try:
            processing_times = []
            for job in jobs:
                if job.get('started_at') and job.get('ended_at'):
                    processing_time = (job['ended_at'] - job['started_at']).total_seconds()
                    processing_times.append(processing_time)
            
            return sum(processing_times) / len(processing_times) if processing_times else 0.0
        except Exception as e:
            logger.error(f"Error calculating average processing time: {e}")
            return 0.0
    
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
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Integrated VOD Processing Monitor</title>
    <link rel="icon" type="image/png" href="/favicon.ico">
    <link rel="stylesheet" href="/static/dashboard.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
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
            <button class="nav-tab" onclick="showTab('controls')">🎮 Manual Controls</button>
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
                <div id="metrics-data">Loading...</div>
            </div>
            
            <!-- Manual Controls Tab -->
            <div id="controls" class="tab-pane">
                <h2>🎮 Manual Controls</h2>
                <div class="controls-grid">
                    <div class="control-card">
                        <h3>VOD Processing</h3>
                        <p>Trigger manual VOD processing for a specific file</p>
                        <button onclick="openVODDialog()" class="control-btn">🚀 Trigger VOD Processing</button>
                    </div>
                    <div class="control-card">
                        <h3>Transcription</h3>
                        <p>Start transcription for a video file</p>
                        <button onclick="openTranscriptionDialog()" class="control-btn">🎤 Trigger Transcription</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- VOD Processing Dialog -->
    <div id="vod-dialog" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>VOD Processing</h3>
                <span class="close" onclick="closeVODDialog()">&times;</span>
            </div>
            <div class="modal-body">
                <p class="vod-dialog p">Enter the full path to the video file you want to process:</p>
                <input type="text" id="vod-file-path" placeholder="e.g., /path/to/video.mp4" />
                <div class="dialog-buttons">
                    <button onclick="closeVODDialog()" class="cancel-btn">
                        Cancel
                    </button>
                    <button onclick="triggerVODProcessing()" class="start-btn">
                        Start Processing
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Transcription Dialog -->
    <div id="transcription-dialog" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Transcription</h3>
                <span class="close" onclick="closeTranscriptionDialog()">&times;</span>
            </div>
            <div class="modal-body">
                <p class="transcription-dialog p">Enter the full path to the video file you want to transcribe:</p>
                <input type="text" id="transcription-file-path" placeholder="e.g., /path/to/video.mp4" />
                <div class="dialog-buttons">
                    <button onclick="closeTranscriptionDialog()" class="cancel-btn">
                        Cancel
                    </button>
                    <button onclick="triggerTranscription()" class="start-btn">
                        Start Transcription
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        var currentTab = 'overview';
        
        function showTab(tabName) {
            // Remove active class from all tab panes
            var panes = document.querySelectorAll('.tab-pane');
            for (var i = 0; i < panes.length; i++) {
                panes[i].classList.remove('active');
            }
            // Remove active class from all tabs
            var tabs = document.querySelectorAll('.nav-tab');
            for (var i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove('active');
            }
            // Show selected tab pane
            document.getElementById(tabName).classList.add('active');
            // Add active class to selected tab
            event.target.classList.add('active');
            currentTab = tabName;
            // Refresh data for the selected tab
            refreshTabData(tabName);
        }
        
        function refreshAllData() {
            refreshTabData(currentTab);
        }
        
        function refreshTabData(tabName) {
            switch(tabName) {
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
                case 'controls':
                    // Controls tab doesn't need refresh - static content
                    break;
            }
        }
        
        /* SocketIO connection and real-time task monitoring */
        var socket = null;
        var currentTaskFilter = 'all';
        
        function initializeSocketIO() {
            socket = io();
            
            socket.on('connect', function() {
                console.log('Connected to SocketIO server');
                updateSocketStatus(true);
                socket.emit('join_task_monitoring');
            });
            
            socket.on('disconnect', function() {
                console.log('Disconnected from SocketIO server');
                updateSocketStatus(false);
            });
            
            socket.on('task_updates', function(data) {
                updateRealtimeTasks(data);
            });
            
            socket.on('filtered_tasks', function(data) {
                updateRealtimeTasks(data);
            });
            
            socket.on('system_metrics', function(data) {
                updateSystemHealth(data);
            });
            
            socket.on('error', function(data) {
                console.error('SocketIO error:', data);
            });
        }
        
        function updateSocketStatus(connected) {
            var statusIndicator = document.getElementById('socket-status');
            var statusText = document.getElementById('socket-text');
            
            if (connected) {
                statusIndicator.className = 'status-indicator status-healthy';
                statusText.textContent = 'Connected';
            } else {
                statusIndicator.className = 'status-indicator status-unhealthy';
                statusText.textContent = 'Disconnected';
            }
        }
        
        function filterTasks(filterType) {
            currentTaskFilter = filterType;
            
            // Update filter button states
            var filterBtns = document.querySelectorAll('.filter-btn');
            for (var i = 0; i < filterBtns.length; i++) {
                filterBtns[i].classList.remove('active');
            }
            event.target.classList.add('active');
            
            // Request filtered tasks from server
            if (socket && socket.connected) {
                socket.emit('filter_tasks', { filter: filterType });
            }
        }
        
        function updateRealtimeTasks(data) {
            var tasksList = document.getElementById('realtime-tasks-list');
            var totalTasks = document.getElementById('total-tasks');
            var activeTasks = document.getElementById('active-tasks');
            var reservedTasks = document.getElementById('reserved-tasks');
            var queuedTasks = document.getElementById('queued-tasks');
            
            if (data.tasks && data.tasks.length > 0) {
                var html = '';
                for (var i = 0; i < data.tasks.length; i++) {
                    var task = data.tasks[i];
                    html += '<div class="task-item">';
                    html += '<div class="task-info">';
                    html += '<div class="task-name">' + task.name + '</div>';
                    html += '<div class="task-details">ID: ' + task.id + ' | Status: ' + task.status + '</div>';
                    html += '</div>';
                    if (task.progress !== undefined) {
                        html += '<div class="task-progress">';
                        html += '<div class="progress-bar">';
                        html += '<div class="progress-fill" style="width: ' + task.progress + '%"></div>';
                        html += '</div>';
                        html += '<div class="progress-text">' + task.progress + '%</div>';
                        html += '</div>';
                    }
                    html += '</div>';
                }
                tasksList.innerHTML = html;
            } else {
                tasksList.innerHTML = '<p>No tasks found</p>';
            }
            
            // Update summary counts
            if (data.summary) {
                totalTasks.textContent = data.summary.total || 0;
                activeTasks.textContent = data.summary.active || 0;
                reservedTasks.textContent = data.summary.reserved || 0;
                queuedTasks.textContent = data.summary.queued || 0;
            }
        }
        
        function updateSystemHealth(data) {
            var systemHealth = document.getElementById('system-health');
            if (data && data.system) {
                var html = '<div class="health-grid">';
                html += '<div class="health-item">';
                html += '<span class="health-label">CPU:</span>';
                html += '<span class="health-value">' + data.system.cpu_percent + '%</span>';
                html += '</div>';
                html += '<div class="health-item">';
                html += '<span class="health-label">Memory:</span>';
                html += '<span class="health-value">' + data.system.memory_percent + '%</span>';
                html += '</div>';
                html += '<div class="health-item">';
                html += '<span class="health-label">Disk:</span>';
                html += '<span class="health-value">' + data.system.disk_percent + '%</span>';
                html += '</div>';
                html += '</div>';
                systemHealth.innerHTML = html;
            }
        }
        
        // Modal functions
        function openVODDialog() {
            document.getElementById('vod-dialog').style.display = 'block';
        }
        
        function closeVODDialog() {
            document.getElementById('vod-dialog').style.display = 'none';
        }
        
        function openTranscriptionDialog() {
            document.getElementById('transcription-dialog').style.display = 'block';
        }
        
        function closeTranscriptionDialog() {
            document.getElementById('transcription-dialog').style.display = 'none';
        }
        
        function triggerVODProcessing() {
            var filePath = document.getElementById('vod-file-path').value;
            if (!filePath) {
                alert('Please enter a file path');
                return;
            }
            
            fetch('/api/tasks/trigger_vod_processing', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ file_path: filePath })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('VOD processing started successfully!');
                    closeVODDialog();
                } else {
                    alert('Error: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error starting VOD processing');
            });
        }
        
        function triggerTranscription() {
            var filePath = document.getElementById('transcription-file-path').value;
            if (!filePath) {
                alert('Please enter a file path');
                return;
            }
            
            fetch('/api/tasks/trigger_transcription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ file_path: filePath })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Transcription started successfully!');
                    closeTranscriptionDialog();
                } else {
                    alert('Error: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error starting transcription');
            });
        }
        
        // Data refresh functions
        function refreshOverviewData() {
            // Refresh system health
            fetch('/api/health')
                .then(response => response.json())
                .then(data => {
                    if (data.checks && data.checks.system) {
                        updateSystemHealth({ system: data.checks.system });
                    }
                })
                .catch(error => console.error('Error refreshing overview:', error));
            
            // Refresh queue overview
            fetch('/api/queue/stats')
                .then(response => response.json())
                .then(data => {
                    var queueOverview = document.getElementById('queue-overview');
                    if (data.total_jobs !== undefined) {
                        queueOverview.innerHTML = '<p>Total Jobs: ' + data.total_jobs + '</p>';
                    }
                })
                .catch(error => console.error('Error refreshing queue overview:', error));
        }
        
        function refreshRealtimeData() {
            if (socket && socket.connected) {
                socket.emit('request_task_updates');
            }
        }
        
        function refreshQueueData() {
            fetch('/api/queue/jobs')
                .then(response => response.json())
                .then(data => {
                    var queueJobs = document.getElementById('queue-jobs');
                    if (data.jobs && data.jobs.length > 0) {
                        var html = '<div class="queue-jobs-list">';
                        for (var i = 0; i < data.jobs.length; i++) {
                            var job = data.jobs[i];
                            html += '<div class="job-item">';
                            html += '<div class="job-info">';
                            html += '<div class="job-name">' + job.name + '</div>';
                            html += '<div class="job-details">ID: ' + job.id + ' | Status: ' + job.status + '</div>';
                            html += '</div>';
                            html += '<div class="job-actions">';
                            html += '<button onclick="pauseJob(\'' + job.id + '\')" class="action-btn">Pause</button>';
                            html += '<button onclick="resumeJob(\'' + job.id + '\')" class="action-btn">Resume</button>';
                            html += '<button onclick="stopJob(\'' + job.id + '\')" class="action-btn">Stop</button>';
                            html += '<button onclick="removeJob(\'' + job.id + '\')" class="action-btn">Remove</button>';
                            html += '</div>';
                            html += '</div>';
                        }
                        html += '</div>';
                        queueJobs.innerHTML = html;
                    } else {
                        queueJobs.innerHTML = '<p>No jobs in queue</p>';
                    }
                })
                .catch(error => console.error('Error refreshing queue data:', error));
        }
        
        function refreshCeleryData() {
            fetch('/api/celery/tasks')
                .then(response => response.json())
                .then(data => {
                    var celeryTasks = document.getElementById('celery-tasks');
                    if (data.tasks && data.tasks.length > 0) {
                        var html = '<div class="celery-tasks-list">';
                        for (var i = 0; i < data.tasks.length; i++) {
                            var task = data.tasks[i];
                            html += '<div class="task-item">';
                            html += '<div class="task-info">';
                            html += '<div class="task-name">' + task.name + '</div>';
                            html += '<div class="task-details">ID: ' + task.id + ' | Status: ' + task.status + '</div>';
                            html += '</div>';
                            html += '</div>';
                        }
                        html += '</div>';
                        celeryTasks.innerHTML = html;
                    } else {
                        celeryTasks.innerHTML = '<p>No Celery tasks found</p>';
                    }
                })
                .catch(error => console.error('Error refreshing Celery data:', error));
        }
        
        function refreshHealthData() {
            fetch('/api/health')
                .then(response => response.json())
                .then(data => {
                    var healthChecks = document.getElementById('health-checks');
                    if (data.checks) {
                        var html = '<div class="health-checks-grid">';
                        for (var checkName in data.checks) {
                            var check = data.checks[checkName];
                            html += '<div class="health-check-item">';
                            html += '<div class="health-check-name">' + checkName + '</div>';
                            html += '<div class="health-check-status ' + check.status + '">' + check.status + '</div>';
                            html += '</div>';
                        }
                        html += '</div>';
                        healthChecks.innerHTML = html;
                    }
                })
                .catch(error => console.error('Error refreshing health data:', error));
        }
        
        function refreshMetricsData() {
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => {
                    var metricsData = document.getElementById('metrics-data');
                    if (data.metrics) {
                        var html = '<div class="metrics-grid">';
                        for (var metricName in data.metrics) {
                            var metric = data.metrics[metricName];
                            html += '<div class="metric-item">';
                            html += '<div class="metric-name">' + metricName + '</div>';
                            html += '<div class="metric-value">' + metric.value + '</div>';
                            html += '</div>';
                        }
                        html += '</div>';
                        metricsData.innerHTML = html;
                    }
                })
                .catch(error => console.error('Error refreshing metrics data:', error));
        }
        
        // Queue management functions
        function pauseJob(jobId) {
            fetch('/api/queue/jobs/' + jobId + '/pause', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        refreshQueueData();
                    } else {
                        alert('Error pausing job: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => console.error('Error pausing job:', error));
        }
        
        function resumeJob(jobId) {
            fetch('/api/queue/jobs/' + jobId + '/resume', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        refreshQueueData();
                    } else {
                        alert('Error resuming job: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => console.error('Error resuming job:', error));
        }
        
        function stopJob(jobId) {
            fetch('/api/queue/jobs/' + jobId + '/stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        refreshQueueData();
                    } else {
                        alert('Error stopping job: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => console.error('Error stopping job:', error));
        }
        
        function removeJob(jobId) {
            fetch('/api/queue/jobs/' + jobId + '/remove', { method: 'DELETE' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        refreshQueueData();
                    } else {
                        alert('Error removing job: ' + (data.error || 'Unknown error'));
                    }
                })
                .catch(error => console.error('Error removing job:', error));
        }
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initializeSocketIO();
            refreshAllData();
            
            // Set up periodic refresh
            setInterval(refreshAllData, 30000); // Refresh every 30 seconds
        });
    </script>
</body>
</html>
"""
    
    def _render_dashboard_css(self) -> str:
        """Render the dashboard CSS styles."""
        return """
        /* Main Dashboard Styles */
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .nav-tabs {
            display: flex;
            background: white;
            border-radius: 10px 10px 0 0;
            overflow: hidden;
            margin-bottom: 0;
        }
        
        .nav-tab {
            flex: 1;
            padding: 15px;
            text-align: center;
            background: #f8f9fa;
            border: none;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .nav-tab.active {
            background: white;
            font-weight: bold;
        }
        
        .nav-tab:hover {
            background: #e9ecef;
        }
        
        .tab-content {
            background: white;
            padding: 20px;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            min-height: 600px;
        }
        
        .tab-pane {
            display: none;
        }
        
        .tab-pane.active {
            display: block;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .status-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .status-card h3 {
            margin-top: 0;
            color: #333;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-healthy { background-color: #28a745; }
        .status-degraded { background-color: #ffc107; }
        .status-unhealthy { background-color: #dc3545; }
        
        /* Real-time Task Monitoring Styles */
        .realtime-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .task-filters {
            display: flex;
            gap: 10px;
        }
        
        .filter-btn {
            padding: 8px 16px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .filter-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        .filter-btn:hover {
            background: #f8f9fa;
        }
        
        .connection-status {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .task-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .summary-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        
        .summary-value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }
        
        .realtime-tasks-container {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .task-analytics {
            background: white;
            border-radius: 8px;
            padding: 20px;
        }
        
        /* Queue Management Styles */
        .queue-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        .queue-table th,
        .queue-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        .queue-table th {
            background: #f8f9fa;
            font-weight: bold;
        }
        
        .action-button {
            padding: 6px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 5px;
            font-size: 12px;
        }
        
        .action-button.danger {
            background: #dc3545;
            color: white;
        }
        
        .action-button.warning {
            background: #ffc107;
            color: #333;
        }
        
        .action-button.warning:hover {
            background: #e0a800;
        }
        
        /* Manual Controls Styles */
        .manual-controls {
            margin-bottom: 20px;
        }
        
        .controls-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .control-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .control-card button {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            width: 100%;
        }
        
        .control-card button.transcription-btn {
            background: #28a745;
        }
        
        .control-card button.cancel-btn {
            background: #6c757d;
            margin-right: 10px;
        }
        
        .control-card button.start-btn {
            background: #28a745;
        }
        
        #transcription-dialog {
            display: none;
            position: fixed;
            top: 30%;
            left: 50%;
            transform: translate(-50%,-50%);
            background: white;
            border: 1px solid #ccc;
            padding: 20px;
            z-index: 1000;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        
        .transcription-dialog p {
            margin-bottom: 15px;
        }
        
        #transcription-file-path {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 15px;
        }
        
        .dialog-buttons {
            text-align: right;
        }
        
        .dialog-buttons button {
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            border: none;
        }
        
        /* Refresh Button */
        .refresh-button {
            background: rgba(255,255,255,0.2);
            color: white;
            border: 1px solid rgba(255,255,255,0.3);
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 10px;
        }
        
        .refresh-button:hover {
            background: rgba(255,255,255,0.3);
        }
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

def start_integrated_dashboard(host: str = "0.0.0.0", port: int = 5051, config: Optional[DashboardConfig] = None):
    """Start the integrated monitoring dashboard."""
    if config is None:
        config = DashboardConfig(host=host, port=port)
    
    dashboard = IntegratedDashboard(config)
    dashboard.run()

if __name__ == "__main__":
    start_integrated_dashboard() 