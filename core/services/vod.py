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

    @handle_vod_error
    def delete_vod(self, vod_id: int) -> bool:
        """Delete a VOD from Cablecast.
        
        Args:
            vod_id: ID of the VOD to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            success = self.client.delete_vod(vod_id)
            if success:
                logger.info(f"VOD {vod_id} deleted successfully")
            return success
        except Exception as e:
            logger.error(f"Failed to delete VOD {vod_id}: {e}")
            raise VODError(f"VOD deletion failed: {str(e)}")

    @handle_vod_error
    def get_vod_chapters(self, vod_id: int) -> List[Dict]:
        """Get chapters for a VOD.
        
        Args:
            vod_id: ID of the VOD
            
        Returns:
            List of chapter dictionaries
        """
        try:
            chapters = self.client.get_vod_chapters(vod_id)
            logger.info(f"Retrieved {len(chapters)} chapters for VOD {vod_id}")
            return chapters
        except Exception as e:
            logger.error(f"Failed to get VOD chapters: {e}")
            raise VODError(f"Failed to retrieve VOD chapters: {str(e)}")

    @handle_vod_error
    def create_vod_chapter(self, vod_id: int, chapter_data: Dict) -> Optional[Dict]:
        """Create a new chapter for a VOD.
        
        Args:
            vod_id: ID of the VOD
            chapter_data: Chapter data dictionary
            
        Returns:
            Created chapter dictionary or None
        """
        try:
            chapter = self.client.create_vod_chapter(vod_id, chapter_data)
            if chapter:
                logger.info(f"Created chapter for VOD {vod_id}")
            return chapter
        except Exception as e:
            logger.error(f"Failed to create VOD chapter: {e}")
            raise VODError(f"Failed to create VOD chapter: {str(e)}")

    @handle_vod_error
    def update_vod_chapter(self, vod_id: int, chapter_id: int, chapter_data: Dict) -> bool:
        """Update a VOD chapter.
        
        Args:
            vod_id: ID of the VOD
            chapter_id: ID of the chapter
            chapter_data: Updated chapter data
            
        Returns:
            True if update was successful
        """
        try:
            success = self.client.update_vod_chapter(vod_id, chapter_id, chapter_data)
            if success:
                logger.info(f"Updated chapter {chapter_id} for VOD {vod_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to update VOD chapter: {e}")
            raise VODError(f"Failed to update VOD chapter: {str(e)}")

    @handle_vod_error
    def delete_vod_chapter(self, vod_id: int, chapter_id: int) -> bool:
        """Delete a VOD chapter.
        
        Args:
            vod_id: ID of the VOD
            chapter_id: ID of the chapter
            
        Returns:
            True if deletion was successful
        """
        try:
            success = self.client.delete_vod_chapter(vod_id, chapter_id)
            if success:
                logger.info(f"Deleted chapter {chapter_id} for VOD {vod_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete VOD chapter: {e}")
            raise VODError(f"Failed to delete VOD chapter: {str(e)}")

    @handle_vod_error
    def get_locations(self) -> List[Dict]:
        """Get all Cablecast locations.
        
        Returns:
            List of location dictionaries
        """
        try:
            locations = self.client.get_locations()
            logger.info(f"Retrieved {len(locations)} locations from Cablecast")
            return locations
        except Exception as e:
            logger.error(f"Failed to get locations: {e}")
            raise VODError(f"Failed to retrieve locations: {str(e)}")

    @handle_vod_error
    def get_qualities(self) -> List[Dict]:
        """Get all VOD quality settings.
        
        Returns:
            List of quality setting dictionaries
        """
        try:
            qualities = self.client.get_vod_qualities()
            logger.info(f"Retrieved {len(qualities)} quality settings from Cablecast")
            return qualities
        except Exception as e:
            logger.error(f"Failed to get qualities: {e}")
            raise VODError(f"Failed to retrieve qualities: {str(e)}")

    @handle_vod_error
    def search_shows(self, query: str, location_id: Optional[int] = None) -> List[Dict]:
        """Search shows by title or description.
        
        Args:
            query: Search query string
            location_id: Optional location ID to filter results
            
        Returns:
            List of matching show dictionaries
        """
        try:
            shows = self.client.search_shows(query, location_id)
            logger.info(f"Found {len(shows)} shows matching '{query}'")
            return shows
        except Exception as e:
            logger.error(f"Failed to search shows: {e}")
            raise VODError(f"Show search failed: {str(e)}")

    @handle_vod_error
    def get_vod_embed_code(self, vod_id: int) -> Optional[str]:
        """Get embed code for a VOD.
        
        Args:
            vod_id: ID of the VOD
            
        Returns:
            Embed code string or None
        """
        try:
            embed_code = self.client.get_vod_embed_code(vod_id)
            if embed_code:
                logger.debug(f"Retrieved embed code for VOD {vod_id}")
            return embed_code
        except Exception as e:
            logger.error(f"Failed to get VOD embed code: {e}")
            raise VODError(f"Failed to retrieve VOD embed code: {str(e)}")

    @handle_vod_error
    def get_vod_stream_url(self, vod_id: int) -> Optional[str]:
        """Get streaming URL for a VOD.
        
        Args:
            vod_id: ID of the VOD
            
        Returns:
            Stream URL string or None
        """
        try:
            stream_url = self.client.get_vod_stream_url(vod_id)
            if stream_url:
                logger.debug(f"Retrieved stream URL for VOD {vod_id}")
            return stream_url
        except Exception as e:
            logger.error(f"Failed to get VOD stream URL: {e}")
            raise VODError(f"Failed to retrieve VOD stream URL: {str(e)}")

    @handle_vod_error
    def get_vod_analytics(self, vod_id: int) -> Optional[Dict]:
        """Get analytics data for a VOD.
        
        Args:
            vod_id: ID of the VOD
            
        Returns:
            Analytics data dictionary or None
        """
        try:
            analytics = self.client.get_vod_analytics(vod_id)
            if analytics:
                logger.debug(f"Retrieved analytics for VOD {vod_id}")
            return analytics
        except Exception as e:
            logger.error(f"Failed to get VOD analytics: {e}")
            raise VODError(f"Failed to retrieve VOD analytics: {str(e)}") 