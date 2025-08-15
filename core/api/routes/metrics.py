from flask import Blueprint, jsonify
import psutil
import redis
from datetime import datetime
from loguru import logger

# Import monitoring components
from core.monitoring.middleware import performance_middleware
from core.monitoring.socket_tracker import socket_tracker
from core.services.queue_analytics import queue_analytics
from core.database_health import db_health_checker

bp = Blueprint('metrics', __name__)

@bp.route('/metrics')
def api_metrics():
    """Get comprehensive system metrics including performance, queue, and connection data."""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent()  # Remove interval parameter to avoid blocking
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network metrics
        network = psutil.net_io_counters()
        
        # Redis status and metrics
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            redis_client.ping()
            redis_info = redis_client.info()
            redis_status = {
                'status': 'connected',
                'version': redis_info.get('redis_version', 'unknown'),
                'connected_clients': redis_info.get('connected_clients', 0),
                'used_memory_human': redis_info.get('used_memory_human', 'unknown'),
                'total_commands_processed': redis_info.get('total_commands_processed', 0),
                'keyspace_hits': redis_info.get('keyspace_hits', 0),
                'keyspace_misses': redis_info.get('keyspace_misses', 0),
            }
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            redis_status = {'status': 'disconnected', 'error': str(e)}
        
        # Queue metrics (if Celery is available)
        queue_metrics = {}
        try:
            from core.services.queue import QueueService
            queue_service = QueueService()
            queue_status = queue_service.get_queue_status()
            queue_metrics = {
                'active_jobs': len(queue_status.get('active', [])),
                'reserved_jobs': len(queue_status.get('reserved', [])),
                'scheduled_jobs': len(queue_status.get('scheduled', [])),
                'total_jobs': queue_status.get('total_jobs', 0),
                'queue_status': queue_status.get('status', 'unknown')
            }
        except Exception as e:
            logger.warning(f"Queue metrics unavailable: {e}")
            queue_metrics = {'error': str(e)}
        
        # Performance metrics from middleware
        performance_metrics = {}
        try:
            performance_metrics = performance_middleware.get_performance_metrics()
        except Exception as e:
            logger.warning(f"Performance metrics unavailable: {e}")
            performance_metrics = {'error': str(e)}
        
        # Socket.IO connection metrics
        socket_metrics = {}
        try:
            socket_metrics = socket_tracker.get_connection_metrics()
        except Exception as e:
            logger.warning(f"Socket.IO metrics unavailable: {e}")
            socket_metrics = {'error': str(e)}
        
        # Queue analytics
        queue_analytics_data = {}
        try:
            queue_analytics_data = queue_analytics.get_queue_analytics()
        except Exception as e:
            logger.warning(f"Queue analytics unavailable: {e}")
            queue_analytics_data = {'error': str(e)}
        
        # Database health
        database_health = {}
        try:
            if db_health_checker:
                database_health = db_health_checker.get_health_status()
            else:
                database_health = {'status': 'unknown', 'error': 'Database health checker not initialized'}
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            database_health = {'status': 'error', 'error': str(e)}
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
            },
            'redis': redis_status,
            'queue': queue_metrics,
            'performance': performance_metrics,
            'socket_io': socket_metrics,
            'queue_analytics': queue_analytics_data,
            'database': database_health,
            'services': {
                'flask': 'healthy',
                'redis': redis_status.get('status', 'unknown'),
                'celery': 'healthy' if queue_metrics.get('error') is None else 'unhealthy',
                'database': database_health.get('status', 'unknown'),
                'socket_io': 'healthy' if socket_metrics.get('error') is None else 'unhealthy'
            }
        })
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/health')
def api_health():
    """Get comprehensive health check data for all services."""
    try:
        health = {
            'status': 'healthy', 
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'checks': {}
        }
        
        # System health
        try:
            cpu_percent = psutil.cpu_percent()  # Remove interval parameter to avoid blocking
            memory = psutil.virtual_memory()
            health['checks']['system'] = {
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'status': 'healthy' if cpu_percent < 90 and memory.percent < 90 else 'warning'
            }
            health['services']['system'] = 'healthy'
        except Exception as e:
            health['services']['system'] = 'unhealthy'
            health['checks']['system'] = {'error': str(e)}
        
        # Redis health
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            redis_client.ping()
            health['services']['redis'] = 'healthy'
            health['checks']['redis'] = {'status': 'connected'}
        except Exception as e:
            health['services']['redis'] = 'unhealthy'
            health['checks']['redis'] = {'error': str(e)}
        
        # Queue health
        try:
            from core.services.queue import QueueService
            queue_service = QueueService()
            queue_status = queue_service.get_queue_status()
            health['services']['celery'] = 'healthy'
            health['checks']['queue'] = {
                'total_jobs': queue_status.get('total_jobs', 0),
                'status': queue_status.get('status', 'unknown')
            }
        except Exception as e:
            health['services']['celery'] = 'unhealthy'
            health['checks']['queue'] = {'error': str(e)}
        
        # Database health
        try:
            if db_health_checker:
                db_health = db_health_checker.get_health_status()
                health['services']['database'] = db_health.get('status', 'unknown')
                health['checks']['database'] = db_health
            else:
                health['services']['database'] = 'unknown'
                health['checks']['database'] = {'error': 'Database health checker not initialized'}
        except Exception as e:
            health['services']['database'] = 'unhealthy'
            health['checks']['database'] = {'error': str(e)}
        
        # Socket.IO health
        try:
            socket_metrics = socket_tracker.get_connection_metrics()
            health['services']['socket_io'] = 'healthy'
            health['checks']['socket_io'] = {
                'active_connections': socket_metrics.get('active_connections', 0),
                'total_connects': socket_metrics.get('total_connects', 0)
            }
        except Exception as e:
            health['services']['socket_io'] = 'unhealthy'
            health['checks']['socket_io'] = {'error': str(e)}
        
        # Overall status
        unhealthy_services = [s for s in health['services'].values() if s != 'healthy']
        if unhealthy_services:
            health['status'] = 'degraded' if len(unhealthy_services) < len(health['services']) else 'unhealthy'
        
        return jsonify(health)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@bp.route('/status')
