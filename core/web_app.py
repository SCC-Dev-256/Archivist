from flask import Flask, Blueprint, render_template, jsonify, request, send_file
from pathlib import Path
import os
import glob
from loguru import logger
from core.config import NAS_PATH, OUTPUT_DIR
from core.transcription import run_whisper_transcription
from core.scc_summarizer import summarize_srt
from core.task_queue import queue_manager
from core.models import (
    BrowseRequest, TranscribeRequest, QueueReorderRequest,
    JobStatus, FileItem, ErrorResponse, SuccessResponse,
    TranscriptionJobORM, TranscriptionResultORM
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api, Resource, Namespace, fields
from core.logging_config import setup_logging
from core.file_manager import file_manager
from core.security import security_manager, validate_json_input, sanitize_output, require_csrf_token, get_csrf_token
from datetime import datetime
import json
import time
from core.app import db  # Add db import from core.app where it's initialized

# Set up logging
setup_logging()

# Rate limiting configuration via environment variables
BROWSE_RATE_LIMIT = os.getenv('BROWSE_RATE_LIMIT', '30 per minute')
TRANSCRIBE_RATE_LIMIT = os.getenv('TRANSCRIBE_RATE_LIMIT', '10 per minute')
QUEUE_RATE_LIMIT = os.getenv('QUEUE_RATE_LIMIT', '60 per minute')
QUEUE_OPERATION_RATE_LIMIT = os.getenv('QUEUE_OPERATION_RATE_LIMIT', '10 per minute')
FILE_OPERATION_RATE_LIMIT = os.getenv('FILE_OPERATION_RATE_LIMIT', '30 per minute')

def register_routes(app, limiter):
    # Initialize API documentation on its own blueprint
    bp_api = Blueprint('api', __name__, url_prefix='/api')

    # CSRF token endpoint for AJAX requests
    @bp_api.route('/csrf-token')
    def get_csrf_token_endpoint():
        """Get CSRF token for AJAX requests"""
        return jsonify({'csrf_token': get_csrf_token()})

    # Move all function-based endpoints here BEFORE registering the blueprint
    @bp_api.route('/file-details')
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    def get_file_details():
        path = request.args.get('path')
        if not path:
            return jsonify({'error': 'Path is required'}), 400
        
        # Validate path to prevent directory traversal
        if not security_manager.validate_path(path, NAS_PATH):
            logger.warning(f"Invalid path access attempt: {path}")
            return jsonify({'error': 'Invalid path'}), 400
        
        try:
            details = file_manager.get_file_details(path)
            return jsonify(sanitize_output(details))
        except Exception as e:
            logger.error(f"Error getting file details: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp_api.route('/transcriptions')
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    def get_transcriptions():
        try:
            transcriptions = TranscriptionResultORM.query.order_by(
                TranscriptionResultORM.completed_at.desc()
            ).all()
            result = [{
                'id': t.id,
                'video_path': t.video_path,
                'completed_at': t.completed_at.isoformat(),
                'status': t.status,
                'output_path': t.output_path
            } for t in transcriptions]
            return jsonify(sanitize_output(result))
        except Exception as e:
            logger.error(f"Error getting transcriptions: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp_api.route('/transcriptions/<transcription_id>/view')
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    def view_transcription(transcription_id):
        try:
            # Validate transcription_id to prevent injection
            if not transcription_id or len(transcription_id) > 36:
                return jsonify({'error': 'Invalid transcription ID'}), 400
            
            transcription = TranscriptionResultORM.query.get_or_404(transcription_id)
            if not os.path.exists(transcription.output_path):
                return jsonify({'error': 'Transcription file not found'}), 404
            
            # Validate file path
            if not security_manager.validate_path(transcription.output_path, OUTPUT_DIR):
                logger.warning(f"Invalid file access attempt: {transcription.output_path}")
                return jsonify({'error': 'Invalid file path'}), 400
            
            return send_file(
                transcription.output_path,
                mimetype='text/plain',
                as_attachment=False
            )
        except Exception as e:
            logger.error(f"Error viewing transcription: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp_api.route('/transcriptions/<transcription_id>/download')
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    def download_transcription(transcription_id):
        try:
            # Validate transcription_id
            if not transcription_id or len(transcription_id) > 36:
                return jsonify({'error': 'Invalid transcription ID'}), 400
            
            transcription = TranscriptionResultORM.query.get_or_404(transcription_id)
            if not os.path.exists(transcription.output_path):
                return jsonify({'error': 'Transcription file not found'}), 404
            
            # Validate file path
            if not security_manager.validate_path(transcription.output_path, OUTPUT_DIR):
                logger.warning(f"Invalid file access attempt: {transcription.output_path}")
                return jsonify({'error': 'Invalid file path'}), 400
            
            return send_file(
                transcription.output_path,
                mimetype='text/plain',
                as_attachment=True,
                download_name=f"{os.path.basename(transcription.video_path)}.txt"
            )
        except Exception as e:
            logger.error(f"Error downloading transcription: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp_api.route('/transcriptions/<transcription_id>/remove', methods=['DELETE'])
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    @require_csrf_token
    def remove_transcription(transcription_id):
        try:
            # Validate transcription_id
            if not transcription_id or len(transcription_id) > 36:
                return jsonify({'error': 'Invalid transcription ID'}), 400
            
            transcription = TranscriptionResultORM.query.get_or_404(transcription_id)
            
            # Validate file path before deletion
            if os.path.exists(transcription.output_path):
                if not security_manager.validate_path(transcription.output_path, OUTPUT_DIR):
                    logger.warning(f"Invalid file deletion attempt: {transcription.output_path}")
                    return jsonify({'error': 'Invalid file path'}), 400
                os.remove(transcription.output_path)
            
            # Delete the record from the database
            db.session.delete(transcription)
            db.session.commit()
            return jsonify({'message': 'Transcription removed successfully'})
        except Exception as e:
            logger.error(f"Error removing transcription: {e}")
            db.session.rollback()
            return jsonify({'error': 'Internal server error'}), 500

    # Now register the blueprint
    api = Api(bp_api, doc='/docs')
    ns = api.namespace('', description='Archivist API')
    app.register_blueprint(bp_api)

    # Model definitions for Swagger docs
    browse_request = ns.model('BrowseRequest', {
        'path': fields.String(description='Path to browse, relative to NAS_PATH', default='')
    })

    transcribe_request = ns.model('TranscribeRequest', {
        'path': fields.String(required=True, description='Path to video file, relative to /mnt'),
        'position': fields.Integer(description='Optional position in queue')
    })

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

    file_item = ns.model('FileItem', {
        'name': fields.String(description='File or directory name'),
        'type': fields.String(description='Item type', enum=['directory', 'file']),
        'path': fields.String(description='Relative path'),
        'size': fields.String(description='File size in MB'),
        'mount': fields.Boolean(description='Whether this is a mount point')
    })

    error_response = ns.model('ErrorResponse', {
        'error': fields.String(description='Error message'),
        'details': fields.Raw(description='Additional error details')
    })

    success_response = ns.model('SuccessResponse', {
        'status': fields.String(description='Status', enum=['success']),
        'job_id': fields.String(description='Job ID if applicable')
    })

    @ns.route('/browse')
    class Browse(Resource):
        @limiter.limit(BROWSE_RATE_LIMIT)
        def get(self):
            try:
                # Validate request parameters
                browse_req = BrowseRequest(path=request.args.get('path', ''))
                
                # Start from NAS_PATH if no path provided
                current_path = browse_req.path
                
                # Handle both absolute and relative paths
                if current_path.startswith('/'):
                    # If absolute path, check if it's within NAS_PATH
                    if not current_path.startswith(NAS_PATH):
                        logger.error(f"Path outside NAS_PATH: {current_path}")
                        return ErrorResponse(error='Path must be within NAS_PATH').dict(), 400
                    full_path = current_path
                else:
                    # For relative paths, join with NAS_PATH
                    full_path = os.path.join(NAS_PATH, current_path)
                
                # Validate path to prevent directory traversal
                if not security_manager.validate_path(current_path, NAS_PATH):
                    logger.warning(f"Directory traversal attempt: {current_path}")
                    return ErrorResponse(error='Invalid path').dict(), 400
                
                if not current_path:
                    # At root: list only flex* directories
                    items = []
                    for item in os.listdir(NAS_PATH):
                        item_path = os.path.join(NAS_PATH, item)
                        if os.path.isdir(item_path) and (item.startswith('flex') or item.startswith('flex-')):
                            rel_path = os.path.relpath(item_path, NAS_PATH)
                            items.append(FileItem(
                                name=item,
                                type='directory',
                                path=rel_path,
                                size=None,
                                mount=True
                            ).dict())
                    return jsonify(sorted(items, key=lambda x: x['name'].lower()))

                if not os.path.exists(full_path):
                    logger.error(f"Path not found: {full_path}")
                    return ErrorResponse(error='Path not found').dict(), 404
                    
                items = []
                for item in os.listdir(full_path):
                    item_path = os.path.join(full_path, item)
                    rel_path = os.path.relpath(item_path, NAS_PATH)
                    
                    logger.info(f"Processing item: {item_path}")
                    logger.info(f"Relative path: {rel_path}")
                    
                    if os.path.isdir(item_path):
                        items.append(FileItem(
                            name=item,
                            type='directory',
                            path=rel_path,
                            size=None,  # Set size to None for directories
                            mount=item.startswith('flex')
                        ).dict())
                    else:
                        # Only include video files
                        if item.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.mpeg', '.mpg')):
                            items.append(FileItem(
                                name=item,
                                type='file',
                                path=rel_path,
                                size=os.path.getsize(item_path)  # Always return bytes
                            ).dict())
                return jsonify(sorted(items, key=lambda x: (x['type'] != 'directory', x['name'].lower())))
            except ValueError as e:
                logger.error(f"Validation error: {e}")
                return ErrorResponse(error=str(e)).dict(), 400
            except Exception as e:
                logger.error(f"Error browsing directory: {e}")
                return ErrorResponse(error='Internal server error').dict(), 500

    @ns.route('/transcribe')
    class Transcribe(Resource):
        @limiter.limit(TRANSCRIBE_RATE_LIMIT)
        @validate_json_input(TranscribeRequest)
        def post(self):
            """API endpoint for starting transcription"""
            try:
                # Get validated data from g context
                transcribe_req = g.validated_data
                video_path = os.path.join('/mnt', transcribe_req.path)
                
                # Validate file path
                if not security_manager.validate_path(transcribe_req.path, '/mnt'):
                    logger.warning(f"Invalid video path: {transcribe_req.path}")
                    return ErrorResponse(error='Invalid video path').dict(), 400
                
                if not os.path.exists(video_path):
                    return ErrorResponse(error='Video file not found').dict(), 404
                
                # Enqueue the processing task
                job_id = queue_manager.enqueue_transcription(video_path, transcribe_req.position)
                return SuccessResponse(status='success', job_id=job_id).dict()
            except ValueError as e:
                logger.error(f"Validation error: {e}")
                return ErrorResponse(error=str(e)).dict(), 400
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                return ErrorResponse(error='Internal server error').dict(), 500

    @ns.route('/transcribe/batch')
    class TranscribeBatch(Resource):
        @limiter.limit(TRANSCRIBE_RATE_LIMIT)
        @require_csrf_token
        def post(self):
            """API endpoint for batch transcription"""
            try:
                data = request.get_json()
                if not data or 'paths' not in data:
                    return ErrorResponse(error='Paths array is required').dict(), 400
                
                paths = data['paths']
                if not isinstance(paths, list):
                    return ErrorResponse(error='Paths must be an array').dict(), 400
                
                queued = []
                errors = []
                
                for path in paths:
                    try:
                        # Validate each path
                        if not security_manager.validate_path(path, '/mnt'):
                            errors.append(f"Invalid path: {path}")
                            continue
                        
                        video_path = os.path.join('/mnt', path)
                        if not os.path.exists(video_path):
                            errors.append(f"File not found: {path}")
                            continue
                        
                        job_id = queue_manager.enqueue_transcription(video_path)
                        queued.append({'path': path, 'job_id': job_id})
                    except Exception as e:
                        errors.append(f"Error processing {path}: {str(e)}")
                
                return jsonify({
                    'queued': queued,
                    'errors': errors
                })
            except Exception as e:
                logger.error(f"Batch transcription error: {e}")
                return ErrorResponse(error='Internal server error').dict(), 500

    @ns.route('/queue')
    class Queue(Resource):
        @limiter.limit(QUEUE_RATE_LIMIT)
        def get(self):
            """Get all jobs in the queue"""
            try:
                jobs = queue_manager.get_all_jobs()
                job_statuses = []
                for job in jobs:
                    try:
                        job_statuses.append(JobStatus(**job).dict())
                    except Exception as e:
                        logger.warning(f"Skipping job due to validation error: {e} | job: {job}")
                        continue
                return jsonify(sanitize_output(job_statuses))
            except Exception as e:
                logger.error(f"Error getting queue: {e}")
                return ErrorResponse(error='Internal server error').dict(), 500

    @ns.route('/queue/reorder')
    class QueueReorder(Resource):
        @limiter.limit(QUEUE_OPERATION_RATE_LIMIT)
        @validate_json_input(QueueReorderRequest)
        @require_csrf_token
        def post(self):
            """Reorder a job in the queue"""
            try:
                # Get validated data from g context
                reorder_req = g.validated_data
                
                # Validate job_id
                if not reorder_req.job_id or len(reorder_req.job_id) > 36:
                    return ErrorResponse(error='Invalid job ID').dict(), 400
                
                success = queue_manager.reorder_job(reorder_req.job_id, reorder_req.position)
                if success:
                    return SuccessResponse(status='success').dict()
                return ErrorResponse(error='Failed to reorder job').dict(), 500
            except ValueError as e:
                logger.error(f"Validation error: {e}")
                return ErrorResponse(error=str(e)).dict(), 400
            except Exception as e:
                logger.error(f"Error reordering queue: {e}")
                return ErrorResponse(error='Internal server error').dict(), 500

    @ns.route('/queue/stop/<string:job_id>')
    class QueueStop(Resource):
        @limiter.limit(QUEUE_OPERATION_RATE_LIMIT)
        @require_csrf_token
        def post(self, job_id):
            """Stop a job in the queue"""
            try:
                # Validate job_id
                if not job_id or len(job_id) > 36:
                    return ErrorResponse(error='Invalid job ID').dict(), 400
                
                success = queue_manager.stop_job(job_id)
                if success:
                    return SuccessResponse(status='success').dict()
                return ErrorResponse(error='Failed to stop job').dict(), 500
            except Exception as e:
                logger.error(f"Error stopping job: {e}")
                return ErrorResponse(error='Internal server error').dict(), 500

    @ns.route('/queue/pause/<string:job_id>')
    class QueuePause(Resource):
        @limiter.limit(QUEUE_OPERATION_RATE_LIMIT)
        @require_csrf_token
        def post(self, job_id):
            """Pause a job in the queue"""
            try:
                # Validate job_id
                if not job_id or len(job_id) > 36:
                    return ErrorResponse(error='Invalid job ID').dict(), 400
                
                success = queue_manager.pause_job(job_id)
                if success:
                    return SuccessResponse(status='success').dict()
                return ErrorResponse(error='Failed to pause job').dict(), 500
            except Exception as e:
                logger.error(f"Error pausing job: {e}")
                return ErrorResponse(error='Internal server error').dict(), 500

    @ns.route('/queue/resume/<string:job_id>')
    class QueueResume(Resource):
        @limiter.limit(QUEUE_OPERATION_RATE_LIMIT)
        @require_csrf_token
        def post(self, job_id):
            """Resume a job in the queue"""
            try:
                # Validate job_id
                if not job_id or len(job_id) > 36:
                    return ErrorResponse(error='Invalid job ID').dict(), 400
                
                success = queue_manager.resume_job(job_id)
                if success:
                    return SuccessResponse(status='success').dict()
                return ErrorResponse(error='Failed to resume job').dict(), 500
            except Exception as e:
                logger.error(f"Error resuming job: {e}")
                return ErrorResponse(error='Internal server error').dict(), 500

    @ns.route('/status/<string:job_id>')
    class Status(Resource):
        @limiter.limit(QUEUE_RATE_LIMIT)
        def get(self, job_id):
            """Get status of a specific job"""
            try:
                # Validate job_id
                if not job_id or len(job_id) > 36:
                    return ErrorResponse(error='Invalid job ID').dict(), 400
                
                status = queue_manager.get_job_status(job_id)
                if status:
                    return JobStatus(**status).dict()
                return ErrorResponse(error='Job not found').dict(), 404
            except Exception as e:
                logger.error(f"Error getting job status: {e}")
                return ErrorResponse(error='Internal server error').dict(), 500

    @ns.route('/download/<path:filepath>')
    class Download(Resource):
        @limiter.limit(FILE_OPERATION_RATE_LIMIT)
        def get(self, filepath):
            """Download a transcription file"""
            try:
                # Validate filepath to prevent directory traversal
                if not security_manager.validate_path(filepath, OUTPUT_DIR):
                    logger.warning(f"Invalid download path: {filepath}")
                    return ErrorResponse(error='Invalid file path').dict(), 400
                
                full_path = os.path.join(OUTPUT_DIR, filepath)
                if not os.path.exists(full_path):
                    return ErrorResponse(error='File not found').dict(), 404
                return send_file(full_path, as_attachment=True)
            except Exception as e:
                logger.error(f"Error downloading file: {e}")
                return ErrorResponse(error='Internal server error').dict(), 500

    @ns.route('/queue/remove/<string:job_id>')
    class QueueRemove(Resource):
        @limiter.limit(QUEUE_OPERATION_RATE_LIMIT)
        @require_csrf_token
        def post(self, job_id):
            """Remove a job from the queue"""
            try:
                # Validate job_id
                if not job_id or len(job_id) > 36:
                    return ErrorResponse(error='Invalid job ID').dict(), 400
                
                success = queue_manager.remove_job(job_id)
                if success:
                    return SuccessResponse(status='success').dict()
                return ErrorResponse(error='Failed to remove job').dict(), 500
            except Exception as e:
                logger.error(f"Error removing job: {e}")
                return ErrorResponse(error='Internal server error').dict(), 500

    # Register root and health check routes
    @app.route('/')
    def index():
        """Render the main UI index page"""
        return render_template('index.html')

    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return {'status': 'healthy'}, 200 