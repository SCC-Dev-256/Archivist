"""Cablecast Integration Automation for Archivist.

This module handles the automated linking of transcriptions to existing
Cablecast shows, including show discovery, transcription linking, and
metadata enhancement.

Key Features:
- Automatic show discovery and matching
- Transcription-to-show linking
- Metadata enhancement
- Manual linking support
- Status tracking and monitoring

Example:
    >>> from core.vod_automation import auto_link_transcription_to_show
    >>> result = auto_link_transcription_to_show("transcription_id")
"""

import os
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from loguru import logger
from core.cablecast_show_mapper import CablecastShowMapper
from core.cablecast_transcription_linker import CablecastTranscriptionLinker
from core.models import TranscriptionResultORM, CablecastShowORM
from core.app import db

def auto_link_transcription_to_show(transcription_id: str) -> Dict:
    """
    Automatically link transcription to existing Cablecast show
    
    Args:
        transcription_id: ID of the completed transcription
        
    Returns:
        Dictionary with operation results
    """
    try:
        logger.info(f"Starting auto-link to show for transcription {transcription_id}")
        
        # Get transcription data
        transcription = TranscriptionResultORM.query.get(transcription_id)
        if not transcription:
            logger.error(f"Transcription {transcription_id} not found")
            return {'success': False, 'error': 'Transcription not found'}
        
        if transcription.status != 'completed':
            logger.error(f"Transcription {transcription_id} is not completed (status: {transcription.status})")
            return {'success': False, 'error': 'Transcription not completed'}
        
        # Check if already linked
        existing_link = CablecastShowORM.query.filter_by(
            transcription_id=transcription_id
        ).first()
        
        if existing_link:
            logger.info(f"Transcription {transcription_id} already linked to show {existing_link.cablecast_id}")
            return {
                'success': True,
                'already_linked': True,
                'show_id': existing_link.cablecast_id,
                'message': 'Transcription already linked to show'
            }
        
        # Initialize components
        show_mapper = CablecastShowMapper()
        linker = CablecastTranscriptionLinker()
        
        # Prepare transcription metadata
        transcription_metadata = {
            'duration': 0,  # Will be calculated from SCC file
            'segments': 0,
            'file_path': transcription.video_path
        }
        
        # Calculate duration from SCC file if available
        if os.path.exists(transcription.output_path):
            try:
                with open(transcription.output_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.strip().split('\n')
                    
                    # Find the last timestamp in SCC format
                    last_timestamp = None
                    segment_count = 0
                    
                    for line in lines:
                        line = line.strip()
                        # SCC timestamp format: HH:MM:SS:FF or HH:MM:SS;FF
                        import re
                        if re.match(r'\d{2}:\d{2}:\d{2}[:;]\d{2}', line):
                            timestamp = line.split('\t')[0]  # Get timestamp part
                            last_timestamp = timestamp
                            segment_count += 1
                    
                    if last_timestamp:
                        # Parse SMPTE timestamp to get duration
                        # Format: HH:MM:SS:FF or HH:MM:SS;FF
                        time_part = last_timestamp.replace(';', ':')  # Handle drop frame
                        parts = time_part.split(':')
                        if len(parts) >= 4:
                            hours = int(parts[0])
                            minutes = int(parts[1])
                            seconds = int(parts[2])
                            frames = int(parts[3])
                            # Convert frames to seconds (assuming 29.97 fps)
                            frame_seconds = frames / 29.97
                            duration = hours * 3600 + minutes * 60 + seconds + frame_seconds
                            transcription_metadata['duration'] = duration
                    
                    transcription_metadata['segments'] = segment_count
                    
            except Exception as e:
                logger.warning(f"Could not calculate duration from SCC: {e}")
        
        # Find matching show
        show_id = show_mapper.find_matching_show(transcription.video_path, transcription_metadata)
        
        if not show_id:
            logger.info(f"No matching show found for transcription {transcription_id}")
            return {
                'success': True,
                'linked': False,
                'message': 'No matching show found - manual linking required',
                'suggestions': show_mapper.get_show_suggestions(transcription.video_path)
            }
        
        # Link transcription to show
        link_success = linker.link_transcription_to_show(transcription_id, show_id)
        
        if link_success:
            logger.info(f"Successfully linked transcription {transcription_id} to show {show_id}")
            return {
                'success': True,
                'linked': True,
                'show_id': show_id,
                'message': 'Transcription successfully linked to show'
            }
        else:
            logger.error(f"Failed to link transcription {transcription_id} to show {show_id}")
            return {
                'success': False,
                'error': 'Failed to link transcription to show'
            }
        
    except Exception as e:
        logger.error(f"Error in auto-link to show: {e}")
        return {'success': False, 'error': str(e)}

def manual_link_transcription_to_show(transcription_id: str, show_id: int) -> Dict:
    """
    Manually link transcription to a specific Cablecast show
    
    Args:
        transcription_id: ID of the transcription
        show_id: ID of the Cablecast show
        
    Returns:
        Dictionary with operation results
    """
    try:
        logger.info(f"Manually linking transcription {transcription_id} to show {show_id}")
        
        # Initialize linker
        linker = CablecastTranscriptionLinker()
        
        # Link transcription to show
        success = linker.link_transcription_to_show(transcription_id, show_id)
        
        if success:
            logger.info(f"Successfully manually linked transcription {transcription_id} to show {show_id}")
            return {
                'success': True,
                'show_id': show_id,
                'message': 'Transcription successfully linked to show'
            }
        else:
            logger.error(f"Failed to manually link transcription {transcription_id} to show {show_id}")
            return {
                'success': False,
                'error': 'Failed to link transcription to show'
            }
        
    except Exception as e:
        logger.error(f"Error in manual link to show: {e}")
        return {'success': False, 'error': str(e)}

def get_show_suggestions(transcription_id: str, limit: int = 5) -> Dict:
    """
    Get suggested Cablecast shows for a transcription
    
    Args:
        transcription_id: ID of the transcription
        limit: Maximum number of suggestions
        
    Returns:
        Dictionary with suggested shows
    """
    try:
        # Get transcription data
        transcription = TranscriptionResultORM.query.get(transcription_id)
        if not transcription:
            return {'success': False, 'error': 'Transcription not found'}
        
        # Get suggestions
        show_mapper = CablecastShowMapper()
        suggestions = show_mapper.get_show_suggestions(transcription.video_path, limit)
        
        return {
            'success': True,
            'suggestions': suggestions,
            'transcription_id': transcription_id
        }
        
    except Exception as e:
        logger.error(f"Error getting show suggestions: {e}")
        return {'success': False, 'error': str(e)}

def get_transcription_link_status(transcription_id: str) -> Dict:
    """
    Get link status for a transcription
    
    Args:
        transcription_id: ID of the transcription
        
    Returns:
        Dictionary with link status information
    """
    try:
        # Check if linked
        link = CablecastShowORM.query.filter_by(transcription_id=transcription_id).first()
        
        if not link:
            return {
                'linked': False,
                'message': 'Transcription not linked to any show'
            }
        
        return {
            'linked': True,
            'show_id': link.cablecast_id,
            'show_title': link.title,
            'linked_at': link.created_at.isoformat(),
            'enhanced': True
        }
        
    except Exception as e:
        logger.error(f"Error getting transcription link status: {e}")
        return {'error': str(e)}

def unlink_transcription_from_show(transcription_id: str) -> Dict:
    """
    Unlink transcription from its Cablecast show
    
    Args:
        transcription_id: ID of the transcription
        
    Returns:
        Dictionary with operation results
    """
    try:
        logger.info(f"Unlinking transcription {transcription_id} from show")
        
        # Initialize linker
        linker = CablecastTranscriptionLinker()
        
        # Unlink transcription
        success = linker.unlink_transcription_from_show(transcription_id)
        
        if success:
            logger.info(f"Successfully unlinked transcription {transcription_id}")
            return {
                'success': True,
                'message': 'Transcription successfully unlinked from show'
            }
        else:
            logger.error(f"Failed to unlink transcription {transcription_id}")
            return {
                'success': False,
                'error': 'Failed to unlink transcription from show'
            }
        
    except Exception as e:
        logger.error(f"Error unlinking transcription: {e}")
        return {'success': False, 'error': str(e)}

def get_linked_transcriptions(show_id: int) -> Dict:
    """
    Get all transcriptions linked to a specific show
    
    Args:
        show_id: Cablecast show ID
        
    Returns:
        Dictionary with linked transcriptions
    """
    try:
        # Initialize linker
        linker = CablecastTranscriptionLinker()
        
        # Get linked transcriptions
        transcriptions = linker.get_linked_transcriptions(show_id)
        
        return {
            'success': True,
            'show_id': show_id,
            'transcriptions': transcriptions,
            'count': len(transcriptions)
        }
        
    except Exception as e:
        logger.error(f"Error getting linked transcriptions: {e}")
        return {'success': False, 'error': str(e)}

def process_transcription_queue() -> Dict:
    """
    Process the transcription linking queue
    
    Returns:
        Dictionary with processing results
    """
    try:
        logger.info("Processing transcription linking queue")
        
        # Get completed transcriptions that aren't linked
        completed_transcriptions = TranscriptionResultORM.query.filter_by(
            status='completed'
        ).all()
        
        unlinked_count = 0
        linked_count = 0
        errors = []
        
        for transcription in completed_transcriptions:
            # Check if already linked
            existing_link = CablecastShowORM.query.filter_by(
                transcription_id=transcription.id
            ).first()
            
            if existing_link:
                continue  # Already linked
            
            unlinked_count += 1
            
            try:
                # Attempt auto-linking
                result = auto_link_transcription_to_show(transcription.id)
                
                if result['success'] and result.get('linked', False):
                    linked_count += 1
                    logger.info(f"Successfully auto-linked transcription {transcription.id}")
                elif not result['success']:
                    errors.append(f"Transcription {transcription.id}: {result['error']}")
                    
            except Exception as e:
                error_msg = f"Transcription {transcription.id}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Error processing transcription {transcription.id}: {e}")
        
        return {
            'success': True,
            'processed': linked_count,
            'total_unlinked': unlinked_count,
            'errors': errors,
            'message': f'Linked {linked_count}/{unlinked_count} transcriptions'
        }
        
    except Exception as e:
        logger.error(f"Error processing transcription queue: {e}")
        return {'success': False, 'error': str(e)}

# Legacy function for backward compatibility
def auto_publish_to_vod(transcription_id: str) -> Dict:
    """
    Legacy function - now redirects to auto_link_transcription_to_show
    
    Args:
        transcription_id: ID of the completed transcription
        
    Returns:
        Dictionary with operation results
    """
    logger.warning("auto_publish_to_vod is deprecated, use auto_link_transcription_to_show instead")
    return auto_link_transcription_to_show(transcription_id)
