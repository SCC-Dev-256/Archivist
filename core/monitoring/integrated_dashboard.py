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
# Lazy service initialization
_queue_manager = None

def get_queue_manager():
    """Get queue manager with lazy initialization."""
    global _queue_manager
    if _queue_manager is None:
        try:
            from core.lazy_imports import get_queue_service
            _queue_manager = get_queue_service()
        except ImportError:
            _queue_manager = None
    return _queue_manager
from core.tasks import celery_app
from core.monitoring.socket_tracker import socket_tracker
from core.models import TranscriptionResultORM

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
        self.queue_manager = None  # Will be initialized lazily when needed
        
        # Task history storage for analytics
        
    def _get_queue_manager(self):
        """Get queue manager with lazy initialization."""
        if self.queue_manager is None:
            self.queue_manager = get_queue_manager()
        return self.queue_manager
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
            sid = request.sid
            socket_tracker.on_connect(sid, request.environ)
            emit('connected', {'sid': sid, 'message': 'Connected to server'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            sid = request.sid
            socket_tracker.on_disconnect(sid)
        
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
            """Handle system metrics request."""
            sid = request.sid
            socket_tracker.on_event_received(sid, 'request_system_metrics')
            
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
                
                socket_tracker.on_event_sent(sid, 'system_metrics')
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
                jobs = self._get_queue_manager().get_all_jobs()
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
                job_status = self._get_queue_manager().get_job_status(job_id)
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
                success = self._get_queue_manager().reorder_job(job_id, position)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error reordering job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/stop', methods=['POST'])
        def api_queue_stop_job(job_id):
            """Stop a running job."""
            try:
                success = self._get_queue_manager().stop_job(job_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error stopping job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/pause', methods=['POST'])
        def api_queue_pause_job(job_id):
            """Pause a job."""
            try:
                success = self._get_queue_manager().pause_job(job_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error pausing job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/resume', methods=['POST'])
        def api_queue_resume_job(job_id):
            """Resume a paused job."""
            try:
                success = self._get_queue_manager().resume_job(job_id)
                return jsonify({'success': success})
            except Exception as e:
                logger.error(f"Error resuming job {job_id}: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/queue/jobs/<job_id>/remove', methods=['DELETE'])
        def api_queue_remove_job(job_id):
            """Remove a job from the queue."""
            try:
                success = self._get_queue_manager().remove_job(job_id)
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
                success = self._get_queue_manager().retry_job(job_id)
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
                success = self._get_queue_manager().cancel_job(job_id)
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
                jobs = self._get_queue_manager().get_all_jobs()
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
                success = self._get_queue_manager().cleanup_old_jobs(max_age_hours)
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
                rq_jobs = self._get_queue_manager().get_all_jobs()
                
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
                from core.check_mounts import list_mount_contents
                data = request.get_json()
                file_path = data.get('file_path')
                
                if not file_path:
                    return jsonify({
                        'success': False,
                        'error': 'file_path is required'
                    }), 400
                
                # Validate file exists and is accessible
                if not os.path.exists(file_path):
                    return jsonify({
                        'success': False,
                        'error': f'File not found: {file_path}'
                    }), 404
                
                # Check if file is on a mounted drive
                mount_points = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4', 
                               '/mnt/flex-5', '/mnt/flex-6', '/mnt/flex-7', '/mnt/flex-8']
                
                is_mounted = any(file_path.startswith(mount) for mount in mount_points)
                if is_mounted:
                    logger.info(f"Transcription requested for mounted file: {file_path}")
                else:
                    logger.warning(f"Transcription requested for non-mounted file: {file_path}")
                
                result = run_whisper_transcription.delay(file_path)
                return jsonify({
                    'success': True,
                    'task_id': result.id,
                    'message': f'Transcription triggered for {file_path}',
                    'mounted_file': is_mounted
                })
            except Exception as e:
                logger.error(f"Error triggering transcription: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/mounts/list', methods=['GET'])
        def list_mounts():
            """List available mount points and their contents."""
            try:
                from core.check_mounts import list_mount_contents, verify_critical_mounts
                
                mount_points = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4', 
                               '/mnt/flex-5', '/mnt/flex-6', '/mnt/flex-7', '/mnt/flex-8']
                
                mounts_data = {}
                for mount in mount_points:
                    try:
                        if os.path.exists(mount) and os.path.ismount(mount):
                            contents = list_mount_contents(mount)
                            mounts_data[mount] = {
                                'status': 'mounted',
                                'contents': contents[:50],  # Limit to first 50 items
                                'total_files': len(contents)
                            }
                        else:
                            mounts_data[mount] = {
                                'status': 'not_mounted',
                                'contents': [],
                                'total_files': 0
                            }
                    except Exception as e:
                        mounts_data[mount] = {
                            'status': 'error',
                            'error': str(e),
                            'contents': [],
                            'total_files': 0
                        }
                
                return jsonify({
                    'success': True,
                    'mounts': mounts_data
                })
            except Exception as e:
                logger.error(f"Error listing mounts: {e}")
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
            rq_jobs = self._get_queue_manager().get_all_jobs()
            
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
            from celery.result import AsyncResult
            result = AsyncResult(task_id, app=celery_app)
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
        except (TypeError, ValueError):
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
    <script src="/static/dashboard.js"></script>
</head>
<body>
            <div class="container">
            <div class="header">
                <h1>🚀 Integrated VOD Processing Monitor</h1>
                <p>Unified monitoring for VOD processing, queue management, and system health</p>
                <div class="header-actions">
                    <button class="refresh-button" onclick="refreshAllData()">🔄 Refresh All</button>
                    <button class="status-button" onclick="showSystemStatus()">📊 System Status</button>
                    <button class="help-button" onclick="showHelp()">❓ Help</button>
                </div>
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
                                <h3>🎤 Transcription - Mounted Drives</h3>
                                <span class="close" onclick="closeTranscriptionDialog()">&times;</span>
                            </div>
                            <div class="modal-body">
                                <div class="file-browser-section">
                                    <h4>📁 Available Mounted Drives</h4>
                                    <div id="mounts-list" class="mounts-grid">
                                        <p>Loading mounted drives...</p>
                                    </div>
                                </div>
                                
                                <div class="file-path-section">
                                    <h4>📄 File Path</h4>
                                    <p>Enter the full path to the video file you want to transcribe:</p>
                                    <input type="text" id="transcription-file-path" placeholder="e.g., /mnt/flex-1/videos/video.mp4" />
                                    <div class="path-validation">
                                        <span id="path-status" class="path-indicator"></span>
                                        <span id="path-message"></span>
                                    </div>
                                </div>
                                
                                <div class="dialog-buttons">
                                    <button onclick="closeTranscriptionDialog()" class="cancel-btn">
                                        Cancel
                                    </button>
                                    <button onclick="triggerTranscription()" class="start-btn">
                                        🎤 Start Transcription
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

</body>
</html>
        

        
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
            loadMountedDrives();
        }
        
        function closeTranscriptionDialog() {
            document.getElementById('transcription-dialog').style.display = 'none';
            document.getElementById('transcription-file-path').value = '';
            document.getElementById('path-status').className = 'path-indicator';
            document.getElementById('path-message').textContent = '';
        }
        
        function loadMountedDrives() {
            console.log('Loading mounted drives...');
            var mountsList = document.getElementById('mounts-list');
            if (!mountsList) {
                console.error('Mounts list element not found');
                return;
            }
            
            mountsList.innerHTML = '<p>Loading mounted drives...</p>';
            
            fetch('/api/mounts/list')
                .then(response => {
                    console.log('Response status:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('Mounts data received:', data);
                    if (data.success && data.mounts) {
                        displayMountedDrives(data.mounts);
                    } else {
                        console.error('Invalid mounts data:', data);
                        mountsList.innerHTML = '<p>Error: Invalid data received</p>';
                    }
                })
                .catch(error => {
                    console.error('Error loading mounted drives:', error);
                    mountsList.innerHTML = '<p>Error loading mounted drives: ' + error.message + '</p>';
                });
        }
        
        function displayMountedDrives(mounts) {
            var mountsList = document.getElementById('mounts-list');
            var html = '';
            
            for (var mountPath in mounts) {
                var mount = mounts[mountPath];
                var statusClass = mount.status === 'mounted' ? 'mount-healthy' : 'mount-unhealthy';
                
                html += '<div class="mount-item ' + statusClass + '">';
                html += '<div class="mount-header">';
                html += '<span class="mount-path">' + mountPath + '</span>';
                html += '<span class="mount-status">' + mount.status + '</span>';
                html += '</div>';
                
                if (mount.status === 'mounted' && mount.contents && mount.contents.length > 0) {
                    html += '<div class="mount-contents">';
                    html += '<div class="mount-summary">' + mount.total_files + ' files available</div>';
                    
                    // Create organized file tree
                    var videoFiles = mount.contents.filter(function(file) {
                        return file.toLowerCase().match(/\.(mp4|avi|mov|mkv|wmv|flv|webm|mpeg|mpg)$/);
                    });
                    
                    if (videoFiles.length > 0) {
                        html += '<div class="file-tree">';
                        html += '<div class="tree-header">';
                        html += '<span class="tree-title">Video Files (' + videoFiles.length + ')</span>';
                        html += '<button class="expand-all-btn" onclick="toggleAllFiles(' + JSON.stringify(mountPath) + ')">Expand All</button>';
                        html += '</div>';
                        html += '<div class="tree-content" id="tree-' + mountPath.replace(/\//g, '-') + '">';
                        
                        // Group files by year/type for better organization
                        var groupedFiles = groupFilesByYear(videoFiles);
                        
                        for (var year in groupedFiles) {
                            html += '<div class="year-group">';
                            html += '<div class="year-header" onclick="toggleYearGroup(this)">';
                            html += '<span class="year-icon">📅</span>';
                            html += '<span class="year-title">' + year + ' (' + groupedFiles[year].length + ' files)</span>';
                            html += '<span class="expand-icon">▶</span>';
                            html += '</div>';
                            html += '<div class="year-files">';
                            
                            groupedFiles[year].forEach(function(file) {
                                html += '<div class="file-item" onclick="selectFile(' + JSON.stringify(mountPath + '/' + file) + ')">';
                                html += '<span class="file-icon">🎬</span>';
                                html += '<span class="file-name">' + file + '</span>';
                                html += '<button class="add-to-queue-btn" onclick="event.stopPropagation(); addToQueue(' + JSON.stringify(mountPath + '/' + file) + ')">+</button>';
                                html += '</div>';
                            });
                            
                            html += '</div>';
                            html += '</div>';
                        }
                        
                        html += '</div>';
                        html += '</div>';
                    } else {
                        html += '<div class="no-videos">No video files found in this mount</div>';
                    }
                    
                    html += '</div>';
                } else if (mount.status === 'error') {
                    html += '<div class="mount-error">Error: ' + mount.error + '</div>';
                }
                
                html += '</div>';
            }
            
            mountsList.innerHTML = html;
        }
        
        function groupFilesByYear(files) {
            var grouped = {};
            
            files.forEach(function(file) {
                // Extract year from filename (common pattern: YYYY in filename)
                var yearMatch = file.match(/(20\d{2})/);
                var year = yearMatch ? yearMatch[1] : 'Unknown';
                
                if (!grouped[year]) {
                    grouped[year] = [];
                }
                grouped[year].push(file);
            });
            
            // Sort years and files within each year
            var sortedGrouped = {};
            Object.keys(grouped).sort().reverse().forEach(function(year) {
                sortedGrouped[year] = grouped[year].sort();
            });
            
            return sortedGrouped;
        }
        
        function toggleYearGroup(header) {
            var yearGroup = header.parentElement;
            var yearFiles = yearGroup.querySelector('.year-files');
            var expandIcon = header.querySelector('.expand-icon');
            
            if (yearFiles.style.display === 'none' || yearFiles.style.display === '') {
                yearFiles.style.display = 'block';
                expandIcon.textContent = '▼';
                yearGroup.classList.add('expanded');
            } else {
                yearFiles.style.display = 'none';
                expandIcon.textContent = '▶';
                yearGroup.classList.remove('expanded');
            }
        }
        
        function toggleAllFiles(mountPath) {
            var treeId = 'tree-' + mountPath.replace(/\//g, '-');
            var treeContent = document.getElementById(treeId);
            var yearGroups = treeContent.querySelectorAll('.year-group');
            var expandAllBtn = treeContent.parentElement.querySelector('.expand-all-btn');
            
            var allExpanded = true;
            yearGroups.forEach(function(group) {
                var yearFiles = group.querySelector('.year-files');
                if (yearFiles.style.display === 'none' || yearFiles.style.display === '') {
                    allExpanded = false;
                }
            });
            
            yearGroups.forEach(function(group) {
                var yearFiles = group.querySelector('.year-files');
                var expandIcon = group.querySelector('.expand-icon');
                
                if (allExpanded) {
                    yearFiles.style.display = 'none';
                    expandIcon.textContent = '▶';
                    group.classList.remove('expanded');
                } else {
                    yearFiles.style.display = 'block';
                    expandIcon.textContent = '▼';
                    group.classList.add('expanded');
                }
            });
            
            expandAllBtn.textContent = allExpanded ? 'Expand All' : 'Collapse All';
        }
        
        function addToQueue(filePath) {
            // Add file to transcription queue
            fetch('/api/tasks/trigger_transcription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_path: filePath
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('✅ File added to transcription queue: ' + filePath.split('/').pop(), 'success');
                } else {
                    showNotification('❌ Error adding file to queue: ' + data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error adding to queue:', error);
                showNotification('❌ Error adding file to queue', 'error');
            });
        }
        
        function showNotification(message, type) {
            // Create notification element
            var notification = document.createElement('div');
            notification.className = 'notification notification-' + type;
            notification.textContent = message;
            
            // Add to page
            document.body.appendChild(notification);
            
            // Remove after 3 seconds
            setTimeout(function() {
                notification.remove();
            }, 3000);
        }
        
        function showSystemStatus() {
            // Show detailed system status in a modal
            var statusHtml = '<div class="system-status-modal">';
            statusHtml += '<h2>📊 System Status Overview</h2>';
            statusHtml += '<div class="status-grid-detailed">';
            
            // Fetch and display detailed status
            fetch('/api/health')
                .then(response => response.json())
                .then(data => {
                    if (data.checks) {
                        // System resources
                        if (data.checks.system) {
                            statusHtml += '<div class="status-section">';
                            statusHtml += '<h3>💻 System Resources</h3>';
                            data.checks.system.forEach(check => {
                                statusHtml += '<div class="status-item">';
                                statusHtml += '<span class="status-label">' + check.component + ':</span>';
                                statusHtml += '<span class="status-value ' + check.status + '">' + check.status + '</span>';
                                statusHtml += '</div>';
                            });
                            statusHtml += '</div>';
                        }
                        
                        // Storage status
                        if (data.checks.storage) {
                            statusHtml += '<div class="status-section">';
                            statusHtml += '<h3>💾 Storage Status</h3>';
                            data.checks.storage.forEach(check => {
                                statusHtml += '<div class="status-item">';
                                statusHtml += '<span class="status-label">' + check.component + ':</span>';
                                statusHtml += '<span class="status-value ' + check.status + '">' + check.status + '</span>';
                                statusHtml += '</div>';
                            });
                            statusHtml += '</div>';
                        }
                    }
                    
                    statusHtml += '</div>';
                    statusHtml += '<button onclick="closeSystemStatus()" class="close-btn">Close</button>';
                    statusHtml += '</div>';
                    
                    // Create modal
                    var modal = document.createElement('div');
                    modal.className = 'modal-overlay';
                    modal.innerHTML = statusHtml;
                    document.body.appendChild(modal);
                })
                .catch(error => {
                    console.error('Error fetching system status:', error);
                    showNotification('Error loading system status', 'error');
                });
        }
        
        function closeSystemStatus() {
            var modal = document.querySelector('.modal-overlay');
            if (modal) {
                modal.remove();
            }
        }
        
        function showHelp() {
            var helpHtml = '<div class="help-modal">';
            helpHtml += '<h2>❓ Help & Documentation</h2>';
            helpHtml += '<div class="help-content">';
            helpHtml += '<h3>🎮 Manual Controls</h3>';
            helpHtml += '<ul>';
            helpHtml += '<li><strong>VOD Processing:</strong> Trigger manual VOD processing for specific files</li>';
            helpHtml += '<li><strong>Transcription:</strong> Start transcription jobs with file browser</li>';
            helpHtml += '</ul>';
            helpHtml += '<h3>📋 File Browser</h3>';
            helpHtml += '<ul>';
            helpHtml += '<li><strong>Year Groups:</strong> Files are organized by year for easy navigation</li>';
            helpHtml += '<li><strong>Quick Add:</strong> Click the green "+" button to add files to queue</li>';
            helpHtml += '<li><strong>File Selection:</strong> Click file names to auto-fill the path field</li>';
            helpHtml += '</ul>';
            helpHtml += '<h3>📊 Dashboard Features</h3>';
            helpHtml += '<ul>';
            helpHtml += '<li><strong>Overview:</strong> System health, queue status, and recent activity</li>';
            helpHtml += '<li><strong>Real-time Tasks:</strong> Live monitoring of active tasks</li>';
            helpHtml += '<li><strong>Queue Management:</strong> View and manage queued jobs</li>';
            helpHtml += '<li><strong>Health Checks:</strong> Detailed system health information</li>';
            helpHtml += '</ul>';
            helpHtml += '</div>';
            helpHtml += '<button onclick="closeHelp()" class="close-btn">Close</button>';
            helpHtml += '</div>';
            
            var modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = helpHtml;
            document.body.appendChild(modal);
        }
        
        function closeHelp() {
            var modal = document.querySelector('.modal-overlay');
            if (modal) {
                modal.remove();
            }
        }
        
        function selectFile(filePath) {
            document.getElementById('transcription-file-path').value = filePath;
            validateFilePath(filePath);
        }
        
        function validateFilePath(filePath) {
            var pathStatus = document.getElementById('path-status');
            var pathMessage = document.getElementById('path-message');
            
            if (!filePath) {
                pathStatus.className = 'path-indicator path-unknown';
                pathMessage.textContent = '';
                return;
            }
            
            // Check if it's a video file
            var videoExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'];
            var isVideo = videoExtensions.some(ext => filePath.toLowerCase().endsWith(ext));
            
            if (!isVideo) {
                pathStatus.className = 'path-indicator path-error';
                pathMessage.textContent = 'Not a video file';
                return;
            }
            
            // Check if it's on a mounted drive
            var mountPoints = ['/mnt/flex-1', '/mnt/flex-2', '/mnt/flex-3', '/mnt/flex-4', 
                              '/mnt/flex-5', '/mnt/flex-6', '/mnt/flex-7', '/mnt/flex-8'];
            var isMounted = mountPoints.some(mount => filePath.startsWith(mount));
            
            if (isMounted) {
                pathStatus.className = 'path-indicator path-valid';
                pathMessage.textContent = '✅ Mounted file - optimal for transcription';
            } else {
                pathStatus.className = 'path-indicator path-warning';
                pathMessage.textContent = '⚠️ Non-mounted file - may be slower';
            }
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
            console.log('Refreshing overview data...');
            
            // Refresh system health
            fetch('/api/health')
                .then(response => response.json())
                .then(data => {
                    console.log('Health data received:', data);
                    var systemHealth = document.getElementById('system-health');
                    if (data.checks && data.checks.system) {
                        var systemChecks = data.checks.system;
                        var html = '<div class="health-grid">';
                        
                        // System resources
                        if (systemChecks.find(check => check.component === 'system:resources')) {
                            var resources = systemChecks.find(check => check.component === 'system:resources');
                            if (resources && resources.details) {
                                html += '<div class="health-item">';
                                html += '<span class="health-label">CPU:</span>';
                                html += '<span class="health-value">' + resources.details.cpu_percent + '%</span>';
                                html += '</div>';
                                html += '<div class="health-item">';
                                html += '<span class="health-label">Memory:</span>';
                                html += '<span class="health-value">' + resources.details.memory_percent + '%</span>';
                                html += '</div>';
                                html += '<div class="health-item">';
                                html += '<span class="health-label">Disk:</span>';
                                html += '<span class="health-value">' + resources.details.disk_percent + '%</span>';
                                html += '</div>';
                            }
                        }
                        
                        // Celery workers
                        if (systemChecks.find(check => check.component === 'system:celery_workers')) {
                            var workers = systemChecks.find(check => check.component === 'system:celery_workers');
                            if (workers && workers.details) {
                                html += '<div class="health-item">';
                                html += '<span class="health-label">Workers:</span>';
                                html += '<span class="health-value">' + workers.details.worker_count + ' active</span>';
                                html += '</div>';
                            }
                        }
                        
                        html += '</div>';
                        systemHealth.innerHTML = html;
                    } else {
                        systemHealth.innerHTML = '<p>No system health data available</p>';
                    }
                })
                .catch(error => {
                    console.error('Error refreshing system health:', error);
                    document.getElementById('system-health').innerHTML = '<p>Error loading system health</p>';
                });
            
            // Refresh queue overview
            fetch('/api/queue/stats')
                .then(response => response.json())
                .then(data => {
                    console.log('Queue stats received:', data);
                    var queueOverview = document.getElementById('queue-overview');
                    var html = '<div class="queue-summary">';
                    
                    if (data.total_jobs !== undefined) {
                        html += '<div class="queue-item">';
                        html += '<span class="queue-label">Total Jobs:</span>';
                        html += '<span class="queue-value">' + data.total_jobs + '</span>';
                        html += '</div>';
                    }
                    
                    if (data.status_counts) {
                        for (var status in data.status_counts) {
                            html += '<div class="queue-item">';
                            html += '<span class="queue-label">' + status + ':</span>';
                            html += '<span class="queue-value">' + data.status_counts[status] + '</span>';
                            html += '</div>';
                        }
                    }
                    
                    if (data.success_rate !== undefined) {
                        html += '<div class="queue-item">';
                        html += '<span class="queue-label">Success Rate:</span>';
                        html += '<span class="queue-value">' + (data.success_rate * 100).toFixed(1) + '%</span>';
                        html += '</div>';
                    }
                    
                    html += '</div>';
                    queueOverview.innerHTML = html;
                })
                .catch(error => {
                    console.error('Error refreshing queue overview:', error);
                    document.getElementById('queue-overview').innerHTML = '<p>Error loading queue data</p>';
                });
            
            // Refresh Celery workers overview
            fetch('/api/celery/workers')
                .then(response => response.json())
                .then(data => {
                    console.log('Celery workers data received:', data);
                    var celeryOverview = document.getElementById('celery-overview');
                    var html = '<div class="celery-summary">';
                    
                    if (data.summary) {
                        html += '<div class="celery-item">';
                        html += '<span class="celery-label">Total Workers:</span>';
                        html += '<span class="celery-value">' + data.summary.total_workers + '</span>';
                        html += '</div>';
                        html += '<div class="celery-item">';
                        html += '<span class="celery-label">Active Workers:</span>';
                        html += '<span class="celery-value">' + data.summary.active_workers + '</span>';
                        html += '</div>';
                    }
                    
                    if (data.workers && Object.keys(data.workers).length > 0) {
                        html += '<div class="celery-workers-list">';
                        for (var workerName in data.workers) {
                            var worker = data.workers[workerName];
                            html += '<div class="worker-item">';
                            html += '<span class="worker-name">' + workerName + '</span>';
                            html += '<span class="worker-status">' + (worker.status || 'unknown') + '</span>';
                            html += '</div>';
                        }
                        html += '</div>';
                    } else {
                        html += '<p>No active workers found</p>';
                    }
                    
                    html += '</div>';
                    celeryOverview.innerHTML = html;
                })
                .catch(error => {
                    console.error('Error refreshing Celery overview:', error);
                    document.getElementById('celery-overview').innerHTML = '<p>Error loading Celery data</p>';
                });
            
            // Refresh recent activity
            fetch('/api/queue/stats')
                .then(response => response.json())
                .then(data => {
                    console.log('Recent activity data received:', data);
                    var recentActivity = document.getElementById('recent-activity');
                    var html = '<div class="activity-summary">';
                    
                    if (data.recent_activity) {
                        var activity = data.recent_activity;
                        html += '<div class="activity-item">';
                        html += '<span class="activity-label">Jobs Created:</span>';
                        html += '<span class="activity-value">' + (activity.jobs_created || 0) + '</span>';
                        html += '</div>';
                        html += '<div class="activity-item">';
                        html += '<span class="activity-label">Jobs Completed:</span>';
                        html += '<span class="activity-value">' + (activity.jobs_completed || 0) + '</span>';
                        html += '</div>';
                        html += '<div class="activity-item">';
                        html += '<span class="activity-label">Jobs Failed:</span>';
                        html += '<span class="activity-value">' + (activity.jobs_failed || 0) + '</span>';
                        html += '</div>';
                        html += '<div class="activity-item">';
                        html += '<span class="activity-label">Avg Processing Time:</span>';
                        html += '<span class="activity-value">' + (activity.average_processing_time || 0).toFixed(2) + 's</span>';
                        html += '</div>';
                    } else {
                        html += '<p>No recent activity data available</p>';
                    }
                    
                    html += '</div>';
                    recentActivity.innerHTML = html;
                })
                .catch(error => {
                    console.error('Error refreshing recent activity:', error);
                    document.getElementById('recent-activity').innerHTML = '<p>Error loading activity data</p>';
                });
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
                            html += '<button onclick="pauseJob(' + JSON.stringify(job.id) + ')" class="action-btn">Pause</button>';
                            html += '<button onclick="resumeJob(' + JSON.stringify(job.id) + ')" class="action-btn">Resume</button>';
                            html += '<button onclick="stopJob(' + JSON.stringify(job.id) + ')" class="action-btn">Stop</button>';
                            html += '<button onclick="removeJob(' + JSON.stringify(job.id) + ')" class="action-btn">Remove</button>';
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
            console.log('Dashboard DOM loaded, initializing...');
            
            // Initialize SocketIO
            initializeSocketIO();
            
            // Initial data load
            console.log('Loading initial data...');
            refreshAllData();
            
            // Set up periodic refresh
            setInterval(function() {
                console.log('Periodic refresh triggered');
                refreshAllData();
            }, 30000); // Refresh every 30 seconds
            
            // Set up file path validation
            var transcriptionInput = document.getElementById('transcription-file-path');
            if (transcriptionInput) {
                transcriptionInput.addEventListener('input', function() {
                    validateFilePath(this.value);
                });
            }
            
            // Add loading indicators
            showLoadingStates();
            
            console.log('Dashboard initialization complete');
        });
        
        function showLoadingStates() {
            // Show loading states for all overview sections
            var loadingSections = ["system-health", "queue-overview", "celery-overview", "recent-activity"];
            loadingSections.forEach(function(sectionId) { var element = document.getElementById(sectionId); if (element) { element.innerHTML = '<div class="loading-spinner">🔄 Loading...</div>'; } });
        }

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
        
        /* Overview Data Display Styles */
        .health-grid, .queue-summary, .celery-summary, .activity-summary {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .health-item, .queue-item, .celery-item, .activity-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #007bff;
        }
        
        .health-label, .queue-label, .celery-label, .activity-label {
            font-weight: 600;
            color: #495057;
        }
        
        .health-value, .queue-value, .celery-value, .activity-value {
            font-weight: bold;
            color: #007bff;
        }
        
        .celery-workers-list {
            margin-top: 10px;
        }
        
        .worker-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 10px;
            background: #e9ecef;
            border-radius: 4px;
            margin-bottom: 4px;
        }
        
        .worker-name {
            font-weight: 500;
            color: #495057;
        }
        
        .worker-status {
            font-size: 0.9em;
            color: #6c757d;
        }
        
        /* File Browser and Transcription Dialog Styles */
        .file-browser-section, .file-path-section {
            margin-bottom: 20px;
        }
        
        .file-browser-section h4, .file-path-section h4 {
            margin-bottom: 10px;
            color: #333;
        }
        
        .mounts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .mount-item {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 12px;
            background: #f8f9fa;
        }
        
        .mount-item.mount-healthy {
            border-left: 4px solid #28a745;
        }
        
        .mount-item.mount-unhealthy {
            border-left: 4px solid #dc3545;
        }
        
        .mount-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .mount-path {
            font-weight: 600;
            color: #495057;
        }
        
        .mount-status {
            font-size: 0.8em;
            padding: 2px 8px;
            border-radius: 12px;
            background: #e9ecef;
            color: #6c757d;
        }
        
        .mount-contents {
            margin-top: 10px;
        }
        
        .mount-summary {
            font-size: 0.9em;
            color: #6c757d;
            margin-bottom: 8px;
        }
        
        /* File Tree Styles */
        .file-tree {
            border: 1px solid #dee2e6;
            border-radius: 6px;
            overflow: hidden;
        }
        
        .tree-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 12px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        
        .tree-title {
            font-weight: 600;
            color: #495057;
        }
        
        .expand-all-btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.8em;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .expand-all-btn:hover {
            background: #0056b3;
        }
        
        .tree-content {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .year-group {
            border-bottom: 1px solid #f1f3f4;
        }
        
        .year-header {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            background: #f8f9fa;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .year-header:hover {
            background: #e9ecef;
        }
        
        .year-icon {
            margin-right: 8px;
            font-size: 1.1em;
        }
        
        .year-title {
            flex: 1;
            font-weight: 500;
            color: #495057;
        }
        
        .expand-icon {
            font-size: 0.8em;
            color: #6c757d;
            transition: transform 0.2s;
        }
        
        .year-group.expanded .expand-icon {
            transform: rotate(90deg);
        }
        
        .year-files {
            display: none;
            background: white;
        }
        
        .year-group.expanded .year-files {
            display: block;
        }
        
        .file-item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            border-bottom: 1px solid #f8f9fa;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .file-item:hover {
            background: #f8f9fa;
        }
        
        .file-icon {
            margin-right: 8px;
            font-size: 1.1em;
        }
        
        .file-name {
            flex: 1;
            font-size: 0.9em;
            color: #495057;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .add-to-queue-btn {
            background: #28a745;
            color: white;
            border: none;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: background-color 0.2s;
            margin-left: 8px;
        }
        
        .add-to-queue-btn:hover {
            background: #218838;
        }
        
        .no-videos {
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-style: italic;
        }
        
        /* Notification Styles */
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        }
        
        .notification-success {
            background: #28a745;
        }
        
        .notification-error {
            background: #dc3545;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        /* Loading and Visual Enhancements */
        .loading-spinner {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: #6c757d;
            font-size: 1.1em;
            animation: pulse 1.5s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Enhanced Status Cards */
        .status-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border: 1px solid #dee2e6;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .status-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .status-card h3 {
            margin: 0 0 15px 0;
            color: #495057;
            font-size: 1.2em;
            font-weight: 600;
            border-bottom: 2px solid #007bff;
            padding-bottom: 8px;
        }
        
        /* Enhanced Health Grid */
        .health-grid, .queue-summary, .celery-summary, .activity-summary {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .health-item, .queue-item, .celery-item, .activity-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #007bff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: background-color 0.2s;
        }
        
        .health-item:hover, .queue-item:hover, .celery-item:hover, .activity-item:hover {
            background: #f8f9fa;
        }
        
        .health-label, .queue-label, .celery-label, .activity-label {
            font-weight: 600;
            color: #495057;
        }
        
        .health-value, .queue-value, .celery-value, .activity-value {
            font-weight: 500;
            color: #007bff;
            background: #e3f2fd;
            padding: 4px 8px;
            border-radius: 4px;
            min-width: 60px;
            text-align: center;
        }
        
        /* Enhanced Navigation Tabs */
        .nav-tabs {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 20px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }
        
        .nav-tab {
            background: white;
            border: 1px solid #dee2e6;
            padding: 10px 15px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            font-weight: 500;
            color: #6c757d;
        }
        
        .nav-tab:hover {
            background: #e9ecef;
            border-color: #adb5bd;
            transform: translateY(-1px);
        }
        
        .nav-tab.active {
            background: #007bff;
            color: white;
            border-color: #007bff;
            box-shadow: 0 2px 4px rgba(0,123,255,0.3);
        }
        
        /* Enhanced Header */
        .header {
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,123,255,0.3);
        }
        
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 2.5em;
            font-weight: 700;
        }
        
        .header p {
            margin: 0 0 20px 0;
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .refresh-button {
            background: rgba(255,255,255,0.2);
            color: white;
            border: 2px solid rgba(255,255,255,0.3);
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        .refresh-button:hover {
            background: rgba(255,255,255,0.3);
            border-color: rgba(255,255,255,0.5);
            transform: translateY(-2px);
        }
        
        .header-actions {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .status-button, .help-button {
            background: rgba(255,255,255,0.2);
            color: white;
            border: 2px solid rgba(255,255,255,0.3);
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        .status-button:hover, .help-button:hover {
            background: rgba(255,255,255,0.3);
            border-color: rgba(255,255,255,0.5);
            transform: translateY(-2px);
        }
        
        /* Modal Overlay Styles */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        }
        
        .system-status-modal, .help-modal {
            background: white;
            border-radius: 12px;
            padding: 30px;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .system-status-modal h2, .help-modal h2 {
            margin: 0 0 20px 0;
            color: #495057;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        
        .status-grid-detailed {
            display: grid;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .status-section h3 {
            margin: 0 0 15px 0;
            color: #495057;
            font-size: 1.1em;
        }
        
        .status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: #f8f9fa;
            border-radius: 6px;
            margin-bottom: 5px;
        }
        
        .status-label {
            font-weight: 500;
            color: #495057;
        }
        
        .status-value {
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.9em;
        }
        
        .status-value.healthy {
            background: #d4edda;
            color: #155724;
        }
        
        .status-value.unhealthy {
            background: #f8d7da;
            color: #721c24;
        }
        
        .status-value.degraded {
            background: #fff3cd;
            color: #856404;
        }
        
        .help-content h3 {
            margin: 20px 0 10px 0;
            color: #495057;
        }
        
        .help-content ul {
            margin: 0 0 20px 20px;
        }
        
        .help-content li {
            margin-bottom: 8px;
            color: #6c757d;
        }
        
        .close-btn {
            background: #6c757d;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: background-color 0.2s;
        }
        
        .close-btn:hover {
            background: #5a6268;
        }
        
        .mount-error {
            color: #dc3545;
            font-size: 0.9em;
            font-style: italic;
        }
        
        .path-validation {
            display: flex;
            align-items: center;
            margin-top: 8px;
        }
        
        .path-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .path-unknown { background-color: #6c757d; }
        .path-valid { background-color: #28a745; }
        .path-warning { background-color: #ffc107; }
        .path-error { background-color: #dc3545; }
        
        #path-message {
            font-size: 0.9em;
            color: #6c757d;
        }
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
    
    def _render_dashboard_js(self) -> str:
        """Render the dashboard JavaScript code."""
        return """
        var currentTab = 'overview';
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
            
            if (statusIndicator && statusText) {
                if (connected) {
                    statusIndicator.className = 'status-indicator status-healthy';
                    statusText.textContent = 'Connected';
                } else {
                    statusIndicator.className = 'status-indicator status-unhealthy';
                    statusText.textContent = 'Disconnected';
                }
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
                if (tasksList) tasksList.innerHTML = html;
            } else {
                if (tasksList) tasksList.innerHTML = '<p>No tasks found</p>';
            }
            
            // Update task counts
            if (totalTasks) totalTasks.textContent = data.total_tasks || 0;
            if (activeTasks) activeTasks.textContent = data.active_tasks || 0;
            if (reservedTasks) reservedTasks.textContent = data.reserved_tasks || 0;
            if (queuedTasks) queuedTasks.textContent = data.queued_tasks || 0;
        }
        
        function updateSystemHealth(data) {
            var systemHealth = document.getElementById('system-health');
            if (systemHealth && data.overall_status) {
                if (data.overall_status === 'healthy') {
                    systemHealth.innerHTML = '<div class="health-status healthy">✅ System Healthy</div>';
                } else {
                    systemHealth.innerHTML = '<div class="health-status unhealthy">⚠️ System Issues Detected</div>';
                }
            }
        }
        
        function showTab(tabName) {
            // Remove active class from all tab panes
            var panes = document.querySelectorAll('.tab-pane');
            for (var i = 0; i < panes.length; i++) {
                panes[i].classList.remove('active');
            }
            
            // Remove active class from all tab buttons
            var tabs = document.querySelectorAll('.nav-tab');
            for (var i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove('active');
            }
            
            // Add active class to selected tab and pane
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            currentTab = tabName;
            
            // Refresh data for the selected tab
            refreshTabData(tabName);
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
            }
        }
        
        function refreshAllData() {
            refreshTabData(currentTab);
        }
        
        function refreshOverviewData() {
            // Refresh system health
            fetch('/api/health')
                .then(response => response.json())
                .then(data => {
                    var systemHealth = document.getElementById('system-health');
                    if (data.overall_status === 'healthy') {
                        systemHealth.innerHTML = '<div class="health-status healthy">✅ System Healthy</div>';
                    } else {
                        systemHealth.innerHTML = '<div class="health-status unhealthy">⚠️ System Issues Detected</div>';
                    }
                })
                .catch(error => {
                    document.getElementById('system-health').innerHTML = '<div class="health-status error">❌ Error Loading</div>';
                });
            
            // Refresh queue overview
            fetch('/api/queue/stats')
                .then(response => response.json())
                .then(data => {
                    var queueOverview = document.getElementById('queue-overview');
                    queueOverview.innerHTML = '<div class="queue-summary">📋 ' + data.total_jobs + ' Total Jobs</div>';
                })
                .catch(error => {
                    document.getElementById('queue-overview').innerHTML = '<div class="queue-summary error">❌ Error Loading</div>';
                });
            
            // Refresh Celery overview
            fetch('/api/celery/workers')
                .then(response => response.json())
                .then(data => {
                    var celeryOverview = document.getElementById('celery-overview');
                    celeryOverview.innerHTML = '<div class="celery-summary">⚡ ' + data.worker_count + ' Active Workers</div>';
                })
                .catch(error => {
                    document.getElementById('celery-overview').innerHTML = '<div class="celery-summary error">❌ Error Loading</div>';
                });
            
            // Refresh recent activity
            fetch('/api/queue/stats')
                .then(response => response.json())
                .then(data => {
                    var recentActivity = document.getElementById('recent-activity');
                    var html = '<div class="activity-summary">';
                    if (data.recent_activity && data.recent_activity.length > 0) {
                        for (var i = 0; i < Math.min(5, data.recent_activity.length); i++) {
                            var activity = data.recent_activity[i];
                            html += '<div class="activity-item">' + activity.description + '</div>';
                        }
                    } else {
                        html += '<div class="activity-item">No recent activity</div>';
                    }
                    html += '</div>';
                    recentActivity.innerHTML = html;
                })
                .catch(error => {
                    document.getElementById('recent-activity').innerHTML = '<p>Error loading activity data</p>';
                });
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
                            html += '<button onclick="pauseJob(' + JSON.stringify(job.id) + ')" class="action-btn">Pause</button>';
                            html += '<button onclick="resumeJob(' + JSON.stringify(job.id) + ')" class="action-btn">Resume</button>';
                            html += '<button onclick="stopJob(' + JSON.stringify(job.id) + ')" class="action-btn">Stop</button>';
                            html += '<button onclick="removeJob(' + JSON.stringify(job.id) + ')" class="action-btn">Remove</button>';
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
        
        function showLoadingStates() {
            // Show loading states for all overview sections
            var loadingSections = ["system-health", "queue-overview", "celery-overview", "recent-activity"];
            loadingSections.forEach(function(sectionId) { var element = document.getElementById(sectionId); if (element) { element.innerHTML = '<div class="loading-spinner">🔄 Loading...</div>'; } });
        }
        
        function showSystemStatus() {
            // Create modal overlay
            var overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            overlay.innerHTML = '<div class="system-status-modal"><h2>System Status</h2><div id="system-status-content">Loading...</div><button onclick="this.parentElement.parentElement.remove()">Close</button></div>';
            document.body.appendChild(overlay);
            
            // Load system status
            fetch('/api/health')
                .then(response => response.json())
                .then(data => {
                    var content = document.getElementById('system-status-content');
                    var html = '<div class="status-details">';
                    html += '<p><strong>Overall Status:</strong> ' + data.overall_status + '</p>';
                    html += '<p><strong>Total Checks:</strong> ' + data.summary.total_checks + '</p>';
                    html += '<p><strong>Healthy:</strong> ' + data.summary.healthy + '</p>';
                    html += '<p><strong>Degraded:</strong> ' + data.summary.degraded + '</p>';
                    html += '<p><strong>Unhealthy:</strong> ' + data.summary.unhealthy + '</p>';
                    html += '</div>';
                    content.innerHTML = html;
                })
                .catch(error => {
                    document.getElementById('system-status-content').innerHTML = '<p>Error loading system status</p>';
                });
        }
        
        function showHelp() {
            // Create modal overlay
            var overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            overlay.innerHTML = '<div class="help-modal"><h2>Dashboard Help</h2><div class="help-content"><h3>Overview Tab</h3><p>Shows system health, queue status, and recent activity.</p><h3>Real-time Tasks</h3><p>Displays live task updates and progress.</p><h3>Queue Management</h3><p>Manage and control job queues.</p><h3>Manual Controls</h3><p>Trigger VOD processing and transcription jobs.</p></div><button onclick="this.parentElement.parentElement.remove()">Close</button></div>';
            document.body.appendChild(overlay);
        }
        
        function showNotification(message, type) {
            // Create notification element
            var notification = document.createElement('div');
            notification.className = 'notification notification-' + type;
            notification.textContent = message;
            
            // Add to page
            document.body.appendChild(notification);
            
            // Remove after 3 seconds
            setTimeout(function() {
                notification.remove();
            }, 3000);
        }
        
        function openVODDialog() {
            document.getElementById('vod-dialog').style.display = 'block';
        }
        
        function closeVODDialog() {
            document.getElementById('vod-dialog').style.display = 'none';
        }
        
        function closeSystemStatus() {
            var modal = document.querySelector('.system-status-modal');
            if (modal && modal.parentElement) {
                modal.parentElement.remove();
            }
        }
        
        function closeHelp() {
            var modal = document.querySelector('.help-modal');
            if (modal && modal.parentElement) {
                modal.parentElement.remove();
            }
        }
        
        function triggerVODProcessing() {
            var filePath = document.getElementById('vod-file-path').value.trim();
            
            if (!filePath) {
                showNotification('Please enter a file path', 'error');
                return;
            }
            
            if (!validateFilePath(filePath)) {
                showNotification('Invalid file path', 'error');
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
                    showNotification('VOD processing triggered successfully', 'success');
                    closeVODDialog();
                    refreshAllData();
                } else {
                    showNotification('Failed to trigger VOD processing: ' + (data.error || 'Unknown error'), 'error');
                }
            })
            .catch(error => {
                console.error('Error triggering VOD processing:', error);
                showNotification('Error triggering VOD processing', 'error');
            });
        }
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Dashboard DOM loaded, initializing...');
            
            // Initialize SocketIO
            initializeSocketIO();
            
            // Initial data refresh
            refreshAllData();
            
            // Set up periodic refresh
            setInterval(refreshAllData, 30000); // Refresh every 30 seconds
            
            // Set up file path validation
            var transcriptionInput = document.getElementById('transcription-file-path');
            if (transcriptionInput) {
                transcriptionInput.addEventListener('input', function() {
                    validateFilePath(this.value);
                });
            }
            
            // Add loading indicators
            showLoadingStates();
            
            console.log('Dashboard initialization complete');
        });
        
        // File browser and transcription functions
        function openTranscriptionDialog() {
            document.getElementById('transcription-dialog').style.display = 'block';
            loadMountedDrives();
        }
        
        function closeTranscriptionDialog() {
            document.getElementById('transcription-dialog').style.display = 'none';
            var input = document.getElementById('transcription-file-path');
            if (input) {
                input.value = '';
                document.getElementById('path-status').className = 'path-indicator';
                document.getElementById('path-message').textContent = '';
            }
        }
        
        function loadMountedDrives() {
            console.log('Loading mounted drives...');
            var mountsList = document.getElementById('mounts-list');
            if (!mountsList) {
                console.error('Mounts list element not found');
                return;
            }
            mountsList.innerHTML = '<p>Loading mounted drives...</p>';
            fetch('/api/mounts/list')
                .then(response => {
                    console.log('Response status:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('Mounts data received:', data);
                    if (data.success && data.mounts) {
                        displayMountedDrives(data.mounts);
                    } else {
                        console.error('Invalid mounts data:', data);
                        mountsList.innerHTML = '<p>Error: Invalid data received</p>';
                    }
                })
                .catch(error => {
                    console.error('Error loading mounted drives:', error);
                    mountsList.innerHTML = '<p>Error loading mounted drives: ' + error.message + '</p>';
                });
        }
        
        function displayMountedDrives(mounts) {
            var mountsList = document.getElementById('mounts-list');
            var html = '';
            for (var mountPath in mounts) {
                var mount = mounts[mountPath];
                var statusClass = mount.status === 'mounted' ? 'mount-healthy' : 'mount-unhealthy';
                html += '<div class="mount-item ' + statusClass + '">';
                html += '<div class="mount-header">';
                html += '<div class="mount-path">' + mountPath + '</div>';
                html += '<div class="mount-status">' + mount.status + '</div>';
                html += '</div>';
                if (mount.contents && mount.contents.length > 0) {
                    var videoFiles = mount.contents.filter(function(file) {
                        return /\.(mp4|avi|mov|mkv|wmv|flv|webm|mpeg|mpg)$/i.test(file);
                    });
                    if (videoFiles.length > 0) {
                        var groupedFiles = groupFilesByYear(videoFiles, mountPath);
                        html += '<div class="mount-contents">';
                        html += '<div class="mount-summary">' + videoFiles.length + ' video files found</div>';
                        html += '<div class="file-tree">';
                        html += '<div class="tree-header">';
                        html += '<div class="tree-title">Video Files</div>';
                        html += '<button class="expand-all-btn" onclick="toggleAllFiles(' + JSON.stringify(mountPath) + ')">Expand All</button>';
                        html += '</div>';
                        html += '<div class="tree-content">';
                        for (var year in groupedFiles) {
                            html += '<div class="year-group">';
                            html += '<div class="year-header" onclick="toggleYear(' + JSON.stringify(year) + ')">';
                            html += '<span class="year-icon">📁</span>';
                            html += '<span class="year-title">' + year + '</span>';
                            html += '<span class="expand-icon">▼</span>';
                            html += '</div>';
                            html += '<div class="year-files" id="year-' + year + '">';
                            for (var i = 0; i < groupedFiles[year].length; i++) {
                                var file = groupedFiles[year][i];
                                html += '<div class="file-item" onclick="selectFile(' + JSON.stringify(mountPath + '/' + file) + ')">';
                                html += '<span class="file-icon">🎬</span>';
                                html += '<span class="file-name">' + file + '</span>';
                                html += '<button class="add-to-queue-btn" onclick="event.stopPropagation(); addToQueue(' + JSON.stringify(mountPath + '/' + file) + ')">+</button>';
                                html += '</div>';
                            }
                            html += '</div>';
                            html += '</div>';
                        }
                        html += '</div>';
                        html += '</div>';
                        html += '</div>';
                    } else {
                        html += '<div class="mount-contents">';
                        html += '<div class="no-videos">No video files found</div>';
                        html += '</div>';
                    }
                } else {
                    html += '<div class="mount-contents">';
                    html += '<div class="no-videos">No contents available</div>';
                    html += '</div>';
                }
                html += '</div>';
            }
            mountsList.innerHTML = html;
        }
        
        function groupFilesByYear(files, mountPath) {
            var grouped = {};
            for (var i = 0; i < files.length; i++) {
                var file = files[i];
                var year = '2023'; // Default year, could be extracted from filename or metadata
                if (!grouped[year]) {
                    grouped[year] = [];
                }
                grouped[year].push(file);
            }
            return grouped;
        }
        
        function toggleYear(year) {
            var yearFiles = document.getElementById('year-' + year);
            if (yearFiles) {
                yearFiles.style.display = yearFiles.style.display === 'none' ? 'block' : 'none';
            }
        }
        
        function toggleAllFiles(mountPath) {
            var yearFiles = document.querySelectorAll('.year-files');
            yearFiles.forEach(function(element) {
                element.style.display = 'block';
            });
        }
        
        function selectFile(filePath) {
            var input = document.getElementById('transcription-file-path');
            if (input) {
                input.value = filePath;
                validateFilePath(filePath);
            }
        }
        
        function addToQueue(filePath) {
            // Add file to transcription queue
            fetch('/api/tasks/trigger_transcription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_path: filePath
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('File added to transcription queue: ' + filePath, 'success');
                } else {
                    showNotification('Error adding file to queue: ' + data.error, 'error');
                }
            })
            .catch(error => {
                showNotification('Error adding file to queue: ' + error.message, 'error');
            });
        }
        
        function validateFilePath(filePath) {
            var statusElement = document.getElementById('path-status');
            var messageElement = document.getElementById('path-message');
            
            if (!filePath) {
                statusElement.className = 'path-indicator';
                messageElement.textContent = '';
                return;
            }
            
            // Basic validation - check if it looks like a video file path
            var videoExtensions = /\.(mp4|avi|mov|mkv|wmv|flv|webm|mpeg|mpg)$/i;
            if (videoExtensions.test(filePath)) {
                statusElement.className = 'path-indicator valid';
                messageElement.textContent = 'Valid video file path';
            } else {
                statusElement.className = 'path-indicator invalid';
                messageElement.textContent = 'Invalid video file path';
            }
        }
        
        function triggerTranscription() {
            var filePath = document.getElementById('transcription-file-path').value;
            if (!filePath) {
                showNotification('Please enter a file path', 'error');
                return;
            }
            
            fetch('/api/tasks/trigger_transcription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_path: filePath
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Transcription started successfully', 'success');
                    closeTranscriptionDialog();
                } else {
                    showNotification('Error starting transcription: ' + data.error, 'error');
                }
            })
            .catch(error => {
                showNotification('Error starting transcription: ' + error.message, 'error');
            });
        }
        
        // Job control functions
        function pauseJob(jobId) {
            fetch('/api/queue/jobs/' + jobId + '/pause', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification('Job paused successfully', 'success');
                        refreshQueueData();
                    } else {
                        showNotification('Error pausing job: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    showNotification('Error pausing job: ' + error.message, 'error');
                });
        }
        
        function resumeJob(jobId) {
            fetch('/api/queue/jobs/' + jobId + '/resume', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification('Job resumed successfully', 'success');
                        refreshQueueData();
                    } else {
                        showNotification('Error resuming job: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    showNotification('Error resuming job: ' + error.message, 'error');
                });
        }
        
        function stopJob(jobId) {
            fetch('/api/queue/jobs/' + jobId + '/stop', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification('Job stopped successfully', 'success');
                        refreshQueueData();
                    } else {
                        showNotification('Error stopping job: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    showNotification('Error stopping job: ' + error.message, 'error');
                });
        }
        
        function removeJob(jobId) {
            fetch('/api/queue/jobs/' + jobId + '/remove', { method: 'DELETE' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification('Job removed successfully', 'success');
                        refreshQueueData();
                    } else {
                        showNotification('Error removing job: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    showNotification('Error removing job: ' + error.message, 'error');
                });
        }
        """
    
    def run(self):
        """Run the dashboard server with SocketIO support."""
        logger.info(f"Starting integrated monitoring dashboard with SocketIO on {self.host}:{self.port}")
        ssl_context = None
        import os
        if os.path.exists('cert.pem') and os.path.exists('key.pem'):
            ssl_context = ('cert.pem', 'key.pem')
            logger.info("Using self-signed SSL context for HTTPS.")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=False, allow_unsafe_werkzeug=True, ssl_context=ssl_context)

def start_integrated_dashboard(host: str = "0.0.0.0", port: int = 5051, config: Optional[DashboardConfig] = None):
    """Start the integrated monitoring dashboard."""
    if config is None:
        config = DashboardConfig(host=host, port=port)
    
    dashboard = IntegratedDashboard(config)
    dashboard.run()

if __name__ == "__main__":
    start_integrated_dashboard() 