"""Cablecast API client for VOD integration.

This module provides a client for interacting with the Cablecast API system,
handling authentication, content management, and VOD operations.

Key Features:
- Authentication and session management
- Show and VOD creation
- File upload and processing
- Status monitoring
- Metadata management

Example:
    >>> from core.cablecast_client import CablecastAPIClient
    >>> client = CablecastAPIClient()
    >>> shows = client.get_shows()
    >>> vods = client.get_vods(show_id=123)
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
from loguru import logger
from core.config import CABLECAST_API_URL, CABLECAST_API_KEY

class CablecastAPIClient:
    """Client for interacting with Cablecast API"""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or CABLECAST_API_URL
        self.api_key = api_key or CABLECAST_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        
        # Configure session for better reliability
        self.session.timeout = 30
        self.session.max_retries = 3
        
        logger.info(f"Initialized Cablecast API client for {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make HTTP request to Cablecast API with retry logic and error handling"""
        from core.config import VOD_MAX_RETRIES, VOD_RETRY_DELAY
        
        for attempt in range(VOD_MAX_RETRIES):
            try:
                url = f"{self.base_url}{endpoint}"
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1}/{VOD_MAX_RETRIES})")
                
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                
                if response.content:
                    return response.json()
                return {}
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"API request failed (attempt {attempt + 1}/{VOD_MAX_RETRIES}): {e}")
                if attempt < VOD_MAX_RETRIES - 1:
                    # Exponential backoff
                    delay = VOD_RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"API request failed after {VOD_MAX_RETRIES} attempts: {e}")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error in API request: {e}")
                return None
    
    def get_shows(self, location_id: int = None) -> List[Dict]:
        """Get shows from Cablecast"""
        try:
            params = {}
            if location_id:
                params['location'] = location_id
            
            response = self._make_request('GET', '/shows', params=params)
            if response:
                logger.info(f"Retrieved {len(response)} shows from Cablecast")
                return response
            return []
        except Exception as e:
            logger.error(f"Error getting shows from Cablecast: {e}")
            return []
    
    def get_show(self, show_id: int) -> Optional[Dict]:
        """Get a specific show by ID"""
        try:
            response = self._make_request('GET', f'/shows/{show_id}')
            if response:
                logger.debug(f"Retrieved show {show_id}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error getting show {show_id}: {e}")
            return None
    
    def create_show(self, show_data: Dict) -> Optional[Dict]:
        """Create a new show in Cablecast"""
        try:
            response = self._make_request('POST', '/shows', json=show_data)
            if response:
                logger.info(f"Created show: {response.get('id')}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error creating show in Cablecast: {e}")
            return None
    
    def update_show(self, show_id: int, show_data: Dict) -> bool:
        """Update an existing show in Cablecast"""
        try:
            response = self._make_request('PUT', f'/shows/{show_id}', json=show_data)
            if response is not None:
                logger.info(f"Updated show {show_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating show {show_id}: {e}")
            return False
    
    def get_vods(self, show_id: int = None) -> List[Dict]:
        """Get VODs from Cablecast"""
        try:
            params = {}
            if show_id:
                params['show'] = show_id
            
            response = self._make_request('GET', '/vods', params=params)
            if response:
                logger.info(f"Retrieved {len(response)} VODs from Cablecast")
                return response
            return []
        except Exception as e:
            logger.error(f"Error getting VODs from Cablecast: {e}")
            return []
    
    def get_vod(self, vod_id: int) -> Optional[Dict]:
        """Get a specific VOD by ID"""
        try:
            response = self._make_request('GET', f'/vods/{vod_id}')
            if response:
                logger.debug(f"Retrieved VOD {vod_id}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error getting VOD {vod_id}: {e}")
            return None
    
    def create_vod(self, vod_data: Dict) -> Optional[Dict]:
        """Create a new VOD in Cablecast"""
        try:
            response = self._make_request('POST', '/vods', json=vod_data)
            if response:
                logger.info(f"Created VOD: {response.get('id')}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error creating VOD in Cablecast: {e}")
            return None
    
    def get_vod_status(self, vod_id: int) -> Optional[Dict]:
        """Get VOD processing status"""
        try:
            response = self._make_request('GET', f'/vodStatus/{vod_id}')
            if response:
                logger.debug(f"Retrieved VOD status for {vod_id}: {response.get('vodState')}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error getting VOD status: {e}")
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
    
    def get_vod_qualities(self) -> List[Dict]:
        """Get available VOD quality settings"""
        try:
            response = self._make_request('GET', '/vodTranscodeQualities')
            if response:
                logger.info(f"Retrieved {len(response)} VOD quality settings")
                return response
            return []
        except Exception as e:
            logger.error(f"Error getting VOD qualities: {e}")
            return []
    
    def get_vod_chapters(self, vod_id: int) -> List[Dict]:
        """Get chapters for a VOD"""
        try:
            response = self._make_request('GET', f'/vods/{vod_id}/chapters')
            if response:
                logger.debug(f"Retrieved {len(response)} chapters for VOD {vod_id}")
                return response
            return []
        except Exception as e:
            logger.error(f"Error getting VOD chapters: {e}")
            return []
    
    def create_vod_chapter(self, vod_id: int, chapter_data: Dict) -> Optional[Dict]:
        """Create a new chapter for a VOD"""
        try:
            response = self._make_request('POST', f'/vods/{vod_id}/chapters', json=chapter_data)
            if response:
                logger.info(f"Created chapter for VOD {vod_id}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error creating VOD chapter: {e}")
            return None
    
    def get_locations(self) -> List[Dict]:
        """Get available locations"""
        try:
            response = self._make_request('GET', '/locations')
            if response:
                logger.info(f"Retrieved {len(response)} locations")
                return response
            return []
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test API connection and authentication"""
        try:
            response = self._make_request('GET', '/locations')
            if response is not None:
                logger.info("Cablecast API connection test successful")
                return True
            return False
        except Exception as e:
            logger.error(f"Cablecast API connection test failed: {e}")
            return False
    
    def wait_for_vod_processing(self, vod_id: int, timeout: int = 1800, check_interval: int = 30) -> bool:
        """Wait for VOD processing to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_vod_status(vod_id)
            if not status:
                logger.error(f"Failed to get status for VOD {vod_id}")
                return False
            
            vod_state = status.get('vodState', '')
            percent_complete = status.get('percentComplete', 0)
            
            logger.info(f"VOD {vod_id} state: {vod_state}, progress: {percent_complete}%")
            
            if vod_state == 'ready':
                logger.info(f"VOD {vod_id} processing completed successfully")
                return True
            elif vod_state == 'error':
                error_message = status.get('errorMessage', 'Unknown error')
                logger.error(f"VOD {vod_id} processing failed: {error_message}")
                return False
            
            time.sleep(check_interval)
        
        logger.error(f"VOD {vod_id} processing timed out after {timeout} seconds")
        return False