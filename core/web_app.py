from flask import Flask, render_template, jsonify, request, send_file
from pathlib import Path
import os
import glob
from loguru import logger
from core.config import NAS_PATH, OUTPUT_DIR
from core.transcription import run_whisperx
from core.scc_summarizer import summarize_srt
from core.queue import queue_manager
from core.models import (
    BrowseRequest, TranscribeRequest, QueueReorderRequest,
    JobStatus, FileItem, ErrorResponse, SuccessResponse
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api, Resource, Namespace
from core.logging_config import setup_logging
import json
import time

# Set up logging
setup_logging()

app = Flask(__name__, 
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)

# Initialize API documentation
api = Api(app, doc='/api/docs')
ns = Namespace('api', description='Archivist API')
api.add_namespace(ns)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379/0"
)

def get_flex_mounts():
    """Get all available flex mount points"""
    mounts = []
    # Check both flex and flex- patterns
    for pattern in ['/mnt/flex/*', '/mnt/flex-*']:
        mounts.extend(glob.glob(pattern))
    return sorted(mounts)

@app.route('/')
def index():
    logger.info("Accessing index route")
    try:
        logger.debug(f"Template folder: {app.template_folder}")
        logger.debug(f"Template exists: {os.path.exists(os.path.join(app.template_folder, 'index.html'))}")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index template: {e}")
        return str(e), 500

@ns.route('/browse')
class Browse(Resource):
    @limiter.limit("30 per minute")
    def get(self):
        try:
            # Validate request parameters
            browse_req = BrowseRequest(path=request.args.get('path', ''))
            
            # Start from NAS_PATH if no path provided
            current_path = browse_req.path
            full_path = os.path.join(NAS_PATH, current_path) if current_path else NAS_PATH
            
            logger.info(f"Browsing path: {full_path}")
            logger.info(f"Path exists: {os.path.exists(full_path)}")
            logger.info(f"Is directory: {os.path.isdir(full_path)}")
            
            if not os.path.exists(full_path):
                logger.error(f"Path not found: {full_path}")
                return ErrorResponse(error='Path not found').dict(), 404
                
            items = []
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                rel_path = os.path.relpath(item_path, '/mnt')
                
                logger.info(f"Processing item: {item_path}")
                logger.info(f"Relative path: {rel_path}")
                
                if os.path.isdir(item_path):
                    items.append(FileItem(
                        name=item,
                        type='directory',
                        path=rel_path,
                        mount=item.startswith('flex')
                    ).dict())
                else:
                    # Only include video files
                    if item.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.mpeg', '.mpg')):
                        items.append(FileItem(
                            name=item,
                            type='file',
                            path=rel_path,
                            size=f"{os.path.getsize(item_path) / (1024*1024):.1f} MB"
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

@ns.route('/queue')
class Queue(Resource):
    @limiter.limit("60 per minute")
    def get(self):
        """Get all jobs in the queue"""
        try:
            jobs = queue_manager.get_all_jobs()
            return jsonify([JobStatus(**job).dict() for job in jobs])
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
        """Get the status of a processing job"""
        try:
            status = queue_manager.get_job_status(job_id)
            return JobStatus(**status).dict()
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return ErrorResponse(error=str(e)).dict(), 500

@ns.route('/download/<path:filepath>')
class Download(Resource):
    @limiter.limit("30 per minute")
    def get(self, filepath):
        """API endpoint for downloading files"""
        try:
            # Security check - prevent directory traversal
            if '..' in filepath or filepath.startswith('/'):
                return ErrorResponse(error='Invalid path').dict(), 400
                
            full_path = os.path.join('/mnt', filepath)
            if not os.path.exists(full_path):
                return ErrorResponse(error='File not found').dict(), 404
            return send_file(full_path)
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return ErrorResponse(error=str(e)).dict(), 500

def process_video_task(video_path: str):
    """Process a video file for transcription."""
    try:
        logger.info(f"Starting transcription of {video_path}")
        
        # Run WhisperX transcription
        result = run_whisperx(video_path)
        
        # Get the current job
        job = queue_manager.get_current_job()
        if job:
            job.meta['progress'] = 100
            job.meta['status_message'] = 'Transcription completed'
            job.save_meta()
        
        return result
    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise

# Add error handler for rate limit exceeded
@app.errorhandler(429)
def ratelimit_handler(e):
    return ErrorResponse(
        error="Rate limit exceeded",
        details={
            "limit": e.description,
            "retry_after": e.retry_after
        }
    ).dict(), 429

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 