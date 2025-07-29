"""VOD API endpoints for Archivist application."""

from flask import Blueprint, jsonify, request
from flask_restx import Namespace, Resource, fields
from flask_limiter import Limiter
from loguru import logger
import os

from core import TranscriptionResultORM, sanitize_output, require_csrf_token
from core.database import db
from core.services.vod import VODService

def create_vod_blueprint(limiter):
    """Create VOD blueprint with routes."""
    bp = Blueprint('vod', __name__)
    
    # Create namespace for API documentation
    ns = Namespace('vod', description='VOD integration operations')

    @bp.route('/vod/publish/<string:transcription_id>', methods=['POST'])
    @limiter.limit('10 per hour')
    @require_csrf_token
    def publish_to_vod(transcription_id):
        """Publish a transcription to VOD."""
        try:
            # Validate transcription_id
            if not transcription_id or len(transcription_id) > 36:
                return jsonify({'error': 'Invalid transcription ID'}), 400
            
            # Get transcription record
            transcription = TranscriptionResultORM.query.get_or_404(transcription_id)
            
            if not os.path.exists(transcription.output_path):
                return jsonify({'error': 'Transcription file not found'}), 404
            
            # Publish to VOD
            vod_service = VODService()
            result = vod_service.publish_content(transcription_id)
            
            if result.get('success'):
                return jsonify({
                    'message': 'Content published to VOD successfully',
                    'vod_id': result.get('vod_id'),
                    'transcription_id': transcription_id
                })
            else:
                return jsonify({
                    'error': 'Failed to publish to VOD',
                    'details': result.get('error')
                }), 500
        except Exception as e:
            logger.error(f"Error publishing to VOD: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/vod/batch-publish', methods=['POST'])
    @limiter.limit('5 per hour')
    @require_csrf_token
    def batch_publish_to_vod():
        """Batch publish multiple transcriptions to VOD."""
        try:
            data = request.get_json()
            transcription_ids = data.get('transcription_ids', [])
            
            if not transcription_ids:
                return jsonify({'error': 'No transcription IDs provided'}), 400
            
            if len(transcription_ids) > 20:  # Limit batch size
                return jsonify({'error': 'Maximum 20 transcriptions per batch'}), 400
            
            # Validate all transcription IDs
            for transcription_id in transcription_ids:
                if not transcription_id or len(transcription_id) > 36:
                    return jsonify({'error': f'Invalid transcription ID: {transcription_id}'}), 400
                
                transcription = TranscriptionResultORM.query.get(transcription_id)
                if not transcription:
                    return jsonify({'error': f'Transcription not found: {transcription_id}'}), 404
                
                if not os.path.exists(transcription.output_path):
                    return jsonify({'error': f'Transcription file not found: {transcription_id}'}), 404
            
            # Publish all to VOD
            vod_service = VODService()
            results = []
            
            for transcription_id in transcription_ids:
                try:
                    result = vod_service.publish_content(transcription_id)
                    results.append({
                        'transcription_id': transcription_id,
                        'success': result.get('success', False),
                        'vod_id': result.get('vod_id'),
                        'error': result.get('error')
                    })
                except Exception as e:
                    logger.error(f"Error publishing transcription {transcription_id}: {e}")
                    results.append({
                        'transcription_id': transcription_id,
                        'success': False,
                        'error': str(e)
                    })
            
            # Count successes and failures
            successful = sum(1 for r in results if r['success'])
            failed = len(results) - successful
            
            return jsonify({
                'message': f'Batch publish completed: {successful} successful, {failed} failed',
                'results': results,
                'summary': {
                    'total': len(results),
                    'successful': successful,
                    'failed': failed
                }
            })
        except Exception as e:
            logger.error(f"Error in batch publish: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @bp.route('/vod/sync-status')
    @limiter.limit('30 per minute')
    def get_vod_sync_status():
        """Get VOD synchronization status."""
        try:
            vod_service = VODService()
            status = vod_service.get_publishing_status()
            
            return jsonify({
                'vod_sync_status': status,
                'last_sync': status.get('last_sync'),
                'pending_publishes': status.get('pending_publishes', 0),
                'failed_publishes': status.get('failed_publishes', 0),
                'connection_status': status.get('connection_status', 'unknown')
            })
        except Exception as e:
            logger.error(f"Error getting VOD sync status: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    return bp, ns 