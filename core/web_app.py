"""Web application module for Archivist.

This module provides the main web application setup and route registration
using the new modular route structure.
"""

from flask import Flask, Blueprint, render_template, jsonify, request, send_file
from pathlib import Path
import os
import glob
from loguru import logger
from core.config import NAS_PATH, OUTPUT_DIR
from core.services import TranscriptionService, VODService, FileService, QueueService
from core.models import (
    BrowseRequest, TranscribeRequest, QueueReorderRequest,
    JobStatus, FileItem, ErrorResponse, SuccessResponse,
    TranscriptionJobORM, TranscriptionResultORM, CablecastShowORM
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api, Resource, Namespace, fields
from core.logging_config import setup_logging
from core.security import security_manager, validate_json_input, sanitize_output, require_csrf_token, get_csrf_token
from datetime import datetime
import json
import time
from core.database import db
from core.cablecast_client import CablecastAPIClient
from core.cablecast_integration import CablecastIntegrationService

# Set up logging
setup_logging()

def register_routes(app, limiter):
    """Register all API routes using the new modular structure."""
    try:
        # Import and use the new modular route structure
        from core.api.routes import register_routes as register_modular_routes
        api = register_modular_routes(app, limiter)
        logger.info("Successfully registered modular API routes")
        
        # Register unified queue management routes
        try:
            from core.api.unified_queue_routes import register_unified_queue_routes
            register_unified_queue_routes(app)
            logger.info("Successfully registered unified queue management routes")
        except ImportError as e:
            logger.warning(f"Failed to import unified queue routes: {e}")
        
        return api
    except ImportError as e:
        logger.error(f"Failed to import modular routes: {e}")
        # Fallback to original implementation if needed
        logger.warning("Falling back to original route implementation")
        return register_legacy_routes(app, limiter)

def register_legacy_routes(app, limiter):
    """Legacy route implementation as fallback."""
    logger.warning("Using legacy route implementation")
    
    # Initialize API documentation on its own blueprint
    bp_api = Blueprint('api', __name__, url_prefix='/api')

    # CSRF token endpoint for AJAX requests
    @bp_api.route('/csrf-token')
    def get_csrf_token_endpoint():
        """Get CSRF token for AJAX requests"""
        return jsonify({'csrf_token': get_csrf_token()})

    # Register the blueprint
    api = Api(bp_api, doc='/docs')
    app.register_blueprint(bp_api)
    
    # Register Cablecast blueprint
    try:
        from web.api.cablecast import cablecast_bp
        app.register_blueprint(cablecast_bp)
    except ImportError:
        logger.warning("Cablecast blueprint not found, skipping registration")

    return api

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    
    # Register routes
    api = register_routes(app, limiter)
    
    # Add main routes that don't fit into specific modules
    @app.route('/')
    def index():
        """Main application index."""
        return jsonify({
            'message': 'Archivist API',
            'version': '1.0.0',
            'status': 'running',
            'documentation': '/api/docs'
        })

    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'transcription': 'available',
                'file': 'available',
                'queue': 'available',
                'vod': 'available'
            }
        })

    return app, limiter, api 