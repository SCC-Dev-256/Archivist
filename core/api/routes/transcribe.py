"""Transcription API endpoints for Archivist application."""

from flask import Blueprint, jsonify, request, g
from flask_restx import Namespace, Resource, fields
from flask_limiter import Limiter
from loguru import logger
import os
import redis
from kombu.exceptions import OperationalError

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
        logger.info("🔍 DEBUG: transcribe_batch endpoint called")
        logger.info("🔍 DEBUG: Request method: %s", request.method)
        logger.info("🔍 DEBUG: Request path: %s", request.path)
        logger.info("🔍 DEBUG: Request headers: %s", dict(request.headers))
        logger.info("🔍 DEBUG: Request is_json: %s", request.is_json)
        
        if request.is_json:
            try:
                json_data = request.get_json()
                logger.info("🔍 DEBUG: JSON data: %s", json_data)
            except Exception as e:
                logger.error("🔍 DEBUG: JSON parse error: %s", e)
        
        try:
            # Use validated data from Pydantic model
            validated_data = g.validated_data
            video_paths = validated_data.paths
            
            if not video_paths:
                return jsonify({'error': 'No video paths provided'}), 400
            
            if len(video_paths) > 10:  # Limit batch size
                return jsonify({'error': 'Maximum 10 files per batch'}), 400
            
            # Convert relative Flex server paths to absolute paths
            from core.config import MEMBER_CITIES, NAS_PATH
            processed_paths = []
            
            for path in video_paths:
                # Handle Flex server relative paths (../flex-X/...)
                if path.startswith('../flex-') and '/' in path[8:]:
                    # Extract the flex server ID and the rest of the path
                    flex_part = path[3:]  # Remove '../'
                    flex_id_with_hyphen = flex_part.split('/')[0]  # Get flex-X
                    relative_path = '/'.join(flex_part.split('/')[1:])  # Get the rest
                    
                    # Convert flex-X to flexX to match MEMBER_CITIES keys
                    flex_id = flex_id_with_hyphen.replace('-', '')  # Convert flex-1 to flex1
                    
                    # Check if this is a valid Flex server
                    if flex_id in MEMBER_CITIES:
                        # Convert to absolute path
                        absolute_path = os.path.join(MEMBER_CITIES[flex_id]['mount_path'], relative_path)
                        processed_paths.append(absolute_path)
                        logger.info(f"Converted Flex server path: {path} -> {absolute_path}")
                    else:
                        logger.warning(f"Invalid Flex server ID: {flex_id} (from {flex_id_with_hyphen})")
                        continue
                else:
                    # Regular path - assume it's relative to NAS_PATH
                    absolute_path = os.path.join(NAS_PATH, path)
                    processed_paths.append(absolute_path)
                    logger.info(f"Converted regular path: {path} -> {absolute_path}")
            
            if not processed_paths:
                return jsonify({'error': 'No valid video paths provided'}), 400
            
            # Validate all paths
            file_service = FileService()
            valid_paths = []
            invalid_paths = []
            
            for path in processed_paths:
                if file_service.validate_path(path):
                    valid_paths.append(path)
                else:
                    invalid_paths.append(path)
                    logger.warning(f"Invalid file path: {path}")
            
            if not valid_paths:
                return jsonify({'error': 'No valid video paths provided'}), 400
            
            # Use Celery batch transcription task for better integration with captioning workflow
            logger.info(f"Starting Celery batch transcription for {len(valid_paths)} files")
            try:
                # Get the registered task from the Celery app
                from core.tasks import celery_app
                batch_task = celery_app.tasks.get('batch_transcription')
                
                if not batch_task:
                    logger.error("batch_transcription task not found in Celery app")
                    return jsonify({'error': 'Transcription service unavailable'}), 503
                
                # Submit the task
                result = batch_task.delay(valid_paths)
                batch_task_id = result.id
                
            except (OperationalError, redis.exceptions.ConnectionError) as e:
                logger.error(f"Celery broker unavailable: {e}")
                return jsonify({'error': 'Task queue unavailable'}), 503
            except ImportError as e:
                logger.error(f"Failed to import batch_transcription task: {e}")
                return jsonify({'error': 'Transcription service unavailable'}), 503
            except Exception as e:
                logger.error(f"Failed to queue batch transcription: {e}")
                return jsonify({'error': 'Failed to queue transcription'}), 500
            
            # Return response with task ID for tracking
            response_data = {
                'message': f'Batch transcription queued successfully',
                'batch_task_id': batch_task_id,
                'total_files': len(valid_paths),
                'valid_paths': valid_paths,
                'queued': valid_paths
            }
            
            if invalid_paths:
                response_data['errors'] = [f'Invalid file path: {path}' for path in invalid_paths]
                response_data['invalid_paths'] = invalid_paths
            
            logger.info(f"Batch transcription task {batch_task_id} queued for {len(valid_paths)} files")
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Error queuing batch transcription: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    return bp, ns 