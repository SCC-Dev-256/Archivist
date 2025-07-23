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
from core.database import db

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

    @bp.route('/db-health')
    @limiter.limit('10 per minute')
    def db_health_check():
        """Check database connectivity."""
        try:
            db.session.execute('SELECT 1')
            db.session.commit()
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'message': 'Database connection successful'
            })
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': str(e),
                'message': 'Database connection failed'
            }), 500

    @bp.route('/transcriptions')
    @limiter.limit(FILE_OPERATION_RATE_LIMIT)
    def get_transcriptions():
        """Get list of completed transcriptions."""
        try:
            # Test database connection first
            try:
                db.session.execute('SELECT 1')
                db.session.commit()
            except Exception as db_error:
                logger.warning(f"Database connection failed, returning empty transcriptions list: {db_error}")
                # Return empty list instead of error when database is unavailable
                return jsonify([])
            
            transcriptions = TranscriptionResultORM.query.order_by(
                TranscriptionResultORM.completed_at.desc()
            ).all()
            result = [{
                'id': t.id,
                'video_path': t.video_path,
                'completed_at': t.completed_at.isoformat() if t.completed_at else None,
                'status': t.status,
                'output_path': t.output_path
            } for t in transcriptions]
            return jsonify(sanitize_output(result))
        except Exception as e:
            logger.error(f"Error getting transcriptions: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return empty list instead of error to prevent frontend issues
            return jsonify([])

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

    @bp.route('/browse')
    @limiter.limit(BROWSE_RATE_LIMIT)
    def browse():
        """Browse files and directories. If path is empty, return NAS root."""
        path = request.args.get('path', '')
        # If path is empty, use NAS_PATH as root
        browse_path = NAS_PATH if not path else os.path.join(NAS_PATH, path)
        # Validate path to prevent directory traversal
        if not security_manager.validate_path(browse_path, NAS_PATH):
            logger.warning(f"Invalid path access attempt: {browse_path}")
            return jsonify({'error': 'Invalid path'}), 400
        try:
            contents = FileService().browse_directory(browse_path)
            return jsonify(sanitize_output(contents)), 200
        except Exception as e:
            logger.error(f"Error browsing directory {browse_path}: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/member-cities')
    @limiter.limit(BROWSE_RATE_LIMIT)
    def get_member_cities():
        """Get information about all member cities and their storage locations."""
        try:
            from core.config import MEMBER_CITIES
            return jsonify({
                'success': True,
                'data': {
                    'member_cities': MEMBER_CITIES,
                    'total_cities': len(MEMBER_CITIES)
                }
            })
        except Exception as e:
            logger.error(f"Error getting member cities: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/member-cities/<city_id>')
    @limiter.limit(BROWSE_RATE_LIMIT)
    def get_member_city_info(city_id):
        """Get information about a specific member city."""
        try:
            from core.config import MEMBER_CITIES
            city_info = MEMBER_CITIES.get(city_id)
            
            if not city_info:
                return jsonify({'error': 'City not found'}), 404
                
            return jsonify({
                'success': True,
                'data': city_info
            })
        except Exception as e:
            logger.error(f"Error getting city info for {city_id}: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # Swagger model definitions
    browse_request = ns.model('BrowseRequest', {
        'path': fields.String(description='Path to browse, relative to NAS_PATH', default='')
    })

    return bp, ns 