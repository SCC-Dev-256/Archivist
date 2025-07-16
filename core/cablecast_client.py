"""Cablecast API client for Archivist application.

This module provides a comprehensive interface for interacting with Cablecast's API,
including authentication, VOD management, and SCC caption file uploads.

Key Features:
- HTTP Basic Authentication (username/password)
- VOD (Video On Demand) content management
- SCC (Scenarist Closed Caption) file uploads
- Error handling and retry logic
- Comprehensive logging

Example:
    >>> from core.cablecast_client import CablecastAPIClient
    >>> client = CablecastAPIClient()
    >>> vods = client.get_vods()
    >>> client.upload_scc_file(vod_id, 'captions.scc')
"""

import os
import requests
import base64
from typing import Dict, List, Optional, Any
from loguru import logger
from core.config import (
    CABLECAST_SERVER_URL, CABLECAST_API_KEY, 
    CABLECAST_USER_ID, CABLECAST_PASSWORD,
    REQUEST_TIMEOUT, MAX_RETRIES
)

class CablecastAPIClient:
    """Client for interacting with Cablecast API."""
    
    def __init__(self):
        """Initialize the Cablecast API client."""
        self.base_url = CABLECAST_SERVER_URL.rstrip('/')
        self.api_key = CABLECAST_API_KEY
        self.username = CABLECAST_USER_ID
        self.password = CABLECAST_PASSWORD
        self.session = requests.Session()
        
        # Set up HTTP Basic Authentication
        if self.username and self.password:
            # Create Basic Auth header
            credentials = f"{self.username}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            self.session.headers.update({
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            logger.info("HTTP Basic Authentication configured")
        else:
            logger.warning("Cablecast credentials not provided - authentication may fail")
        
        # Test connection on initialization
        if not self.test_connection():
            logger.error("Failed to connect to Cablecast API - check credentials and server URL")
    
    def test_connection(self) -> bool:
        """Test connection to Cablecast API.
        
        Returns:
            True if connection is successful
        """
        try:
            # Try to get shows as a connection test
            response = self._make_request('GET', '/shows', params={'limit': 1})
            if response is not None:
                logger.info("✓ Cablecast API connection successful")
                return True
            else:
                logger.error("✗ Cablecast API connection failed")
                return False
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return False
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make HTTP request with authentication and retry logic."""
        url = f"{self.base_url}{endpoint}"
        
        # Extract parameters that should be passed as query params, not as kwargs to session.request
        params = kwargs.pop('params', {})
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.request(
                    method, url, 
                    timeout=REQUEST_TIMEOUT,
                    params=params,
                    **kwargs
                )
                
                # Handle authentication errors
                if response.status_code == 401:
                    logger.error("Authentication failed - check username and password")
                    return None
                
                if response.status_code in [200, 201, 204]:
                    if response.content:
                        return response.json()
                    return {}
                else:
                    logger.warning(f"Request failed: {response.status_code} - {response.text}")
                    return None
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{MAX_RETRIES})")
                if attempt == MAX_RETRIES - 1:
                    logger.error("Max retries exceeded")
                    return None
            except Exception as e:
                logger.error(f"Request error: {e}")
                return None
        
        return None
    
    def get_vods(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get list of VODs from Cablecast."""
        try:
            params = {'limit': limit, 'offset': offset}
            response = self._make_request('GET', '/vods', params=params)
            
            if response:
                vods = response.get('vods', [])
                logger.debug(f"Retrieved {len(vods)} VODs")
                return vods
            return []
            
        except Exception as e:
            logger.error(f"Error getting VODs: {e}")
            return []
    
    def get_vod(self, vod_id: int) -> Optional[Dict]:
        """Get specific VOD by ID."""
        try:
            response = self._make_request('GET', f'/vods/{vod_id}')
            if response:
                logger.debug(f"Retrieved VOD {vod_id}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error getting VOD {vod_id}: {e}")
            return None
    
    def search_vods(self, query: str, limit: int = 50) -> List[Dict]:
        """Search VODs by title or description."""
        try:
            params = {'search': query, 'limit': limit}
            response = self._make_request('GET', '/vods', params=params)
            
            if response:
                vods = response.get('vods', [])
                logger.debug(f"Found {len(vods)} VODs matching '{query}'")
                return vods
            return []
            
        except Exception as e:
            logger.error(f"Error searching VODs: {e}")
            return []
    
    def create_vod(self, vod_data: Dict) -> Optional[Dict]:
        """Create a new VOD."""
        try:
            response = self._make_request('POST', '/vods', json=vod_data)
            if response:
                logger.info(f"Created VOD: {response.get('id')}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error creating VOD: {e}")
            return None
    
    def update_vod(self, vod_id: int, vod_data: Dict) -> bool:
        """Update an existing VOD."""
        try:
            response = self._make_request('PUT', f'/vods/{vod_id}', json=vod_data)
            if response is not None:
                logger.info(f"Updated VOD {vod_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating VOD {vod_id}: {e}")
            return False
    
    def delete_vod(self, vod_id: int) -> bool:
        """Delete a VOD."""
        try:
            response = self._make_request('DELETE', f'/vods/{vod_id}')
            if response is not None:
                logger.info(f"Deleted VOD {vod_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting VOD {vod_id}: {e}")
            return False
    
    def get_shows(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get list of shows from Cablecast."""
        try:
            params = {'limit': limit, 'offset': offset}
            response = self._make_request('GET', '/shows', params=params)
            
            if response:
                shows = response.get('shows', [])
                logger.debug(f"Retrieved {len(shows)} shows")
                return shows
            return []
            
        except Exception as e:
            logger.error(f"Error getting shows: {e}")
            return []
    
    def get_show(self, show_id: int) -> Optional[Dict]:
        """Get specific show by ID."""
        try:
            response = self._make_request('GET', f'/shows/{show_id}')
            if response:
                logger.debug(f"Retrieved show {show_id}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error getting show {show_id}: {e}")
            return None
    
    def update_vod_metadata(self, vod_id: int, metadata: Dict) -> bool:
        """Update VOD metadata"""
        try:
            response = self._make_request('PUT', f'/vods/{vod_id}', json=metadata)
            if response is not None:
                logger.info(f"Updated VOD metadata for {vod_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating VOD metadata: {e}")
            return False
    
    def upload_video_file(self, vod_id: int, file_path: str) -> bool:
        """Upload video file for VOD processing"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = self._make_request('POST', f'/vods/{vod_id}/upload', files=files)
                if response is not None:
                    logger.info(f"Uploaded video file for VOD {vod_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error uploading video file: {e}")
            return False

    def upload_scc_file(self, vod_id: int, scc_path: str) -> bool:
        """Upload SCC (Scenarist Closed Caption) file as sidecar to VOD"""
        try:
            with open(scc_path, 'rb') as f:
                files = {'caption': f}
                response = self._make_request('POST', f'/vods/{vod_id}/captions', files=files)
                if response is not None:
                    logger.info(f"Uploaded SCC caption file for VOD {vod_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error uploading SCC file for VOD {vod_id}: {e}")
            return False

    # Legacy method for backward compatibility
    def upload_srt_file(self, vod_id: int, srt_path: str) -> bool:
        """Legacy method that redirects to SCC upload (backward compatibility)"""
        logger.warning("upload_srt_file is deprecated. Use upload_scc_file instead.")
        return self.upload_scc_file(vod_id, srt_path)
    
    # Additional methods for VOD management
    def get_vod_status(self, vod_id: int) -> Optional[Dict]:
        """Get status of a VOD."""
        try:
            response = self._make_request('GET', f'/vods/{vod_id}/status')
            if response:
                logger.debug(f"Retrieved VOD status for {vod_id}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error getting VOD status for {vod_id}: {e}")
            return None
    
    def get_vod_chapters(self, vod_id: int) -> List[Dict]:
        """Get chapters for a VOD."""
        try:
            response = self._make_request('GET', f'/vods/{vod_id}/chapters')
            if response:
                chapters = response.get('chapters', [])
                logger.debug(f"Retrieved {len(chapters)} chapters for VOD {vod_id}")
                return chapters
            return []
        except Exception as e:
            logger.error(f"Error getting VOD chapters for {vod_id}: {e}")
            return []
    
    def create_vod_chapter(self, vod_id: int, chapter_data: Dict) -> Optional[Dict]:
        """Create a new chapter for a VOD."""
        try:
            response = self._make_request('POST', f'/vods/{vod_id}/chapters', json=chapter_data)
            if response:
                logger.info(f"Created chapter for VOD {vod_id}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error creating VOD chapter: {e}")
            return None
    
    def update_vod_chapter(self, vod_id: int, chapter_id: int, chapter_data: Dict) -> bool:
        """Update a VOD chapter."""
        try:
            response = self._make_request('PUT', f'/vods/{vod_id}/chapters/{chapter_id}', json=chapter_data)
            if response is not None:
                logger.info(f"Updated chapter {chapter_id} for VOD {vod_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating VOD chapter: {e}")
            return False
    
    def delete_vod_chapter(self, vod_id: int, chapter_id: int) -> bool:
        """Delete a VOD chapter."""
        try:
            response = self._make_request('DELETE', f'/vods/{vod_id}/chapters/{chapter_id}')
            if response is not None:
                logger.info(f"Deleted chapter {chapter_id} for VOD {vod_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting VOD chapter: {e}")
            return False
    
    def get_locations(self) -> List[Dict]:
        """Get all Cablecast locations."""
        try:
            response = self._make_request('GET', '/locations')
            if response:
                locations = response.get('locations', [])
                logger.debug(f"Retrieved {len(locations)} locations")
                return locations
            return []
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            return []
    
    def get_vod_qualities(self) -> List[Dict]:
        """Get all VOD quality settings."""
        try:
            response = self._make_request('GET', '/qualities')
            if response:
                qualities = response.get('qualities', [])
                logger.debug(f"Retrieved {len(qualities)} quality settings")
                return qualities
            return []
        except Exception as e:
            logger.error(f"Error getting VOD qualities: {e}")
            return []
    
    def search_shows(self, query: str, location_id: Optional[int] = None) -> List[Dict]:
        """Search shows by title or description."""
        try:
            params = {'search': query}
            if location_id:
                params['location_id'] = location_id
            
            response = self._make_request('GET', '/shows', params=params)
            if response:
                shows = response.get('shows', [])
                logger.debug(f"Found {len(shows)} shows matching '{query}'")
                return shows
            return []
        except Exception as e:
            logger.error(f"Error searching shows: {e}")
            return []
    
    def get_vod_embed_code(self, vod_id: int) -> Optional[str]:
        """Get embed code for a VOD."""
        try:
            response = self._make_request('GET', f'/vods/{vod_id}/embed')
            if response:
                embed_code = response.get('embed_code')
                logger.debug(f"Retrieved embed code for VOD {vod_id}")
                return embed_code
            return None
        except Exception as e:
            logger.error(f"Error getting VOD embed code for {vod_id}: {e}")
            return None
    
    def get_vod_stream_url(self, vod_id: int) -> Optional[str]:
        """Get streaming URL for a VOD."""
        try:
            response = self._make_request('GET', f'/vods/{vod_id}/stream')
            if response:
                stream_url = response.get('stream_url')
                logger.debug(f"Retrieved stream URL for VOD {vod_id}")
                return stream_url
            return None
        except Exception as e:
            logger.error(f"Error getting VOD stream URL for {vod_id}: {e}")
            return None
    
    def get_recent_vods(self, city_id: str = None, limit: int = 10) -> List[Dict]:
        """Get recent VODs, optionally filtered by city."""
        try:
            params = {'limit': limit, 'sort': 'created_at', 'order': 'desc'}
            if city_id:
                params['location_id'] = city_id
            
            response = self._make_request('GET', '/vods', params=params)
            
            if response:
                vods = response.get('vods', [])
                logger.debug(f"Retrieved {len(vods)} recent VODs")
                return vods
            return []
            
        except Exception as e:
            logger.error(f"Error getting recent VODs: {e}")
            return []
    
    def get_vod_direct_url(self, vod_id: int) -> Optional[str]:
        """Get direct download URL for a VOD."""
        try:
            response = self._make_request('GET', f'/vods/{vod_id}/download')
            if response:
                direct_url = response.get('direct_url') or response.get('url')
                logger.debug(f"Retrieved direct URL for VOD {vod_id}")
                return direct_url
            return None
        except Exception as e:
            logger.error(f"Error getting VOD direct URL for {vod_id}: {e}")
            return None
    
    def get_vod_captions(self, vod_id: int) -> Optional[Dict]:
        """Get caption information for a VOD."""
        try:
            response = self._make_request('GET', f'/vods/{vod_id}/captions')
            if response:
                captions = response.get('captions') or response.get('scc')
                logger.debug(f"Retrieved captions for VOD {vod_id}")
                return captions
            return None
        except Exception as e:
            logger.error(f"Error getting VOD captions for {vod_id}: {e}")
            return None
    
    def upload_scc_file(self, vod_id: int, scc_file_path: str) -> bool:
        """Upload SCC caption file for a VOD."""
        try:
            with open(scc_file_path, 'rb') as f:
                files = {'scc_file': f}
                response = self._make_request('POST', f'/vods/{vod_id}/captions', files=files)
                if response is not None:
                    logger.info(f"Uploaded SCC file for VOD {vod_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error uploading SCC file for VOD {vod_id}: {e}")
            return False
    
    def update_vod_captions(self, vod_id: int, caption_data: Dict) -> bool:
        """Update caption metadata for a VOD."""
        try:
            response = self._make_request('PUT', f'/vods/{vod_id}/captions', json=caption_data)
            if response is not None:
                logger.info(f"Updated captions for VOD {vod_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating VOD captions for {vod_id}: {e}")
            return False
    
    def get_vod_processing_status(self, vod_id: int) -> Optional[Dict]:
        """Get processing status for a VOD."""
        try:
            response = self._make_request('GET', f'/vods/{vod_id}/status')
            if response:
                status = response.get('status') or response.get('processing_status')
                logger.debug(f"Retrieved processing status for VOD {vod_id}: {status}")
                return status
            return None
        except Exception as e:
            logger.error(f"Error getting VOD processing status for {vod_id}: {e}")
            return None
    
    def wait_for_vod_processing(self, vod_id: int, timeout: int = 1800) -> bool:
        """Wait for VOD processing to complete."""
        try:
            start_time = datetime.now()
            while (datetime.now() - start_time).seconds < timeout:
                status = self.get_vod_processing_status(vod_id)
                if status == 'completed' or status == 'ready':
                    logger.info(f"VOD {vod_id} processing completed")
                    return True
                elif status == 'failed' or status == 'error':
                    logger.error(f"VOD {vod_id} processing failed")
                    return False
                
                time.sleep(30)  # Check every 30 seconds
            
            logger.warning(f"VOD {vod_id} processing timed out after {timeout} seconds")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for VOD processing for {vod_id}: {e}")
            return False
    
    def get_latest_vod(self, city_id: str) -> Optional[Dict]:
        """Get the latest VOD for a specific city."""
        try:
            recent_vods = self.get_recent_vods(city_id, limit=1)
            if recent_vods:
                return recent_vods[0]
            return None
        except Exception as e:
            logger.error(f"Error getting latest VOD for city {city_id}: {e}")
            return None
    
    def create_show(self, show_data: Dict) -> Optional[Dict]:
        """Create a new show in Cablecast."""
        try:
            response = self._make_request('POST', '/shows', json=show_data)
            if response:
                logger.info(f"Created show: {response.get('id')}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error creating show: {e}")
            return None