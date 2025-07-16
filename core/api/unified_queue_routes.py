"""
Unified Queue Management API Routes

This module provides REST API endpoints for managing both RQ and Celery tasks
through a unified interface.
"""

from flask import Blueprint, jsonify, request
from flask_restx import Api, Resource, Namespace, fields
from loguru import logger

from core.unified_queue_manager import get_unified_queue_manager

# Create blueprint
unified_queue_bp = Blueprint('unified_queue', __name__, url_prefix='/api/unified-queue')
api = Api(unified_queue_bp, doc='/docs', title='Unified Queue Management API')

# Create namespaces
tasks_ns = Namespace('tasks', description='Task management operations')
workers_ns = Namespace('workers', description='Worker management operations')
api.add_namespace(tasks_ns)
api.add_namespace(workers_ns)

# Define models
task_model = api.model('Task', {
    'id': fields.String(required=True, description='Task ID'),
    'queue_type': fields.String(required=True, description='Queue type (rq or celery)'),
    'name': fields.String(description='Task name'),
    'status': fields.String(description='Task status'),
    'progress': fields.Integer(description='Task progress (0-100)'),
    'created_at': fields.DateTime(description='Creation timestamp'),
    'started_at': fields.DateTime(description='Start timestamp'),
    'ended_at': fields.DateTime(description='End timestamp'),
    'video_path': fields.String(description='Video file path'),
    'worker': fields.String(description='Worker name'),
    'error': fields.String(description='Error message'),
    'position': fields.Integer(description='Position in queue')
})

task_summary_model = api.model('TaskSummary', {
    'total_tasks': fields.Integer(description='Total number of tasks'),
    'rq_tasks': fields.Integer(description='Number of RQ tasks'),
    'celery_tasks': fields.Integer(description='Number of Celery tasks'),
    'status_counts': fields.Raw(description='Counts by status'),
    'workers': fields.Raw(description='Worker information'),
    'queue_health': fields.Raw(description='Queue health status')
})

worker_model = api.model('Worker', {
    'name': fields.String(description='Worker name'),
    'status': fields.String(description='Worker status'),
    'active_tasks': fields.Integer(description='Number of active tasks'),
    'reserved_tasks': fields.Integer(description='Number of reserved tasks'),
    'stats': fields.Raw(description='Worker statistics')
})

@tasks_ns.route('/')
class TaskList(Resource):
    """List all tasks from both RQ and Celery queues."""
    
    @tasks_ns.doc('list_tasks')
    @tasks_ns.marshal_list_with(task_model)
    def get(self):
        """Get all tasks from both queues."""
        try:
            queue_manager = get_unified_queue_manager()
            tasks = queue_manager.get_all_tasks()
            return tasks
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            api.abort(500, f"Failed to get tasks: {str(e)}")

@tasks_ns.route('/summary')
class TaskSummary(Resource):
    """Get task summary statistics."""
    
    @tasks_ns.doc('get_task_summary')
    @tasks_ns.marshal_with(task_summary_model)
    def get(self):
        """Get summary statistics for all queues."""
        try:
            queue_manager = get_unified_queue_manager()
            summary = queue_manager.get_task_summary()
            return summary
        except Exception as e:
            logger.error(f"Error getting task summary: {e}")
            api.abort(500, f"Failed to get task summary: {str(e)}")

@tasks_ns.route('/<string:queue_type>/<string:task_id>')
class TaskDetail(Resource):
    """Get detailed information about a specific task."""
    
    @tasks_ns.doc('get_task_details')
    def get(self, queue_type, task_id):
        """Get detailed information about a task."""
        try:
            queue_manager = get_unified_queue_manager()
            details = queue_manager.get_task_details(task_id, queue_type)
            if details:
                return details
            else:
                api.abort(404, f"Task {task_id} not found in {queue_type} queue")
        except Exception as e:
            logger.error(f"Error getting task details: {e}")
            api.abort(500, f"Failed to get task details: {str(e)}")

@tasks_ns.route('/<string:queue_type>/<string:task_id>/stop')
class TaskStop(Resource):
    """Stop a running task."""
    
    @tasks_ns.doc('stop_task')
    def post(self, queue_type, task_id):
        """Stop a running task."""
        try:
            queue_manager = get_unified_queue_manager()
            success = queue_manager.stop_task(task_id, queue_type)
            return {
                'success': success,
                'message': f"Task {task_id} {'stopped' if success else 'failed to stop'}"
            }
        except Exception as e:
            logger.error(f"Error stopping task: {e}")
            api.abort(500, f"Failed to stop task: {str(e)}")

@tasks_ns.route('/<string:queue_type>/<string:task_id>/pause')
class TaskPause(Resource):
    """Pause a task (RQ only)."""
    
    @tasks_ns.doc('pause_task')
    def post(self, queue_type, task_id):
        """Pause a task."""
        try:
            queue_manager = get_unified_queue_manager()
            success = queue_manager.pause_task(task_id, queue_type)
            return {
                'success': success,
                'message': f"Task {task_id} {'paused' if success else 'failed to pause'}"
            }
        except Exception as e:
            logger.error(f"Error pausing task: {e}")
            api.abort(500, f"Failed to pause task: {str(e)}")

