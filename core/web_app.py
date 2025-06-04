from flask import Flask, Blueprint, render_template, jsonify, request, send_file
from pathlib import Path
import os
import glob
from loguru import logger
from core.config import NAS_PATH, OUTPUT_DIR
from core.transcription import run_whisperx
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
from datetime import datetime
import json
import time
from core.app import db  # Add db import from core.app where it's initialized

# Set up logging
setup_logging()

def register_routes(app, limiter):
    # Initialize API documentation on its own blueprint
    bp_api = Blueprint('api', __name__, url_prefix='/api')

    # Move all function-based endpoints here BEFORE registering the blueprint
    @bp_api.route('/file-details')
    @limiter.limit("30/minute")
    def get_file_details():
        path = request.args.get('path')
        if not path:
            return jsonify({'error': 'Path is required'}), 400
        try:
            details = file_manager.get_file_details(path)
            return jsonify(details)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp_api.route('/transcriptions')
    @limiter.limit("30/minute")
    def get_transcriptions():
        try:
            transcriptions = TranscriptionResultORM.query.order_by(
                TranscriptionResultORM.completed_at.desc()
            ).all()
            return jsonify([{
                'id': t.id,
                'video_path': t.video_path,
                'completed_at': t.completed_at.isoformat(),
                'status': t.status,
                'output_path': t.output_path
            } for t in transcriptions])
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp_api.route('/transcriptions/<transcription_id>/view')
    @limiter.limit("30/minute")
    def view_transcription(transcription_id):
        try:
            transcription = TranscriptionResultORM.query.get_or_404(transcription_id)
            if not os.path.exists(transcription.output_path):
                return jsonify({'error': 'Transcription file not found'}), 404
            return send_file(
                transcription.output_path,
                mimetype='text/plain',
                as_attachment=False
            )
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp_api.route('/transcriptions/<transcription_id>/download')
    @limiter.limit("30/minute")
    def download_transcription(transcription_id):
        try:
            transcription = TranscriptionResultORM.query.get_or_404(transcription_id)
            if not os.path.exists(transcription.output_path):
                return jsonify({'error': 'Transcription file not found'}), 404
            return send_file(
                transcription.output_path,
                mimetype='text/plain',
                as_attachment=True,
                download_name=f"{os.path.basename(transcription.video_path)}.txt"
            )
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @bp_api.route('/transcriptions/<transcription_id>/remove', methods=['DELETE'])
    @limiter.limit("30/minute")
    def remove_transcription(transcription_id):
        try:
            transcription = TranscriptionResultORM.query.get_or_404(transcription_id)
            # Remove the output file if it exists
            if os.path.exists(transcription.output_path):
                os.remove(transcription.output_path)
            # Delete the record from the database
            db.session.delete(transcription)
            db.session.commit()
            return jsonify({'message': 'Transcription removed successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

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
        @limiter.limit("30 per minute")
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
                return ErrorResponse(error=str(e)).dict(), 500

    @ns.route('/transcribe')
    class Transcribe(Resource):
        @limiter.limit("10 per minute")
        def post(self):
            """API endpoint for starting transcription"""
            try:
                # Validate request body
                transcribe_req = TranscribeRequest(**request.json)
                video_path = os.path.join('/mnt', transcribe_req.path)
                
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
                return ErrorResponse(error=str(e)).dict(), 500

    @ns.route('/transcribe/batch')
    class TranscribeBatch(Resource):
        @limiter.limit("10 per minute")
        def post(self):
            """Batch API endpoint for starting transcription on multiple files"""
            try:
                data = request.get_json()
                paths = data.get('paths', [])
                if not isinstance(paths, list) or not paths:
                    return ErrorResponse(error='No files provided').dict(), 400
                queued = []
                errors = []
                for rel_path in paths:
                    video_path = os.path.join('/mnt', rel_path)
                    if not os.path.exists(video_path):
                        errors.append(rel_path)
                        continue
                    try:
                        job_id = queue_manager.enqueue_transcription(video_path, None)
                        queued.append(rel_path)
                    except Exception as e:
                        errors.append(f"{rel_path}: {str(e)}")
                return jsonify({"queued": queued, "errors": errors})
            except Exception as e:
                logger.error(f"Batch transcription error: {e}")
                return ErrorResponse(error=str(e)).dict(), 500

    @ns.route('/queue')
    class Queue(Resource):
        @limiter.limit("60 per minute")
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
                return jsonify(job_statuses)
            except Exception as e:
                logger.error(f"Error getting queue: {e}")
                return ErrorResponse(error=str(e)).dict(), 500

    @ns.route('/queue/reorder')
    class QueueReorder(Resource):
        @limiter.limit("20 per minute")
        def post(self):
            """Reorder a job in the queue"""
            try:
                # Validate request body
                reorder_req = QueueReorderRequest(**request.json)
                
                success = queue_manager.reorder_job(reorder_req.job_id, reorder_req.position)
                if success:
                    return SuccessResponse(status='success').dict()
                return ErrorResponse(error='Failed to reorder job').dict(), 500
            except ValueError as e:
                logger.error(f"Validation error: {e}")
                return ErrorResponse(error=str(e)).dict(), 400
            except Exception as e:
                logger.error(f"Error reordering queue: {e}")
                return ErrorResponse(error=str(e)).dict(), 500

    @ns.route('/queue/stop/<string:job_id>')
    class QueueStop(Resource):
        @limiter.limit("10 per minute")
        def post(self, job_id):
            """Stop a running job"""
            try:
                success = queue_manager.stop_job(job_id)
                if success:
                    return SuccessResponse(status='success').dict()
                return ErrorResponse(error='Failed to stop job').dict(), 500
            except Exception as e:
                logger.error(f"Error stopping job: {e}")
                return ErrorResponse(error=str(e)).dict(), 500

    @ns.route('/queue/pause/<string:job_id>')
    class QueuePause(Resource):
        @limiter.limit("10 per minute")
        def post(self, job_id):
            """Pause a running job"""
            try:
                success = queue_manager.pause_job(job_id)
                if success:
                    return SuccessResponse(status='success').dict()
                return ErrorResponse(error='Failed to pause job').dict(), 500
            except Exception as e:
                logger.error(f"Error pausing job: {e}")
                return ErrorResponse(error=str(e)).dict(), 500

    @ns.route('/queue/resume/<string:job_id>')
    class QueueResume(Resource):
        @limiter.limit("10 per minute")
        def post(self, job_id):
            """Resume a paused job"""
            try:
                success = queue_manager.resume_job(job_id)
                if success:
                    return SuccessResponse(status='success').dict()
                return ErrorResponse(error='Failed to resume job').dict(), 500
            except Exception as e:
                logger.error(f"Error resuming job: {e}")
                return ErrorResponse(error=str(e)).dict(), 500

    @ns.route('/status/<string:job_id>')
    class Status(Resource):
        @limiter.limit("60 per minute")
        def get(self, job_id):
            """Get status of a specific job"""
            try:
                status = queue_manager.get_job_status(job_id)
                if status:
                    return JobStatus(**status).dict()
                return ErrorResponse(error='Job not found').dict(), 404
            except Exception as e:
                logger.error(f"Error getting job status: {e}")
                return ErrorResponse(error=str(e)).dict(), 500

    @ns.route('/download/<path:filepath>')
    class Download(Resource):
        @limiter.limit("30 per minute")
        def get(self, filepath):
            """Download a transcription file"""
            try:
                full_path = os.path.join(OUTPUT_DIR, filepath)
                if not os.path.exists(full_path):
                    return ErrorResponse(error='File not found').dict(), 404
                return send_file(full_path, as_attachment=True)
            except Exception as e:
                logger.error(f"Error downloading file: {e}")
                return ErrorResponse(error=str(e)).dict(), 500

    @ns.route('/queue/remove/<string:job_id>')
    class QueueRemove(Resource):
        @limiter.limit("10 per minute")
        def post(self, job_id):
            """Remove a job from the queue"""
            try:
                success = queue_manager.remove_job(job_id)
                if success:
                    return SuccessResponse(status='success').dict()
                return ErrorResponse(error='Failed to remove job').dict(), 500
            except Exception as e:
                logger.error(f"Error removing job: {e}")
                return ErrorResponse(error=str(e)).dict(), 500

    # Register root and health check routes
    @app.route('/')
    def index():
        """Render the main UI index page"""
        return render_template('index.html')

    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return {'status': 'healthy'}, 200 