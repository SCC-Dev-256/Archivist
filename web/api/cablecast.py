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
from core.services import VODService
from core.models import TranscriptionResultORM
from core.database import db
from core.security import require_csrf_token

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
        client = VODService().client
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
        client = VODService().client
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
        client = VODService().client
        
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

# Enhanced VOD Management Endpoints

@cablecast_bp.route('/vods', methods=['GET'])
@limiter.limit("100 per hour")
def list_vods():
    """List all Cablecast VODs"""
    try:
        client = VODService().client
        show_id = request.args.get('show_id', type=int)
        vods = client.get_vods(show_id)
        
        return jsonify({
            'success': True,
            'vods': vods,
            'count': len(vods)
        })
        
    except Exception as e:
        logger.error(f"Error listing Cablecast VODs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/vods/<int:vod_id>', methods=['GET'])
@limiter.limit("200 per hour")
def get_vod(vod_id):
    """Get specific Cablecast VOD details"""
    try:
        client = VODService().client
        vod = client.get_vod(vod_id)
        
        if not vod:
            return jsonify({
                'success': False,
                'error': 'VOD not found'
            }), 404
        
        return jsonify({
            'success': True,
            'vod': vod
        })
        
    except Exception as e:
        logger.error(f"Error getting Cablecast VOD {vod_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/vods/<int:vod_id>', methods=['DELETE'])
@limiter.limit("20 per hour")
@require_csrf_token
def delete_vod(vod_id):
    """Delete a Cablecast VOD"""
    try:
        client = VODService().client
        success = client.delete_vod(vod_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'VOD {vod_id} deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete VOD'
            }), 500
        
    except Exception as e:
        logger.error(f"Error deleting Cablecast VOD {vod_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/vods/<int:vod_id>/chapters', methods=['GET'])
@limiter.limit("100 per hour")
def get_vod_chapters(vod_id):
    """Get chapters for a VOD"""
    try:
        client = VODService().client
        chapters = client.get_vod_chapters(vod_id)
        
        return jsonify({
            'success': True,
            'chapters': chapters,
            'count': len(chapters)
        })
        
    except Exception as e:
        logger.error(f"Error getting chapters for VOD {vod_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/vods/<int:vod_id>/chapters', methods=['POST'])
@limiter.limit("50 per hour")
@require_csrf_token
def create_vod_chapter(vod_id):
    """Create a new chapter for a VOD"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Chapter data is required'
            }), 400
        
        client = VODService().client
        chapter = client.create_vod_chapter(vod_id, data)
        
        if chapter:
            return jsonify({
                'success': True,
                'chapter': chapter
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create chapter'
            }), 500
            
    except Exception as e:
        logger.error(f"Error creating chapter for VOD {vod_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/vods/<int:vod_id>/chapters/<int:chapter_id>', methods=['PUT'])
@limiter.limit("50 per hour")
@require_csrf_token
def update_vod_chapter(vod_id, chapter_id):
    """Update a VOD chapter"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Chapter data is required'
            }), 400
        
        client = VODService().client
        success = client.update_vod_chapter(vod_id, chapter_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Chapter {chapter_id} updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update chapter'
            }), 500
        
    except Exception as e:
        logger.error(f"Error updating chapter {chapter_id} for VOD {vod_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/vods/<int:vod_id>/chapters/<int:chapter_id>', methods=['DELETE'])
@limiter.limit("20 per hour")
@require_csrf_token
def delete_vod_chapter(vod_id, chapter_id):
    """Delete a VOD chapter"""
    try:
        client = VODService().client
        success = client.delete_vod_chapter(vod_id, chapter_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Chapter {chapter_id} deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete chapter'
            }), 500
        
    except Exception as e:
        logger.error(f"Error deleting chapter {chapter_id} for VOD {vod_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/locations', methods=['GET'])
@limiter.limit("100 per hour")
def list_locations():
    """List all Cablecast locations"""
    try:
        client = VODService().client
        locations = client.get_locations()
        
        return jsonify({
            'success': True,
            'locations': locations,
            'count': len(locations)
        })
        
    except Exception as e:
        logger.error(f"Error listing Cablecast locations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/qualities', methods=['GET'])
@limiter.limit("100 per hour")
def list_qualities():
    """List all VOD quality settings"""
    try:
        client = VODService().client
        qualities = client.get_vod_qualities()
        
        return jsonify({
            'success': True,
            'qualities': qualities,
            'count': len(qualities)
        })
        
    except Exception as e:
        logger.error(f"Error listing VOD qualities: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/sync/vods', methods=['POST'])
@limiter.limit("10 per hour")
@require_csrf_token
def sync_vods():
    """Sync VODs from Cablecast to local database"""
    try:
        from core.cablecast_integration import CablecastIntegrationService
        
        integration_service = CablecastIntegrationService()
        synced_count = integration_service.sync_vods()
        
        return jsonify({
            'success': True,
            'message': f'Synced {synced_count} VODs from Cablecast',
            'synced_count': synced_count
        })
        
    except Exception as e:
        logger.error(f"Error syncing VODs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/vods/<int:vod_id>/status', methods=['GET'])
@limiter.limit("100 per hour")
def get_vod_status(vod_id):
    """Get detailed status for a VOD"""
    try:
        client = VODService().client
        status = client.get_vod_status(vod_id)
        
        if not status:
            return jsonify({
                'success': False,
                'error': 'VOD status not found'
            }), 404
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting status for VOD {vod_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/vods/<int:vod_id>/metadata', methods=['PUT'])
@limiter.limit("50 per hour")
@require_csrf_token
def update_vod_metadata(vod_id):
    """Update VOD metadata"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Metadata is required'
            }), 400
        
        client = VODService().client
        success = client.update_vod_metadata(vod_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'VOD {vod_id} metadata updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update VOD metadata'
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating metadata for VOD {vod_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/search/shows', methods=['GET'])
@limiter.limit("100 per hour")
def search_shows():
    """Search shows by title or description"""
    try:
        query = request.args.get('q')
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        location_id = request.args.get('location_id', type=int)
        client = VODService().client
        shows = client.search_shows(query, location_id)
        
        return jsonify({
            'success': True,
            'shows': shows,
            'count': len(shows),
            'query': query
        })
        
    except Exception as e:
        logger.error(f"Error searching shows: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/vods/<int:vod_id>/embed', methods=['GET'])
@limiter.limit("200 per hour")
def get_vod_embed(vod_id):
    """Get embed code for a VOD"""
    try:
        client = VODService().client
        embed_code = client.get_vod_embed_code(vod_id)
        
        if embed_code:
            return jsonify({
                'success': True,
                'embed_code': embed_code,
                'vod_id': vod_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Embed code not available'
            }), 404
        
    except Exception as e:
        logger.error(f"Error getting embed code for VOD {vod_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/vods/<int:vod_id>/stream', methods=['GET'])
@limiter.limit("200 per hour")
def get_vod_stream(vod_id):
    """Get streaming URL for a VOD"""
    try:
        client = VODService().client
        stream_url = client.get_vod_stream_url(vod_id)
        
        if stream_url:
            return jsonify({
                'success': True,
                'stream_url': stream_url,
                'vod_id': vod_id
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Stream URL not available'
            }), 404
        
    except Exception as e:
        logger.error(f"Error getting stream URL for VOD {vod_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cablecast_bp.route('/vods/<int:vod_id>/captions', methods=['POST'])
@limiter.limit("50 per hour")
@require_csrf_token
def upload_vod_caption(vod_id):
    """Upload SRT caption file as sidecar to VOD"""
    try:
        # Check if file was uploaded
        if 'caption_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No caption file provided'
            }), 400
        
        caption_file = request.files['caption_file']
        if caption_file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Validate file extension
        if not caption_file.filename.lower().endswith('.srt'):
            return jsonify({
                'success': False,
                'error': 'Only SRT files are supported'
            }), 400
        
        # Save file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.srt') as temp_file:
            caption_file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Upload to Cablecast
            vod_service = VODService()
            success = vod_service.upload_srt_caption(vod_id, temp_path)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Caption file uploaded successfully for VOD {vod_id}',
                    'vod_id': vod_id,
                    'filename': caption_file.filename
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to upload caption file'
                }), 500
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")
        
    except Exception as e:
        logger.error(f"Error uploading caption for VOD {vod_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 