@tasks_ns.route('/<string:queue_type>/<string:task_id>/resume')
class TaskResume(Resource):
    """Resume a paused task (RQ only)."""
    
    @tasks_ns.doc('resume_task')
    def post(self, queue_type, task_id):
        """Resume a paused task."""
        try:
            queue_manager = get_unified_queue_manager()
            success = queue_manager.resume_task(task_id, queue_type)
            return {
                'success': success,
                'message': f"Task {task_id} {'resumed' if success else 'failed to resume'}"
            }
        except Exception as e:
            logger.error(f"Error resuming task: {e}")
            api.abort(500, f"Failed to resume task: {str(e)}")

@tasks_ns.route('/<string:queue_type>/<string:task_id>/remove')
class TaskRemove(Resource):
    """Remove a task from the queue."""
    
    @tasks_ns.doc('remove_task')
    def delete(self, queue_type, task_id):
        """Remove a task from the queue."""
        try:
            queue_manager = get_unified_queue_manager()
            success = queue_manager.remove_task(task_id, queue_type)
            return {
                'success': success,
                'message': f"Task {task_id} {'removed' if success else 'failed to remove'}"
            }
        except Exception as e:
            logger.error(f"Error removing task: {e}")
            api.abort(500, f"Failed to remove task: {str(e)}")

@tasks_ns.route('/<string:queue_type>/<string:task_id>/reorder')
class TaskReorder(Resource):
    """Reorder a task in the queue (RQ only)."""
    
    @tasks_ns.doc('reorder_task')
    def post(self, queue_type, task_id):
        """Reorder a task in the queue."""
        try:
            data = request.get_json()
            position = data.get('position', 0)
            
            queue_manager = get_unified_queue_manager()
            success = queue_manager.reorder_task(task_id, position, queue_type)
            return {
                'success': success,
                'message': f"Task {task_id} {'reordered' if success else 'failed to reorder'}"
            }
        except Exception as e:
            logger.error(f"Error reordering task: {e}")
            api.abort(500, f"Failed to reorder task: {str(e)}")

@tasks_ns.route('/cleanup')
class TaskCleanup(Resource):
    """Clean up failed tasks."""
    
    @tasks_ns.doc('cleanup_failed_tasks')
    def post(self):
        """Clean up failed tasks from both queues."""
        try:
            queue_manager = get_unified_queue_manager()
            results = queue_manager.cleanup_failed_tasks()
            return {
                'success': True,
                'results': results,
                'message': 'Failed tasks cleanup completed'
            }
        except Exception as e:
            logger.error(f"Error cleaning up tasks: {e}")
            api.abort(500, f"Failed to cleanup tasks: {str(e)}")

@tasks_ns.route('/trigger-celery')
class TriggerCeleryTask(Resource):
    """Trigger a Celery task."""
    
    @tasks_ns.doc('trigger_celery_task')
    def post(self):
        """Trigger a Celery task."""
        try:
            data = request.get_json()
            task_name = data.get('task_name')
            kwargs = data.get('kwargs', {})
            
            if not task_name:
                api.abort(400, "task_name is required")
            
            queue_manager = get_unified_queue_manager()
            result = queue_manager.trigger_celery_task(task_name, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Error triggering Celery task: {e}")
            api.abort(500, f"Failed to trigger task: {str(e)}")

@tasks_ns.route('/enqueue-transcription')
class EnqueueTranscription(Resource):
    """Enqueue a transcription job (RQ)."""
    
    @tasks_ns.doc('enqueue_transcription')
    def post(self):
        """Enqueue a transcription job."""
        try:
            data = request.get_json()
            video_path = data.get('video_path')
            position = data.get('position')
            
            if not video_path:
                api.abort(400, "video_path is required")
            
            queue_manager = get_unified_queue_manager()
            result = queue_manager.enqueue_transcription(video_path, position)
            return result
        except Exception as e:
            logger.error(f"Error enqueueing transcription: {e}")
            api.abort(500, f"Failed to enqueue transcription: {str(e)}")

@workers_ns.route('/')
class WorkerList(Resource):
    """Get worker status information."""
    
    @workers_ns.doc('get_worker_status')
    def get(self):
        """Get detailed worker status information."""
        try:
            queue_manager = get_unified_queue_manager()
            status = queue_manager.get_worker_status()
            return status
        except Exception as e:
            logger.error(f"Error getting worker status: {e}")
            api.abort(500, f"Failed to get worker status: {str(e)}")

@workers_ns.route('/cached-data')
class CachedData(Resource):
    """Get cached data for quick access."""
    
    @workers_ns.doc('get_cached_data')
    def get(self):
        """Get cached data for quick access."""
        try:
            queue_manager = get_unified_queue_manager()
            cached_data = queue_manager.get_cached_data()
            return cached_data
        except Exception as e:
            logger.error(f"Error getting cached data: {e}")
            api.abort(500, f"Failed to get cached data: {str(e)}")

def register_unified_queue_routes(app):
    """Register the unified queue routes with the Flask app."""
    app.register_blueprint(unified_queue_bp)
    logger.info("Registered unified queue management routes")
    return api 