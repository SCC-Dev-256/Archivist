"""Cablecast API endpoints for show linking and management.

This module provides REST API endpoints for linking Archivist transcriptions
to existing Cablecast shows, including automatic matching, manual linking,
and status management.

Endpoints:
- GET /api/cablecast/shows - List Cablecast shows
- GET /api/cablecast/shows/{show_id} - Get specific show details
- POST /api/cablecast/link/{transcription_id} - Auto-link transcription to show
- POST /api/cablecast/link/{transcription_id}/manual - Manually link to specific show
- GET /api/cablecast/link/{transcription_id}/status - Get link status
- DELETE /api/cablecast/link/{transcription_id} - Unlink transcription
- GET /api/cablecast/shows/{show_id}/transcriptions - Get linked transcriptions
- GET /api/cablecast/suggestions/{transcription_id} - Get show suggestions
- POST /api/cablecast/queue/process - Process linking queue
"""

from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from loguru import logger
from core.vod_automation import (
    auto_link_transcription_to_show,
    manual_link_transcription_to_show,
    get_transcription_link_status,
    unlink_transcription_from_show,
    get_linked_transcriptions,
    get_show_suggestions,
    process_transcription_queue
)
from core.cablecast_client import CablecastAPIClient
from core.models import TranscriptionResultORM
from core.app import db

# Create blueprint
cablecast_bp = Blueprint('cablecast', __name__, url_prefix='/api/cablecast')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@cablecast_bp.route('/shows', methods=['GET'])
@limiter.limit("100 per hour")
def list_shows():
    """List all Cablecast shows"""
    try:
        client = CablecastAPIClient()
        shows = client.get_shows()
        
        return jsonify({
            'success': True,
            'shows': shows,
            'count': len(shows)
        })
        
    except Exception as e:
        logger.error(f"Error listing Cablecast shows: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/shows/<int:show_id>', methods=['GET'])
@limiter.limit("200 per hour")
def get_show(show_id):
    """Get specific Cablecast show details"""
    try:
        client = CablecastAPIClient()
        show = client.get_show(show_id)
        
        if not show:
            return jsonify({
                'success': False,
                'error': 'Show not found'
            }), 404
        
        return jsonify({
            'success': True,
            'show': show
        })
        
    except Exception as e:
        logger.error(f"Error getting Cablecast show {show_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/link/<transcription_id>', methods=['POST'])
@limiter.limit("50 per hour")
def auto_link_transcription(transcription_id):
    """Automatically link transcription to matching Cablecast show"""
    try:
        # Validate transcription exists
        transcription = TranscriptionResultORM.query.get(transcription_id)
        if not transcription:
            return jsonify({
                'success': False,
                'error': 'Transcription not found'
            }), 404
        
        # Attempt auto-linking
        result = auto_link_transcription_to_show(transcription_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error auto-linking transcription {transcription_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/link/<transcription_id>/manual', methods=['POST'])
@limiter.limit("50 per hour")
def manual_link_transcription(transcription_id):
    """Manually link transcription to specific Cablecast show"""
    try:
        data = request.get_json()
        if not data or 'show_id' not in data:
            return jsonify({
                'success': False,
                'error': 'show_id is required'
            }), 400
        
        show_id = data['show_id']
        
        # Validate transcription exists
        transcription = TranscriptionResultORM.query.get(transcription_id)
        if not transcription:
            return jsonify({
                'success': False,
                'error': 'Transcription not found'
            }), 404
        
        # Attempt manual linking
        result = manual_link_transcription_to_show(transcription_id, show_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error manually linking transcription {transcription_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/link/<transcription_id>/status', methods=['GET'])
@limiter.limit("200 per hour")
def get_link_status(transcription_id):
    """Get link status for a transcription"""
    try:
        # Validate transcription exists
        transcription = TranscriptionResultORM.query.get(transcription_id)
        if not transcription:
            return jsonify({
                'success': False,
                'error': 'Transcription not found'
            }), 404
        
        # Get link status
        result = get_transcription_link_status(transcription_id)
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
        
        return jsonify({
            'success': True,
            'transcription_id': transcription_id,
            'status': result
        })
        
    except Exception as e:
        logger.error(f"Error getting link status for transcription {transcription_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/link/<transcription_id>', methods=['DELETE'])
@limiter.limit("20 per hour")
def unlink_transcription(transcription_id):
    """Unlink transcription from its Cablecast show"""
    try:
        # Validate transcription exists
        transcription = TranscriptionResultORM.query.get(transcription_id)
        if not transcription:
            return jsonify({
                'success': False,
                'error': 'Transcription not found'
            }), 404
        
        # Attempt unlinking
        result = unlink_transcription_from_show(transcription_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error unlinking transcription {transcription_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/shows/<int:show_id>/transcriptions', methods=['GET'])
@limiter.limit("100 per hour")
def get_show_transcriptions(show_id):
    """Get all transcriptions linked to a specific show"""
    try:
        result = get_linked_transcriptions(show_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error getting transcriptions for show {show_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/suggestions/<transcription_id>', methods=['GET'])
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
            return jsonify({
                'success': False,
                'error': 'Transcription not found'
            }), 404
        
        # Get suggestions
        result = get_show_suggestions(transcription_id, limit)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error getting suggestions for transcription {transcription_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/queue/process', methods=['POST'])
@limiter.limit("10 per hour")
def process_queue():
    """Process the transcription linking queue"""
    try:
        result = process_transcription_queue()
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error processing transcription queue: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/health', methods=['GET'])
@limiter.limit("50 per hour")
def health_check():
    """Health check for Cablecast integration"""
    try:
        client = CablecastAPIClient()
        
        # Test connection by getting shows
        shows = client.get_shows()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'cablecast_connected': True,
            'shows_count': len(shows),
            'message': 'Cablecast integration is working'
        })
        
    except Exception as e:
        logger.error(f"Cablecast health check failed: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'cablecast_connected': False,
            'error': str(e),
            'message': 'Cablecast integration is not working'
        }), 500 