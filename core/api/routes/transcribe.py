"""Transcription API endpoints for Archivist application."""

from flask import Blueprint, jsonify, request
from flask_restx import Namespace, Resource, fields
from flask_limiter import Limiter
from loguru import logger
import os

from core.services import TranscriptionService, FileService, QueueService
from core.models import TranscribeRequest
from core.security import validate_json_input, sanitize_output, require_csrf_token

# Rate limiting configuration
TRANSCRIBE_RATE_LIMIT = os.getenv('TRANSCRIBE_RATE_LIMIT', '10 per minute')

def create_transcribe_blueprint(limiter):
    """Create transcribe blueprint with routes."""
    bp = Blueprint('transcribe', __name__)
    
    # Create namespace for API documentation
    ns = Namespace('transcribe', description='Transcription operations')
    
    # Swagger model definitions
    transcribe_request = ns.model('TranscribeRequest', {
        'path': fields.String(required=True, description='Path to video file, relative to /mnt'),
        'position': fields.Integer(description='Optional position in queue')
    })

    @bp.route('/transcribe', methods=['POST'])
    @limiter.limit(TRANSCRIBE_RATE_LIMIT)
    @validate_json_input(TranscribeRequest)
    def transcribe():
        """Transcribe a video file."""
        try:
            data = request.get_json()
            video_path = data.get('path')
            position = data.get('position')
            
            # Validate file exists
            if not FileService().validate_path(video_path):
                return jsonify({'error': 'Invalid file path'}), 400
            
            # Enqueue transcription job
            queue_service = QueueService()
            job_id = queue_service.enqueue_transcription(video_path, position)
            
            return jsonify({
                'message': 'Transcription job queued successfully',
                'job_id': job_id,
                'video_path': video_path
            })
        except Exception as e:
            logger.error(f"Error queuing transcription: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/transcribe/batch', methods=['POST'])
    @limiter.limit(TRANSCRIBE_RATE_LIMIT)
    @require_csrf_token
    def transcribe_batch():
        """Transcribe multiple video files."""
        try:
            data = request.get_json()
            video_paths = data.get('paths', [])
            
            if not video_paths:
                return jsonify({'error': 'No video paths provided'}), 400
            
            if len(video_paths) > 10:  # Limit batch size
                return jsonify({'error': 'Maximum 10 files per batch'}), 400
            
            # Validate all paths
            file_service = FileService()
            for path in video_paths:
                if not file_service.validate_path(path):
                    return jsonify({'error': f'Invalid file path: {path}'}), 400
            
            # Enqueue all jobs
            queue_service = QueueService()
            job_ids = []
            
            for video_path in video_paths:
                job_id = queue_service.enqueue_transcription(video_path)
                job_ids.append(job_id)
            
            return jsonify({
                'message': f'Queued {len(job_ids)} transcription jobs',
                'job_ids': job_ids,
                'video_paths': video_paths
            })
        except Exception as e:
            logger.error(f"Error queuing batch transcription: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    return bp, ns 