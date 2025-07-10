"""Cablecast API client for Archivist application.

This module provides a comprehensive interface for interacting with Cablecast's API,
including authentication, VOD management, and SCC caption file uploads.

Key Features:
- JWT-based authentication with automatic token refresh
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
import time
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
        self.user_id = CABLECAST_USER_ID
        self.password = CABLECAST_PASSWORD
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.auth_token = None
        self.token_expires_at = 0
        
        # Authentication
        self._authenticate()
    
    def _authenticate(self) -> bool:
        """Authenticate with Cablecast API and get JWT token."""
        try:
            auth_data = {
                'UserID': self.user_id,
                'Password': self.password
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=auth_data,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = time.time() + expires_in - 300  # 5 min buffer
                
                # Update session headers with token
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}'
                })
                
                logger.info("Successfully authenticated with Cablecast API")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid authentication token."""
        if not self.auth_token or time.time() >= self.token_expires_at:
            return self._authenticate()
        return True
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make HTTP request with authentication and retry logic."""
        if not self._ensure_authenticated():
            logger.error("Failed to authenticate")
            return None
        
        url = f"{self.base_url}/api/v1{endpoint}"
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.request(
                    method, url, 
                    timeout=REQUEST_TIMEOUT,
                    **kwargs
                )
                
                if response.status_code == 401:
                    # Token expired, re-authenticate
                    if self._authenticate():
                        continue
                    else:
                        logger.error("Re-authentication failed")
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