"""Cablecast API endpoints for Archivist application."""

import os

from flask import Blueprint, g, jsonify, request
from flask_limiter import Limiter
from flask_restx import Namespace, Resource, fields
from loguru import logger

from core.exceptions import (
    APIError,
    CablecastAuthenticationError,
    CablecastError,
    CablecastShowNotFoundError,
    ConnectionError,
    DatabaseError,
    DatabaseQueryError,
    FileNotFoundError,
    NetworkError,
    QueueError,
    RequiredFieldError,
    TaskExecutionError,
    TimeoutError,
    ValidationError,
    VODError,
    create_error_response,
    map_exception_to_http_status
)
from core.models import TranscriptionResultORM
from core.security import require_csrf_token
from core.services import VODService
from core.vod_automation import (
    auto_link_transcription_to_show,
    get_linked_transcriptions,
    get_show_suggestions,
    get_transcription_link_status,
    manual_link_transcription_to_show,
    process_transcription_queue,
    unlink_transcription_from_show
)

# Rate limiting configuration
CABLECAST_RATE_LIMIT = os.getenv('CABLECAST_RATE_LIMIT', '100 per hour')

def create_cablecast_blueprint(limiter):
    """Create cablecast blueprint with routes."""
    bp = Blueprint('cablecast', __name__)
    
    # Create namespace for API documentation
    ns = Namespace('cablecast', description='Cablecast integration operations')
    
    # Swagger model definitions
    link_request = ns.model('LinkRequest', {
        'show_id': fields.Integer(required=True, description='Cablecast show ID')
    })

    @bp.route('/shows', methods=['GET'])
    @limiter.limit(CABLECAST_RATE_LIMIT)
    def list_shows():
        """List all Cablecast shows."""
        try:
            client = VODService().client
            shows = client.list_shows()
            
            return jsonify({
                'success': True,
                'shows': shows,
                'count': len(shows)
            })
            
        except CablecastAuthenticationError as e:
            logger.error(f"Cablecast authentication error: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 401
            
        except ConnectionError as e:
            logger.error(f"Cablecast connection error: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 503
            
        except TimeoutError as e:
            logger.error(f"Cablecast timeout error: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 408
            
        except CablecastError as e:
            logger.error(f"Cablecast error listing shows: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except Exception as e:
            logger.error(f"Unexpected error listing Cablecast shows: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    @bp.route('/shows/<int:show_id>', methods=['GET'])
    @limiter.limit("200 per hour")
    def get_show(show_id):
        """Get specific Cablecast show details"""
        try:
            client = VODService().client
            show = client.get_show(show_id)
            
            if not show:
                raise CablecastShowNotFoundError(str(show_id))
            
            return jsonify({
                'success': True,
                'show': show
            })
            
        except CablecastShowNotFoundError as e:
            logger.error(f"Cablecast show not found: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 404
            
        except CablecastAuthenticationError as e:
            logger.error(f"Cablecast authentication error: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 401
            
        except ConnectionError as e:
            logger.error(f"Cablecast connection error: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 503
            
        except CablecastError as e:
            logger.error(f"Cablecast error getting show {show_id}: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except Exception as e:
            logger.error(f"Unexpected error getting Cablecast show {show_id}: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    @bp.route('/link/<transcription_id>', methods=['POST'])
    @limiter.limit("50 per hour")
    def auto_link_transcription(transcription_id):
        """Automatically link transcription to matching Cablecast show"""
        try:
            # Validate transcription exists
            transcription = TranscriptionResultORM.query.get(transcription_id)
            if not transcription:
                raise FileNotFoundError(f"Transcription with ID {transcription_id}")
            
            # Attempt auto-linking
            result = auto_link_transcription_to_show(transcription_id)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except FileNotFoundError as e:
            logger.error(f"Transcription not found: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 404
            
        except VODError as e:
            logger.error(f"VOD error auto-linking transcription {transcription_id}: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except Exception as e:
            logger.error(f"Unexpected error auto-linking transcription {transcription_id}: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    @bp.route('/link/<transcription_id>/manual', methods=['POST'])
    @limiter.limit("50 per hour")
    def manual_link_transcription(transcription_id):
        """Manually link transcription to specific Cablecast show"""
        try:
            data = request.get_json()
            if not data or 'show_id' not in data:
                raise RequiredFieldError('show_id')
            
            show_id = data['show_id']
            
            # Validate transcription exists
            transcription = TranscriptionResultORM.query.get(transcription_id)
            if not transcription:
                raise FileNotFoundError(f"Transcription with ID {transcription_id}")
            
            # Attempt manual linking
            result = manual_link_transcription_to_show(transcription_id, show_id)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except RequiredFieldError as e:
            logger.error(f"Missing required field: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 400
            
        except FileNotFoundError as e:
            logger.error(f"Transcription not found: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 404
            
        except VODError as e:
            logger.error(f"VOD error manually linking transcription {transcription_id}: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except Exception as e:
            logger.error(f"Unexpected error manually linking transcription {transcription_id}: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    @bp.route('/link/<transcription_id>/status', methods=['GET'])
    @limiter.limit("200 per hour")
    def get_link_status(transcription_id):
        """Get link status for a transcription"""
        try:
            # Validate transcription exists
            transcription = TranscriptionResultORM.query.get(transcription_id)
            if not transcription:
                raise FileNotFoundError(f"Transcription with ID {transcription_id}")
            
            # Get link status
            result = get_transcription_link_status(transcription_id)
            
            if 'error' in result:
                raise VODError(f"Link status error: {result['error']}")
            
            return jsonify({
                'success': True,
                'transcription_id': transcription_id,
                'status': result
            })
            
        except FileNotFoundError as e:
            logger.error(f"Transcription not found: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 404
            
        except VODError as e:
            logger.error(f"VOD error getting link status for transcription {transcription_id}: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except Exception as e:
            logger.error(f"Unexpected error getting link status for transcription {transcription_id}: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    @bp.route('/link/<transcription_id>', methods=['DELETE'])
    @limiter.limit("20 per hour")
    def unlink_transcription(transcription_id):
        """Unlink transcription from its Cablecast show"""
        try:
            # Validate transcription exists
            transcription = TranscriptionResultORM.query.get(transcription_id)
            if not transcription:
                raise FileNotFoundError(f"Transcription with ID {transcription_id}")
            
            # Attempt unlinking
            result = unlink_transcription_from_show(transcription_id)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except FileNotFoundError as e:
            logger.error(f"Transcription not found: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 404
            
        except VODError as e:
            logger.error(f"VOD error unlinking transcription {transcription_id}: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except Exception as e:
            logger.error(f"Unexpected error unlinking transcription {transcription_id}: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    @bp.route('/shows/<int:show_id>/transcriptions', methods=['GET'])
    @limiter.limit("100 per hour")
    def get_show_transcriptions(show_id):
        """Get all transcriptions linked to a specific show"""
        try:
            result = get_linked_transcriptions(show_id)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except CablecastShowNotFoundError as e:
            logger.error(f"Cablecast show not found: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 404
            
        except VODError as e:
            logger.error(f"VOD error getting transcriptions for show {show_id}: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except Exception as e:
            logger.error(f"Unexpected error getting transcriptions for show {show_id}: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    @bp.route('/suggestions/<transcription_id>', methods=['GET'])
    @limiter.limit("100 per hour")
    def get_suggestions(transcription_id):
        """Get suggested Cablecast shows for a transcription"""
        try:
            # Get limit from query parameters
            limit = request.args.get('limit', 5, type=int)
            limit = min(max(limit, 1), 20)  # Clamp between 1 and 20
            
            # Validate transcription exists
            transcription = TranscriptionResultORM.query.get(transcription_id)
            if not transcription:
                raise FileNotFoundError(f"Transcription with ID {transcription_id}")
            
            # Get suggestions
            result = get_show_suggestions(transcription_id, limit)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except FileNotFoundError as e:
            logger.error(f"Transcription not found: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 404
            
        except ValidationError as e:
            logger.error(f"Validation error getting suggestions for transcription {transcription_id}: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 400
            
        except VODError as e:
            logger.error(f"VOD error getting suggestions for transcription {transcription_id}: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except Exception as e:
            logger.error(f"Unexpected error getting suggestions for transcription {transcription_id}: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    @bp.route('/queue/process', methods=['POST'])
    @limiter.limit("10 per hour")
    def process_queue():
        """Process the transcription linking queue"""
        try:
            result = process_transcription_queue()
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except QueueError as e:
            logger.error(f"Queue error processing transcription queue: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except TaskExecutionError as e:
            logger.error(f"Task execution error processing transcription queue: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except Exception as e:
            logger.error(f"Unexpected error processing transcription queue: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    @bp.route('/health', methods=['GET'])
    @limiter.limit("50 per hour")
    def health_check():
        """Check Cablecast API health"""
        try:
            client = VODService().client
            
            # Test basic connectivity
            test_result = client.test_connection()
            
            return jsonify({
                'success': True,
                'status': 'healthy',
                'cablecast_api': 'connected',
                'test_result': test_result
            })
            
        except CablecastAuthenticationError as e:
            logger.error(f"Cablecast authentication error: {e}")
            return jsonify({
                'success': False,
                'status': 'unhealthy',
                'cablecast_api': 'authentication_failed',
                'error': str(e)
            }), 401
            
        except ConnectionError as e:
            logger.error(f"Cablecast connection error: {e}")
            return jsonify({
                'success': False,
                'status': 'unhealthy',
                'cablecast_api': 'connection_failed',
                'error': str(e)
            }), 503
            
        except Exception as e:
            logger.error(f"Unexpected error in health check: {e}")
            return jsonify({
                'success': False,
                'status': 'unhealthy',
                'cablecast_api': 'unknown_error',
                'error': str(e)
            }), 500

    # VOD-related endpoints
    @bp.route('/vods', methods=['GET'])
    @limiter.limit("100 per hour")
    def list_vods():
        """List all VODs"""
        try:
            client = VODService().client
            vods = client.list_vods()
            
            return jsonify({
                'success': True,
                'vods': vods,
                'count': len(vods)
            })
            
        except CablecastAuthenticationError as e:
            logger.error(f"Cablecast authentication error: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 401
            
        except ConnectionError as e:
            logger.error(f"Cablecast connection error: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 503
            
        except CablecastError as e:
            logger.error(f"Cablecast error listing VODs: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except Exception as e:
            logger.error(f"Unexpected error listing VODs: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    @bp.route('/vods/<int:vod_id>', methods=['GET'])
    @limiter.limit("200 per hour")
    def get_vod(vod_id):
        """Get specific VOD details"""
        try:
            client = VODService().client
            vod = client.get_vod(vod_id)
            
            if not vod:
                raise VODError(f"VOD with ID {vod_id} not found", vod_id=str(vod_id))
            
            return jsonify({
                'success': True,
                'vod': vod
            })
            
        except VODError as e:
            logger.error(f"VOD not found: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 404
            
        except CablecastAuthenticationError as e:
            logger.error(f"Cablecast authentication error: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 401
            
        except ConnectionError as e:
            logger.error(f"Cablecast connection error: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 503
            
        except Exception as e:
            logger.error(f"Unexpected error getting VOD {vod_id}: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    @bp.route('/vods/<int:vod_id>', methods=['DELETE'])
    @limiter.limit("20 per hour")
    @require_csrf_token
    def delete_vod(vod_id):
        """Delete a VOD"""
        try:
            client = VODService().client
            result = client.delete_vod(vod_id)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except VODError as e:
            logger.error(f"VOD error deleting VOD {vod_id}: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 500
            
        except CablecastAuthenticationError as e:
            logger.error(f"Cablecast authentication error: {e}")
            error_response = create_error_response(e)
            return jsonify(error_response), 401
            
        except Exception as e:
            logger.error(f"Unexpected error deleting VOD {vod_id}: {e}")
            return jsonify({
                'success': False,
                'error': {
                    'code': 'UNKNOWN_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'original_error': str(e)}
                }
            }), 500

    # Additional VOD endpoints with similar pattern...
    # (Chapters, metadata, etc. would follow the same exception handling pattern)

    return bp

# Legacy blueprint for backward compatibility
cablecast_bp = create_cablecast_blueprint(None) 