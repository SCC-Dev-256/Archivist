"""Browse API endpoints for Archivist application."""

import concurrent.futures
import glob
import os
from pathlib import Path

from flask_restx import Namespace, Resource, fields

from core.config import NAS_PATH, OUTPUT_DIR, MEMBER_CITIES
from core import BrowseRequest, TranscriptionResultORM, sanitize_output, security_manager
from core.database import db
from core.services import FileService
from flask import Blueprint, jsonify, request, send_file
from flask_limiter import Limiter
from loguru import logger

# Rate limiting configuration
BROWSE_RATE_LIMIT = os.getenv("BROWSE_RATE_LIMIT", "30 per minute")
FILE_OPERATION_RATE_LIMIT = os.getenv("FILE_OPERATION_RATE_LIMIT", "30 per minute")


def create_browse_blueprint(limiter):
    """Create browse blueprint with routes."""
    bp = Blueprint("browse", __name__)

    # Create namespace for API documentation
    ns = Namespace("browse", description="Browse and file operations")

    @bp.route("/browse")
    @limiter.limit(BROWSE_RATE_LIMIT)
    def browse():
        """Browse files and directories. If path is empty, return NAS root."""
        import signal
        
        path = request.args.get('path', '')
        # If path is empty, use NAS_PATH as root
        browse_path = NAS_PATH if not path else os.path.join(NAS_PATH, path)
        
        # Validate path to prevent directory traversal
        if not security_manager.validate_path(browse_path, NAS_PATH):
            logger.warning(f"Invalid path access attempt: {browse_path}")
            return jsonify({'error': 'Invalid path'}), 400
        
        try:
            # Set a timeout for the browse operation to prevent hanging
            def timeout_handler(signum, frame):
                raise TimeoutError("Browse operation timed out")
            
            # Set 10 second timeout for browse operations
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(10)
            
            try:
                contents = FileService().browse_directory(browse_path)
                signal.alarm(0)  # Cancel the alarm
                return jsonify(sanitize_output(contents)), 200
            except TimeoutError:
                logger.error(f"Browse operation timed out for {browse_path}")
                return jsonify({'error': 'Browse operation timed out. Please try again.'}), 408
            finally:
                signal.alarm(0)  # Ensure alarm is cancelled
                
        except Exception as e:
            logger.error(f"Error browsing directory {browse_path}: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route("/transcriptions")
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

    @bp.route("/member-cities")
    @limiter.limit(BROWSE_RATE_LIMIT)
    def get_member_cities():
        """Get information about all member cities and their storage locations."""
        try:
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

    @bp.route("/member-cities/<city_id>")
    @limiter.limit(BROWSE_RATE_LIMIT)
    def get_member_city_info(city_id):
        """Get information about a specific member city."""
        try:
            city_info = MEMBER_CITIES.get(city_id)

            if not city_info:
                return jsonify({"error": "City not found"}), 404

            return jsonify({"success": True, "data": city_info})
        except Exception as e:
            logger.error(f"Error getting city info for {city_id}: {e}")
            return jsonify({"error": "Internal server error"}), 500

    # Swagger model definitions
    browse_request = ns.model(
        "BrowseRequest",
        {
            "path": fields.String(
                description="Path to browse, relative to NAS_PATH", default=""
            )
        },
    )

    return bp, ns
