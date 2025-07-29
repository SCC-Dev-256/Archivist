"""Queue management API endpoints for Archivist application."""

from flask import Blueprint, jsonify, request
from flask_restx import Namespace, Resource, fields
from flask_limiter import Limiter
from loguru import logger
import os

from core import QueueReorderRequest, JobStatus, validate_json_input, sanitize_output, require_csrf_token
from core.services.queue import QueueService

# Rate limiting configuration
QUEUE_RATE_LIMIT = os.getenv('QUEUE_RATE_LIMIT', '60 per minute')
QUEUE_OPERATION_RATE_LIMIT = os.getenv('QUEUE_OPERATION_RATE_LIMIT', '10 per minute')

def create_queue_blueprint(limiter):
    """Create queue blueprint with routes."""
    bp = Blueprint('queue', __name__)
    
    # Create namespace for API documentation
    ns = Namespace('queue', description='Queue management operations')
    
    # Swagger model definitions
    queue_reorder_request = ns.model('QueueReorderRequest', {
        'job_id': fields.String(required=True, description='ID of the job to reorder'),
        'position': fields.Integer(required=True, description='New position in queue (0-based)')
    })

    job_status = ns.model('JobStatus', {
        'id': fields.String(description='Job ID'),
        'video_path': fields.String(description='Path to video file'),
        'status': fields.String(description='Job status', enum=['queued', 'processing', 'paused', 'completed', 'failed']),
        'progress': fields.Float(description='Progress percentage', min=0, max=100),
        'status_message': fields.String(description='Status message'),
        'error_details': fields.Raw(description='Error details if any'),
        'start_time': fields.Float(description='Job start time'),
        'time_remaining': fields.Float(description='Estimated time remaining'),
        'transcribed_duration': fields.Float(description='Duration transcribed so far'),
        'total_duration': fields.Float(description='Total video duration')
    })

    @bp.route('/queue')
    @limiter.limit(QUEUE_RATE_LIMIT)
    def get_queue():
        """Get current queue status."""
        try:
            queue_service = QueueService()
            queue_status = queue_service.get_queue_status()
            jobs = queue_service.get_all_jobs()
            
            return jsonify({
                'queue_status': queue_status,
                'jobs': jobs
            })
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/queue/reorder', methods=['POST'])
    @limiter.limit(QUEUE_OPERATION_RATE_LIMIT)
    @validate_json_input(QueueReorderRequest)
    @require_csrf_token
    def reorder_queue():
        """Reorder a job in the queue."""
        try:
            data = request.get_json()
            job_id = data.get('job_id')
            position = data.get('position')
            
            queue_service = QueueService()
            success = queue_service.reorder_job(job_id, position)
            
            if success:
                return jsonify({'message': 'Job reordered successfully'})
            else:
                return jsonify({'error': 'Failed to reorder job'}), 400
        except Exception as e:
            logger.error(f"Error reordering job: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/queue/stop/<string:job_id>', methods=['POST'])
    @limiter.limit(QUEUE_OPERATION_RATE_LIMIT)
    @require_csrf_token
    def stop_job(job_id):
        """Stop a running job."""
        try:
            queue_service = QueueService()
            success = queue_service.cancel_job(job_id)
            
            if success:
                return jsonify({'message': 'Job stopped successfully'})
            else:
                return jsonify({'error': 'Failed to stop job'}), 400
        except Exception as e:
            logger.error(f"Error stopping job: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/queue/pause/<string:job_id>', methods=['POST'])
    @limiter.limit(QUEUE_OPERATION_RATE_LIMIT)
    @require_csrf_token
    def pause_job(job_id):
        """Pause a job."""
        try:
            queue_service = QueueService()
            success = queue_service.pause_job(job_id)
            
            if success:
                return jsonify({'message': 'Job paused successfully'})
            else:
                return jsonify({'error': 'Failed to pause job'}), 400
        except Exception as e:
            logger.error(f"Error pausing job: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/queue/resume/<string:job_id>', methods=['POST'])
    @limiter.limit(QUEUE_OPERATION_RATE_LIMIT)
    @require_csrf_token
    def resume_job(job_id):
        """Resume a paused job."""
        try:
            queue_service = QueueService()
            success = queue_service.resume_job(job_id)
            
            if success:
                return jsonify({'message': 'Job resumed successfully'})
            else:
                return jsonify({'error': 'Failed to resume job'}), 400
        except Exception as e:
            logger.error(f"Error resuming job: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/status/<string:job_id>')
    @limiter.limit(QUEUE_RATE_LIMIT)
    def get_job_status(job_id):
        """Get status of a specific job."""
        try:
            queue_service = QueueService()
            status = queue_service.get_job_status(job_id)
            
            if status:
                return jsonify(sanitize_output(status))
            else:
                return jsonify({'error': 'Job not found'}), 404
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/queue/remove/<string:job_id>', methods=['POST'])
    @limiter.limit(QUEUE_OPERATION_RATE_LIMIT)
    @require_csrf_token
    def remove_job(job_id):
        """Remove a job from the queue."""
        try:
            queue_service = QueueService()
            success = queue_service.cancel_job(job_id)
            
            if success:
                return jsonify({'message': 'Job removed successfully'})
            else:
                return jsonify({'error': 'Failed to remove job'}), 400
        except Exception as e:
            logger.error(f"Error removing job: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    return bp, ns 