def api_status():
    """Alias for system metrics (for compatibility)."""
    return api_metrics()

@bp.route('/performance')
def api_performance():
    """Get detailed performance metrics."""
    try:
        performance_data = {
            'timestamp': datetime.now().isoformat(),
            'api_performance': performance_middleware.get_performance_metrics(),
            'socket_io_performance': socket_tracker.get_connection_metrics(),
            'queue_performance': queue_analytics.get_queue_analytics()
        }
        
        # Add database performance if available
        if db_health_checker:
            db_health = db_health_checker.get_health_status()
            if db_health.get('status') == 'healthy':
                performance_data['database_performance'] = db_health.get('performance', {})
        
        return jsonify(performance_data)
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {e}")
        return jsonify({'error': str(e)}), 500 


@bp.route('/metrics/caption-autopriority', methods=['GET'])
def caption_autopriority_metrics():
    """Expose Redis-backed counters for caption autopriority.

    Returns JSON with total counters and per-city enqueued totals.
    """
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        keys = {
            'scanned_total': 'caption_autopriority_scanned_total',
            'enqueued_total': 'caption_autopriority_enqueued_total',
            'skipped_captioned_total': 'caption_autopriority_skipped_captioned_total',
            'skipped_alreadyqueued_total': 'caption_autopriority_skipped_alreadyqueued_total',
        }
        counters = {}
        for field, key in keys.items():
            try:
                val = r.get(key)
                counters[field] = int(val) if val is not None else 0
            except Exception:
                counters[field] = 0

        city_map = {}
        try:
            city_map = r.hgetall('caption_autopriority_city_enqueued_total') or {}
            # cast values to int
            city_map = {k: int(v) for k, v in city_map.items()}
        except Exception:
            city_map = {}

        return jsonify({
            'timestamp': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            'counters': counters,
            'city_enqueued_total': city_map,
        })
    except Exception as e:
        logger.error(f"caption_autopriority metrics error: {e}")
        return jsonify({'error': str(e)}), 500