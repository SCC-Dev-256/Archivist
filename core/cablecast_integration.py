# Add to core/cablecast_integration.py
from typing import Dict, List, Optional
from loguru import logger
from core.cablecast_client import CablecastAPIClient
from core.models import CablecastShowORM, CablecastVODORM, CablecastVODChapterORM
from core.transcription import run_whisper_transcription
from core.app import db
from core.config import CABLECAST_BASE_URL, CABLECAST_API_KEY, CABLECAST_LOCATION_ID
from datetime import datetime
from core.task_queue import queue_manager


class CablecastIntegrationService:
    """Service for integrating Archivist with Cablecast"""
    
    def __init__(self):
        self.client = CablecastAPIClient()
    
    def sync_shows(self, location_id: int = None) -> int:
        """Sync shows from Cablecast to Archivist database"""
        try:
            shows = self.client.get_shows(location_id)
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
    
    def sync_vods(self, show_id: int = None) -> int:
        """Sync VODs from Cablecast to Archivist database"""
        try:
            vods = self.client.get_vods(show_id)
            synced_count = 0
            
            for vod_data in vods:
                # Check if VOD already exists
                existing_vod = CablecastVODORM.query.filter_by(id=vod_data['id']).first()
                
                if not existing_vod:
                    vod = CablecastVODORM(
                        id=vod_data['id'],
                        show_id=vod_data['show'],
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
    
    def transcribe_cablecast_show(self, show_id: int) -> Optional[str]:
        """Transcribe a Cablecast show using Archivist's transcription service"""
        try:
            show = CablecastShowORM.query.filter_by(cablecast_id=show_id).first()
            if not show:
                logger.error(f"Show {show_id} not found in database")
                return None
            
            # Get VODs for the show
            vods = CablecastVODORM.query.filter_by(show_id=show.id).all()
            if not vods:
                logger.error(f"No VODs found for show {show_id}")
                return None
            
            # Use the first available VOD for transcription
            vod = vods[0]
            if not vod.url:
                logger.error(f"No URL available for VOD {vod.id}")
                return None
            
            # Download and transcribe the video
            # This would need to be implemented based on how you want to handle the video files
            # For now, we'll assume the video is accessible via the URL
            
            # Start transcription job
            job_id = queue_manager.enqueue_transcription(vod.url, metadata={
                'cablecast_show_id': show_id,
                'cablecast_vod_id': vod.id,
                'source': 'cablecast'
            })
            
            return job_id
        except Exception as e:
            logger.error(f"Error transcribing Cablecast show {show_id}: {e}")
            return None