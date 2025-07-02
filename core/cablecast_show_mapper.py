"""Cablecast Show Mapper for linking transcriptions to existing shows.

This module handles the mapping between Archivist transcriptions and existing
Cablecast shows, providing intelligent matching based on various criteria.

Key Features:
- Intelligent show matching using multiple criteria
- Date-based matching
- Title similarity matching
- Duration-based matching
- Manual linking support

Example:
    >>> from core.cablecast_show_mapper import CablecastShowMapper
    >>> mapper = CablecastShowMapper()
    >>> show_id = mapper.find_matching_show('/path/to/video.mp4', metadata)
"""

import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher
from loguru import logger
from core.cablecast_client import CablecastAPIClient

class CablecastShowMapper:
    """Maps Archivist transcriptions to existing Cablecast shows"""
    
    def __init__(self):
        self.cablecast_client = CablecastAPIClient()
        self.cache = {}  # Simple cache for show data
    
    def find_matching_show(self, video_path: str, transcription_metadata: Dict) -> Optional[int]:
        """
        Find existing Cablecast show that matches the video content
        
        Args:
            video_path: Path to the video file
            transcription_metadata: Metadata from transcription process
            
        Returns:
            Cablecast show ID if match found, None otherwise
        """
        try:
            # Extract video metadata
            video_name = os.path.basename(video_path)
            video_date = self._extract_date_from_filename(video_name)
            video_title = self._extract_title_from_filename(video_name)
            
            logger.info(f"Looking for matching show for: {video_name}")
            logger.debug(f"Extracted date: {video_date}, title: {video_title}")
            
            # Get all shows from Cablecast
            shows = self._get_cablecast_shows()
            if not shows:
                logger.warning("No shows found in Cablecast")
                return None
            
            # Find best match
            best_match = None
            best_score = 0
            
            for show in shows:
                score = self._calculate_match_score(
                    show, video_name, video_date, video_title, transcription_metadata
                )
                
                if score > best_score and score >= 0.7:  # Minimum threshold
                    best_score = score
                    best_match = show
                    logger.debug(f"New best match: {show.get('title', 'Unknown')} (score: {score:.2f})")
            
            if best_match:
                logger.info(f"Found matching show: {best_match.get('title', 'Unknown')} (ID: {best_match['id']}, score: {best_score:.2f})")
                return best_match['id']
            else:
                logger.info("No matching show found")
                return None
                
        except Exception as e:
            logger.error(f"Error finding matching show: {e}")
            return None
    
    def _get_cablecast_shows(self) -> List[Dict]:
        """Get shows from Cablecast with caching"""
        try:
            # Check cache first
            cache_key = 'shows'
            if cache_key in self.cache:
                cache_time, shows = self.cache[cache_key]
                # Cache for 5 minutes
                if datetime.now() - cache_time < timedelta(minutes=5):
                    return shows
            
            # Fetch from API
            shows = self.cablecast_client.get_shows()
            
            # Update cache
            self.cache[cache_key] = (datetime.now(), shows)
            
            return shows
        except Exception as e:
            logger.error(f"Error getting Cablecast shows: {e}")
            return []
    
    def _extract_date_from_filename(self, filename: str) -> Optional[str]:
        """Extract date from filename using various patterns"""
        # Common date patterns in filenames
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{2}-\d{2}-\d{4})',  # MM-DD-YYYY
            r'(\d{8})',              # YYYYMMDD
            r'(\d{4}_\d{2}_\d{2})',  # YYYY_MM_DD
            r'(\d{2}_\d{2}_\d{4})',  # MM_DD_YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, filename)
            if match:
                date_str = match.group(1)
                try:
                    # Try to parse and standardize the date
                    if len(date_str) == 8 and '_' not in date_str:
                        # YYYYMMDD format
                        date_obj = datetime.strptime(date_str, '%Y%m%d')
                    elif '-' in date_str:
                        if len(date_str.split('-')[0]) == 4:
                            # YYYY-MM-DD format
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        else:
                            # MM-DD-YYYY format
                            date_obj = datetime.strptime(date_str, '%m-%d-%Y')
                    elif '_' in date_str:
                        if len(date_str.split('_')[0]) == 4:
                            # YYYY_MM_DD format
                            date_obj = datetime.strptime(date_str, '%Y_%m_%d')
                        else:
                            # MM_DD_YYYY format
                            date_obj = datetime.strptime(date_str, '%m_%d_%Y')
                    else:
                        continue
                    
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        return None
    
    def _extract_title_from_filename(self, filename: str) -> str:
        """Extract title from filename by removing date and extension"""
        # Remove file extension
        name_without_ext = os.path.splitext(filename)[0]
        
        # Remove date patterns
        name_without_date = re.sub(r'\d{4}[-_]\d{2}[-_]\d{2}', '', name_without_ext)
        name_without_date = re.sub(r'\d{2}[-_]\d{2}[-_]\d{4}', '', name_without_date)
        name_without_date = re.sub(r'\d{8}', '', name_without_date)
        
        # Clean up extra characters
        name_without_date = re.sub(r'[-_]+', ' ', name_without_date)
        name_without_date = name_without_date.strip()
        
        return name_without_date
    
    def _calculate_match_score(self, show: Dict, video_name: str, video_date: str, 
                             video_title: str, transcription_metadata: Dict) -> float:
        """Calculate match score between show and video"""
        score = 0.0
        
        # Date matching (40% weight)
        if video_date and show.get('date'):
            show_date = show['date']
            if isinstance(show_date, str):
                try:
                    show_date_obj = datetime.strptime(show_date, '%Y-%m-%d')
                    video_date_obj = datetime.strptime(video_date, '%Y-%m-%d')
                    date_diff = abs((show_date_obj - video_date_obj).days)
                    
                    if date_diff == 0:
                        score += 0.4  # Exact date match
                    elif date_diff <= 1:
                        score += 0.3  # Within 1 day
                    elif date_diff <= 7:
                        score += 0.1  # Within 1 week
                except ValueError:
                    pass
        
        # Title similarity (35% weight)
        show_title = show.get('title', '').lower()
        video_title_lower = video_title.lower()
        
        if show_title and video_title_lower:
            similarity = SequenceMatcher(None, show_title, video_title_lower).ratio()
            score += similarity * 0.35
        
        # Duration matching (15% weight)
        if show.get('length') and transcription_metadata.get('duration'):
            show_duration = show['length']
            video_duration = transcription_metadata['duration']
            duration_diff = abs(show_duration - video_duration)
            
            if duration_diff < 30:  # Within 30 seconds
                score += 0.15
            elif duration_diff < 120:  # Within 2 minutes
                score += 0.1
            elif duration_diff < 300:  # Within 5 minutes
                score += 0.05
        
        # Description matching (10% weight)
        show_description = show.get('description', '').lower()
        if show_description and video_title_lower:
            # Check if video title appears in show description
            if video_title_lower in show_description:
                score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def get_show_suggestions(self, video_path: str, limit: int = 5) -> List[Dict]:
        """
        Get suggested Cablecast shows for manual linking
        
        Args:
            video_path: Path to the video file
            limit: Maximum number of suggestions to return
            
        Returns:
            List of suggested shows with similarity scores
        """
        try:
            video_name = os.path.basename(video_path)
            video_date = self._extract_date_from_filename(video_name)
            video_title = self._extract_title_from_filename(video_name)
            
            shows = self._get_cablecast_shows()
            suggestions = []
            
            for show in shows:
                score = self._calculate_match_score(
                    show, video_name, video_date, video_title, {}
                )
                
                if score > 0.1:  # Minimum threshold for suggestions
                    suggestions.append({
                        'show_id': show['id'],
                        'title': show.get('title', 'Unknown'),
                        'date': show.get('date', ''),
                        'description': show.get('description', ''),
                        'length': show.get('length'),
                        'similarity_score': round(score, 3),
                        'match_reasons': self._get_match_reasons(show, video_name, video_date, video_title)
                    })
            
            # Sort by similarity score and return top results
            suggestions.sort(key=lambda x: x['similarity_score'], reverse=True)
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting show suggestions: {e}")
            return []
    
    def _get_match_reasons(self, show: Dict, video_name: str, video_date: str, video_title: str) -> List[str]:
        """Get reasons why a show matches the video"""
        reasons = []
        
        # Date match
        if video_date and show.get('date'):
            try:
                show_date_obj = datetime.strptime(show['date'], '%Y-%m-%d')
                video_date_obj = datetime.strptime(video_date, '%Y-%m-%d')
                date_diff = abs((show_date_obj - video_date_obj).days)
                
                if date_diff == 0:
                    reasons.append("Exact date match")
                elif date_diff <= 1:
                    reasons.append("Date within 1 day")
                elif date_diff <= 7:
                    reasons.append("Date within 1 week")
            except ValueError:
                pass
        
        # Title similarity
        show_title = show.get('title', '').lower()
        video_title_lower = video_title.lower()
        
        if show_title and video_title_lower:
            similarity = SequenceMatcher(None, show_title, video_title_lower).ratio()
            if similarity > 0.8:
                reasons.append("High title similarity")
            elif similarity > 0.5:
                reasons.append("Moderate title similarity")
        
        # Duration match
        if show.get('length'):
            reasons.append(f"Duration: {show['length']} seconds")
        
        return reasons
    
    def validate_show_id(self, show_id: int) -> bool:
        """Validate that a show ID exists in Cablecast"""
        try:
            show = self.cablecast_client.get_show(show_id)
            return show is not None
        except Exception as e:
            logger.error(f"Error validating show ID {show_id}: {e}")
            return False 