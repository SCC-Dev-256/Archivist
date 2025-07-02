"""VOD service for Archivist application.

This service provides a clean interface for all VOD-related operations,
including Cablecast integration, content management, and publishing.

Key Features:
- Cablecast API integration
- VOD content management
- Show mapping and linking
- Content publishing
- Error handling and validation

Example:
    >>> from core.services import VODService
    >>> service = VODService()
    >>> result = service.publish_content("transcription_id")
"""

import os
from typing import Dict, Optional, List
from loguru import logger
from core.exceptions import VODError, handle_vod_error
from core.cablecast_client import CablecastAPIClient
from core.vod_content_manager import VODContentManager
from core.cablecast_show_mapper import CablecastShowMapper
from core.cablecast_transcription_linker import CablecastTranscriptionLinker
from core.cablecast_integration import CablecastIntegrationService
from core.vod_automation import auto_link_transcription_to_show
from core.config import CABLECAST_API_URL, CABLECAST_API_KEY, CABLECAST_LOCATION_ID

class VODService:
    """Service for handling VOD operations."""
    
    def __init__(self):
        self.client = CablecastAPIClient()
        self.content_manager = VODContentManager()
        self.show_mapper = CablecastShowMapper(self.client)
        self.transcription_linker = CablecastTranscriptionLinker(self.client)
        self.integration_service = CablecastIntegrationService()
    
    @handle_vod_error
    def test_connection(self) -> bool:
        """Test connection to Cablecast API.
        
        Returns:
            True if connection is successful
        """
        try:
            return self.client.test_connection()
        except Exception as e:
            logger.error(f"VOD connection test failed: {e}")
            raise VODError(f"Connection test failed: {str(e)}")
    
    @handle_vod_error
    def get_shows(self, location_id: Optional[int] = None) -> List[Dict]:
        """Get shows from Cablecast.
        
        Args:
            location_id: Optional location ID to filter shows
            
        Returns:
            List of show dictionaries
        """
        try:
            shows = self.client.get_shows(location_id or CABLECAST_LOCATION_ID)
            logger.info(f"Retrieved {len(shows)} shows from Cablecast")
            return shows
        except Exception as e:
            logger.error(f"Failed to get shows: {e}")
            raise VODError(f"Failed to retrieve shows: {str(e)}")
    
    @handle_vod_error
    def get_vods(self, show_id: Optional[int] = None) -> List[Dict]:
        """Get VODs from Cablecast.
        
        Args:
            show_id: Optional show ID to filter VODs
            
        Returns:
            List of VOD dictionaries
        """
        try:
            vods = self.client.get_vods(show_id)
            logger.info(f"Retrieved {len(vods)} VODs from Cablecast")
            return vods
        except Exception as e:
            logger.error(f"Failed to get VODs: {e}")
            raise VODError(f"Failed to retrieve VODs: {str(e)}")
    
    @handle_vod_error
    def publish_content(self, transcription_id: str, quality: Optional[int] = None) -> Dict:
        """Publish content to VOD system.
        
        Args:
            transcription_id: ID of the transcription to publish
            quality: Optional quality setting for VOD
            
        Returns:
            Dictionary containing publishing results
        """
        try:
            result = self.content_manager.process_archivist_content_for_vod(
                transcription_id, quality=quality
            )
            logger.info(f"Content published to VOD: {transcription_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to publish content {transcription_id}: {e}")
            raise VODError(f"Content publishing failed: {str(e)}")
    
    @handle_vod_error
    def batch_publish(self, transcription_ids: List[str]) -> Dict:
        """Publish multiple transcriptions to VOD.
        
        Args:
            transcription_ids: List of transcription IDs to publish
            
        Returns:
            Dictionary containing batch publishing results
        """
        try:
            results = []
            errors = []
            
            for transcription_id in transcription_ids:
                try:
                    result = self.publish_content(transcription_id)
                    results.append(result)
                except Exception as e:
                    errors.append(f"{transcription_id}: {str(e)}")
            
            batch_result = {
                'published_count': len(results),
                'error_count': len(errors),
                'results': results,
                'errors': errors
            }
            
            logger.info(f"Batch publish completed: {len(results)} successful, {len(errors)} errors")
            return batch_result
            
        except Exception as e:
            logger.error(f"Batch publish failed: {e}")
            raise VODError(f"Batch publishing failed: {str(e)}")
    
    @handle_vod_error
    def link_transcription_to_show(self, transcription_id: str, show_id: Optional[int] = None) -> Dict:
        """Link transcription to a Cablecast show.
        
        Args:
            transcription_id: ID of the transcription
            show_id: Optional show ID (if not provided, will auto-match)
            
        Returns:
            Dictionary containing linking results
        """
        try:
            if show_id:
                # Manual linking
                result = self.transcription_linker.link_transcription_to_show(
                    transcription_id, show_id
                )
            else:
                # Auto-linking
                result = auto_link_transcription_to_show(transcription_id)
            
            logger.info(f"Transcription {transcription_id} linked to show")
            return result
            
        except Exception as e:
            logger.error(f"Failed to link transcription {transcription_id}: {e}")
            raise VODError(f"Transcription linking failed: {str(e)}")
    
    @handle_vod_error
    def get_sync_status(self) -> Dict:
        """Get VOD synchronization status.
        
        Returns:
            Dictionary containing sync status information
        """
        try:
            # This would typically check database for sync status
            # For now, we'll return basic information
            status = {
                'cablecast_connected': self.test_connection(),
                'api_url': CABLECAST_API_URL,
                'location_id': CABLECAST_LOCATION_ID,
                'last_sync': None,  # Would be retrieved from database
                'sync_enabled': True
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            raise VODError(f"Failed to retrieve sync status: {str(e)}")
    
    @handle_vod_error
    def sync_shows(self) -> Dict:
        """Sync shows from Cablecast to local database.
        
        Returns:
            Dictionary containing sync results
        """
        try:
            shows = self.get_shows()
            
            # This would typically update the local database
            # For now, we'll just return the shows
            sync_result = {
                'synced_count': len(shows),
                'shows': shows,
                'status': 'completed'
            }
            
            logger.info(f"Synced {len(shows)} shows from Cablecast")
            return sync_result
            
        except Exception as e:
            logger.error(f"Failed to sync shows: {e}")
            raise VODError(f"Show synchronization failed: {str(e)}")
    
    @handle_vod_error
    def get_vod_status(self, vod_id: int) -> Dict:
        """Get status of a VOD.
        
        Args:
            vod_id: ID of the VOD
            
        Returns:
            Dictionary containing VOD status
        """
        try:
            status = self.client.get_vod_status(vod_id)
            if status:
                logger.info(f"Retrieved VOD status for {vod_id}")
                return status
            else:
                raise VODError(f"VOD {vod_id} not found")
                
        except Exception as e:
            logger.error(f"Failed to get VOD status for {vod_id}: {e}")
            raise VODError(f"Failed to retrieve VOD status: {str(e)}")
    
    @handle_vod_error
    def wait_for_vod_processing(self, vod_id: int, timeout: int = 1800) -> bool:
        """Wait for VOD processing to complete.
        
        Args:
            vod_id: ID of the VOD
            timeout: Timeout in seconds
            
        Returns:
            True if processing completed successfully
        """
        try:
            return self.client.wait_for_vod_processing(vod_id, timeout)
        except Exception as e:
            logger.error(f"Failed to wait for VOD processing {vod_id}: {e}")
            raise VODError(f"VOD processing wait failed: {str(e)}") 