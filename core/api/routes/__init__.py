"""API routes initialization for Archivist application."""

from flask import Blueprint, jsonify
from flask_restx import Api, Resource, fields
from flask_limiter import Limiter
from loguru import logger

from core import get_csrf_token
from .browse import create_browse_blueprint
from .transcribe import create_transcribe_blueprint
from .queue import create_queue_blueprint
from .vod import create_vod_blueprint
from .metrics import bp as metrics_bp

def register_routes(app, limiter):
    """Register all API routes with the Flask application."""
    
    # Initialize API documentation on its own blueprint
    bp_api = Blueprint('api', __name__, url_prefix='/api')

    # CSRF token endpoint for AJAX requests
    @bp_api.route('/csrf-token')
    def get_csrf_token_endpoint():
        """Get CSRF token for AJAX requests"""
        return jsonify({'csrf_token': get_csrf_token()})

    # Create main API namespace for documentation
    api = Api(bp_api, doc='/docs')
    ns = api.namespace('', description='Archivist API')

    # Create and register route blueprints
    browse_bp, browse_ns = create_browse_blueprint(limiter)
    transcribe_bp, transcribe_ns = create_transcribe_blueprint(limiter)
    queue_bp, queue_ns = create_queue_blueprint(limiter)
    vod_bp, vod_ns = create_vod_blueprint(limiter)

    # Add all namespaces to the main API
    api.add_namespace(browse_ns)
    api.add_namespace(transcribe_ns)
    api.add_namespace(queue_ns)
    api.add_namespace(vod_ns)

    # Register blueprints
    app.register_blueprint(browse_bp, url_prefix='/api')
    app.register_blueprint(transcribe_bp, url_prefix='/api')
    app.register_blueprint(queue_bp, url_prefix='/api')
    app.register_blueprint(vod_bp, url_prefix='/api')
    app.register_blueprint(metrics_bp, url_prefix='/api')

    # Register main API blueprint
    app.register_blueprint(bp_api)
    
    # Register Cablecast blueprint (if it exists)
    # try:
    #     from web.api.cablecast import cablecast_bp
    #     app.register_blueprint(cablecast_bp)
    # except ImportError:
    #     logger.warning("Cablecast blueprint not found, skipping registration")

    return api 