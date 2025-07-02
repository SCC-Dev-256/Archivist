"""VOD Content Manager for Archivist to Cablecast integration.

This module orchestrates the content flow from Archivist to the VOD system,
handling transcription processing, metadata extraction, and content publishing.

Key Features:
- Automatic content processing
- Transcription integration
- Metadata extraction
- Error handling and retry logic

Example:
    >>> from core.vod_content_manager import VODContentManager
    >>> manager = VODContentManager()
    >>> result = manager.process_archivist_content_for_vod("transcription_id_123")
"""

import os
import subprocess
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
from core.models import TranscriptionResultORM, CablecastShowORM, CablecastVODORM
from core.app import db
from core.config import CABLECAST_LOCATION_ID, VOD_DEFAULT_QUALITY
from core.cablecast_client import CablecastAPIClient

class VODContentManager:
    """Manages content flow from Archivist to VOD system"""
    
    def __init__(self):
        self.cablecast_client = CablecastAPIClient()
        self.location_id = CABLECAST_LOCATION_ID
    
    def process_archivist_content_for_vod(self, transcription_id: str) -> Optional[Dict]:
        """
        Process Archivist transcription and create VOD content in Cablecast
        
        Args:
            transcription_id: ID of the transcription to process
            
        Returns:
            Dict containing show_id, vod_id, title, and transcription_id if successful
        """
        try:
            # Get transcription result
            transcription = TranscriptionResultORM.query.get(transcription_id)
            if not transcription:
                logger.error(f"Transcription {transcription_id} not found")
                return None
            
            # Extract metadata from transcription
            video_path = transcription.video_path
            video_name = os.path.basename(video_path)
            video_title = os.path.splitext(video_name)[0]
            
            # Get video duration
            duration = self._get_video_duration(video_path)
            
            # Create show in Cablecast
            show_data = {
                'title': video_title,
                'description': f'Transcribed content from Archivist: {video_title}',
                'length': duration,
                'location': self.location_id
            }
            
            show_response = self.cablecast_client.create_show(show_data)
            if not show_response:
                logger.error(f"Failed to create show in Cablecast for {video_title}")
                return None
            
            show_id = show_response['id']
            
            # Create VOD for the show
            vod_data = {
                'show': show_id,
                'quality': self._get_default_quality_id(),
                'fileName': f"{video_title}.mp4"
            }
            
            vod_response = self.cablecast_client.create_vod(vod_data)
            if not vod_response:
                logger.error(f"Failed to create VOD in Cablecast for show {show_id}")
                return None
            
            vod_id = vod_response['id']
            
            # Store relationship in database
            cablecast_show = CablecastShowORM(
                cablecast_id=show_id,
                title=video_title,
                description=show_data['description'],
                duration=duration,
                transcription_id=transcription_id
            )
            db.session.add(cablecast_show)
            
            # Flush to get the show ID
            db.session.flush()
            
            # Create VOD record
            cablecast_vod = CablecastVODORM(
                id=vod_id,
                show_id=cablecast_show.id,
                quality=vod_data['quality'],
                file_name=vod_data['fileName'],
                length=duration,
                vod_state='processing'
            )
            db.session.add(cablecast_vod)
            
            db.session.commit()
            
            logger.info(f"Successfully created VOD content for {video_title}")
            return {
                'show_id': show_id,
                'vod_id': vod_id,
                'title': video_title,
                'transcription_id': transcription_id
            }
            
        except Exception as e:
            logger.error(f"Error processing content for VOD: {e}")
            db.session.rollback()
            return None
    
    def sync_shows_from_cablecast(self, location_id: int = None) -> int:
        """
        Sync shows from Cablecast to Archivist database
        
        Args:
            location_id: Optional location ID to filter shows
            
        Returns:
            Number of shows synced
        """
        try:
            shows = self.cablecast_client.get_shows(location_id or self.location_id)
            synced_count = 0
            
            for show_data in shows:
                # Check if show already exists
                existing_show = CablecastShowORM.query.filter_by(
                    cablecast_id=show_data['id']
                ).first()
                
                if not existing_show:
                    show = CablecastShowORM(
                        cablecast_id=show_data['id'],
                        title=show_data.get('title', ''),
                        description=show_data.get('description', ''),
                        duration=show_data.get('length')
                    )
                    db.session.add(show)
                    synced_count += 1
                else:
                    # Update existing show
                    existing_show.title = show_data.get('title', existing_show.title)
                    existing_show.description = show_data.get('description', existing_show.description)
                    existing_show.duration = show_data.get('length', existing_show.duration)
                    existing_show.updated_at = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Synced {synced_count} new shows from Cablecast")
            return synced_count
        except Exception as e:
            logger.error(f"Error syncing shows: {e}")
            db.session.rollback()
            return 0
    
    def sync_vods_from_cablecast(self, show_id: int = None) -> int:
        """
        Sync VODs from Cablecast to Archivist database
        
        Args:
            show_id: Optional show ID to filter VODs
            
        Returns:
            Number of VODs synced
        """
        try:
            vods = self.cablecast_client.get_vods(show_id)
            synced_count = 0
            
            for vod_data in vods:
                # Check if VOD already exists
                existing_vod = CablecastVODORM.query.filter_by(id=vod_data['id']).first()
                
                if not existing_vod:
                    # Find corresponding show
                    show = CablecastShowORM.query.filter_by(
                        cablecast_id=vod_data['show']
                    ).first()
                    
                    if show:
                        vod = CablecastVODORM(
                            id=vod_data['id'],
                            show_id=show.id,
                            quality=vod_data['quality'],
                            file_name=vod_data.get('fileName', ''),
                            length=vod_data.get('length'),
                            url=vod_data.get('url'),
                            embed_code=vod_data.get('embedCode'),
                            web_vtt_url=vod_data.get('webVtt'),
                            vod_state=vod_data.get('vodState', 'processing'),
                            percent_complete=vod_data.get('percentComplete')
                        )
                        db.session.add(vod)
                        synced_count += 1
                else:
                    # Update existing VOD
                    existing_vod.vod_state = vod_data.get('vodState', existing_vod.vod_state)
                    existing_vod.percent_complete = vod_data.get('percentComplete', existing_vod.percent_complete)
                    existing_vod.updated_at = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Synced {synced_count} new VODs from Cablecast")
            return synced_count
        except Exception as e:
            logger.error(f"Error syncing VODs: {e}")
            db.session.rollback()
            return 0
    
    def enhance_vod_with_transcription(self, vod_id: int, transcription_id: str) -> bool:
        """
        Enhance VOD content with transcription metadata
        
        Args:
            vod_id: VOD ID to enhance
            transcription_id: Transcription ID to use for enhancement
            
        Returns:
            True if successful, False otherwise
        """
        try:
            transcription = TranscriptionResultORM.query.get(transcription_id)
            if not transcription:
                logger.error(f"Transcription {transcription_id} not found")
                return False
            
            # Read transcription content
            if not os.path.exists(transcription.output_path):
                logger.error(f"Transcription file not found: {transcription.output_path}")
                return False
            
            with open(transcription.output_path, 'r') as f:
                transcription_text = f.read()
            
            # Create enhanced metadata
            metadata = {
                'transcription_available': True,
                'transcription_text': transcription_text,
                'transcription_file': transcription.output_path,
                'transcription_completed_at': transcription.completed_at.isoformat(),
                'searchable_content': transcription_text,
                'content_type': 'transcribed_video',
                'source_system': 'archivist'
            }
            
            # Update VOD metadata in Cablecast
            success = self.cablecast_client.update_vod_metadata(vod_id, metadata)
            if success:
                logger.info(f"Enhanced VOD {vod_id} with transcription metadata")
                return True
            else:
                logger.error(f"Failed to enhance VOD {vod_id} with transcription metadata")
                return False
                
        except Exception as e:
            logger.error(f"Error enhancing VOD metadata: {e}")
            return False
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get sync status between Archivist and VOD system
        
        Returns:
            Dict containing sync statistics
        """
        try:
            # Get counts
            total_transcriptions = TranscriptionResultORM.query.count()
            synced_transcriptions = TranscriptionResultORM.query.join(
                CablecastShowORM
            ).count()
            
            # Get recent sync activity
            recent_syncs = CablecastShowORM.query.order_by(
                CablecastShowORM.created_at.desc()
            ).limit(10).all()
            
            recent_data = [{
                'title': show.title,
                'synced_at': show.created_at.isoformat(),
                'cablecast_id': show.cablecast_id
            } for show in recent_syncs]
            
            return {
                'total_transcriptions': total_transcriptions,
                'synced_transcriptions': synced_transcriptions,
                'sync_percentage': (synced_transcriptions / total_transcriptions * 100) if total_transcriptions > 0 else 0,
                'recent_syncs': recent_data
            }
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                'total_transcriptions': 0,
                'synced_transcriptions': 0,
                'sync_percentage': 0,
                'recent_syncs': []
            }
    
    def _get_video_duration(self, video_path: str) -> Optional[int]:
        """Get video duration using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return int(float(result.stdout.strip()))
        except Exception as e:
            logger.error(f"Error getting video duration: {e}")
        return None
    
    def _get_default_quality_id(self) -> int:
        """Get default VOD quality ID from Cablecast"""
        try:
            qualities = self.cablecast_client.get_vod_qualities()
            if qualities:
                return qualities[0]['id']  # Return first available quality
        except Exception as e:
            logger.error(f"Error getting VOD qualities: {e}")
        return VOD_DEFAULT_QUALITY or 1  # Default fallback
    
    def batch_process_transcriptions(self, transcription_ids: List[str]) -> Dict[str, Any]:
        """
        Process multiple transcriptions for VOD publishing
        
        Args:
            transcription_ids: List of transcription IDs to process
            
        Returns:
            Dict containing results and errors
        """
        results = []
        errors = []
        
        for transcription_id in transcription_ids:
            try:
                result = self.process_archivist_content_for_vod(transcription_id)
                if result:
                    results.append(result)
                else:
                    errors.append(f"Failed to process {transcription_id}")
            except Exception as e:
                errors.append(f"Error processing {transcription_id}: {str(e)}")
        
        return {
            'processed_count': len(results),
            'error_count': len(errors),
            'results': results,
            'errors': errors
        }