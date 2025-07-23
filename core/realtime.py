from flask import request, current_app
from datetime import datetime
import psutil
import threading
import time

# Example: import celery_app, queue manager, etc. as needed
# from core.tasks import celery_app
# from core.task_queue import QueueManager

# Placeholder for real-time data sources
# Replace with actual imports and logic as you migrate more features

def register_realtime_events(app):
    socketio = app.socketio

    @socketio.on('connect')
    def handle_connect():
        socketio.emit('connected', {
            'status': 'connected',
            'timestamp': datetime.now().isoformat(),
            'client_id': request.sid
        }, room=request.sid)

    @socketio.on('disconnect')
    def handle_disconnect():
        # Optionally log or update metrics
        pass

    @socketio.on('join_task_monitoring')
    def handle_join_task_monitoring(data=None):
        room = 'task_monitoring'
        socketio.enter_room(request.sid, room)
        socketio.emit('joined_room', {'room': room, 'status': 'joined'}, room=request.sid)

    @socketio.on('request_task_updates')
    def handle_request_task_updates(data=None):
        try:
            from core.api.routes.queue import get_all_jobs  # Adjust import as needed
            jobs = get_all_jobs()
            socketio.emit('task_updates', {'jobs': jobs}, room=request.sid)
        except Exception as e:
            socketio.emit('error', {'message': str(e)}, room=request.sid)

    def broadcast_task_updates():
        while True:
            try:
                from core.api.routes.queue import get_all_jobs  # Adjust import as needed
                jobs = get_all_jobs()
                socketio.emit('task_updates', {'jobs': jobs})
            except Exception as e:
                pass
            time.sleep(5)
    # Start background thread for periodic updates
    thread = threading.Thread(target=broadcast_task_updates, daemon=True)
    thread.start()

    @socketio.on('filter_tasks')
    def handle_filter_tasks(data):
        try:
            task_type = data.get('type', 'all') if data else 'all'
            from core.api.routes.queue import get_all_jobs  # Adjust import as needed
            jobs = get_all_jobs()
            if task_type == 'all':
                filtered = jobs
            else:
                filtered = [j for j in jobs if (task_type in (j.get('type') or '').lower() or task_type in (j.get('name') or '').lower())]
            socketio.emit('filtered_tasks', {'jobs': filtered}, room=request.sid)
        except Exception as e:
            socketio.emit('error', {'message': str(e)}, room=request.sid)

    @socketio.on('request_task_analytics')
    def handle_request_task_analytics():
        try:
            from core.api.routes.queue import get_all_jobs  # Adjust import as needed
            jobs = get_all_jobs()
            # Example analytics: count by status, average progress
            status_counts = {}
            total_progress = 0
            for job in jobs:
                status = job.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                total_progress += job.get('progress', 0) or 0
            avg_progress = total_progress / len(jobs) if jobs else 0
            analytics = {
                'status_counts': status_counts,
                'average_progress': avg_progress,
                'total_jobs': len(jobs)
            }
            socketio.emit('task_analytics', analytics, room=request.sid)
        except Exception as e:
            socketio.emit('error', {'message': str(e)}, room=request.sid)

    @socketio.on('request_system_metrics')
    def handle_system_metrics_request():
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': round(memory.available / (1024**3), 2),
                    'disk_percent': disk.percent,
                    'disk_free_gb': round(disk.free / (1024**3), 2),
                },
                # Add celery/redis/queue metrics as needed
            }
            socketio.emit('system_metrics', metrics, room=request.sid)
        except Exception as e:
            socketio.emit('error', {'message': str(e)}, room=request.sid) 