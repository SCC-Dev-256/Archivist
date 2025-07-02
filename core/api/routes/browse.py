"""Browse API endpoints for Archivist application."""

from flask import Blueprint, jsonify, request, send_file
from flask_restx import Namespace, Resource, fields
from flask_limiter import Limiter
from loguru import logger
import os
from pathlib import Path
import glob

from core.config import NAS_PATH, OUTPUT_DIR
from core.services import FileService
from core.models import BrowseRequest, TranscriptionResultORM
from core.security import security_manager, sanitize_output
from core.app import db

# Rate limiting configuration
BROWSE_RATE_LIMIT = os.getenv('BROWSE_RATE_LIMIT', '30 per minute')
FILE_OPERATION_RATE_LIMIT = os.getenv('FILE_OPERATION_RATE_LIMIT', '30 per minute')

def create_browse_blueprint(limiter):
    """Create browse blueprint with routes."""
    bp = Blueprint('browse', __name__)
    
    # Create namespace for API documentation
    ns = Namespace('browse', description='Browse and file operations')
    
    @bp.route('/file-details')
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    def get_file_details():
        """Get detailed information about a file."""
        path = request.args.get('path')
        if not path:
            return jsonify({'error': 'Path is required'}), 400
        
        # Validate path to prevent directory traversal
        if not security_manager.validate_path(path, NAS_PATH):
            logger.warning(f"Invalid path access attempt: {path}")
            return jsonify({'error': 'Invalid path'}), 400
        
        try:
            details = FileService().get_file_details(path)
            return jsonify(sanitize_output(details))
        except Exception as e:
            logger.error(f"Error getting file details: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/transcriptions')
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    def get_transcriptions():
        """Get list of completed transcriptions."""
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

    @bp.route('/transcriptions/<transcription_id>/view')
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    def view_transcription(transcription_id):
        """View transcription content."""
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

    @bp.route('/transcriptions/<transcription_id>/download')
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    def download_transcription(transcription_id):
        """Download transcription file."""
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

    @bp.route('/transcriptions/<transcription_id>/remove', methods=['DELETE'])
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    def remove_transcription(transcription_id):
        """Remove transcription record and file."""
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

    @bp.route('/download/<path:filepath>')
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    def download_file(filepath):
        """Download a file from the NAS."""
        try:
            # Validate file path
            if not security_manager.validate_path(filepath, NAS_PATH):
                logger.warning(f"Invalid file download attempt: {filepath}")
                return jsonify({'error': 'Invalid file path'}), 400
            
            full_path = os.path.join(NAS_PATH, filepath)
            if not os.path.exists(full_path):
                return jsonify({'error': 'File not found'}), 404
            
            return send_file(full_path, as_attachment=True)
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # Swagger model definitions
    browse_request = ns.model('BrowseRequest', {
        'path': fields.String(description='Path to browse, relative to NAS_PATH', default='')
    })

    return bp, ns 