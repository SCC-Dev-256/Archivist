"""Transcription API endpoints for Archivist application."""

from flask import Blueprint, jsonify, request, g
from flask_restx import Namespace, Resource, fields
from flask_limiter import Limiter
from loguru import logger
import os

from core import TranscribeRequest, BatchTranscribeRequest, validate_json_input, sanitize_output, require_csrf_token
from core.services.file import FileService
from core.services.queue import QueueService
from core.tasks.transcription import batch_transcription

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
    @validate_json_input(BatchTranscribeRequest)
    def transcribe_batch():
        """Transcribe multiple video files using Celery batch processing."""
        try:
            # Use validated data from Pydantic model
            validated_data = g.validated_data
            video_paths = validated_data.paths
            
            if not video_paths:
                return jsonify({'error': 'No video paths provided'}), 400
            
            if len(video_paths) > 10:  # Limit batch size
                return jsonify({'error': 'Maximum 10 files per batch'}), 400
            
            # Validate all paths
            file_service = FileService()
            valid_paths = []
            invalid_paths = []
            
            for path in video_paths:
                if file_service.validate_path(path):
                    valid_paths.append(path)
                else:
                    invalid_paths.append(path)
            
            if not valid_paths:
                return jsonify({'error': 'No valid video paths provided'}), 400
            
            # Use Celery batch transcription task for better integration with captioning workflow
            logger.info(f"Starting Celery batch transcription for {len(valid_paths)} files")
            batch_task = batch_transcription.delay(valid_paths)
            
            # Return response with task ID for tracking
            response_data = {
                'message': f'Batch transcription queued successfully',
                'batch_task_id': batch_task.id,
                'total_files': len(valid_paths),
                'valid_paths': valid_paths,
                'queued': valid_paths
            }
            
            if invalid_paths:
                response_data['errors'] = [f'Invalid file path: {path}' for path in invalid_paths]
                response_data['invalid_paths'] = invalid_paths
            
            logger.info(f"Batch transcription task {batch_task.id} queued for {len(valid_paths)} files")
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Error queuing batch transcription: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    return bp, ns 