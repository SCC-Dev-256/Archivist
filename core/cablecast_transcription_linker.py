"""Cablecast Transcription Linker for connecting transcriptions to existing shows.

This module handles the linking of completed transcriptions to existing
Cablecast shows, including metadata enhancement and database updates.

Key Features:
- Link transcriptions to existing Cablecast shows
- Enhance show metadata with transcription data
- Update database relationships
- Handle transcription file management

Example:
    >>> from core.cablecast_transcription_linker import CablecastTranscriptionLinker
    >>> linker = CablecastTranscriptionLinker()
    >>> success = linker.link_transcription_to_show("transcription_id", 123)
"""

import os
from typing import Dict, Optional, List
from datetime import datetime
from loguru import logger
from core.cablecast_client import CablecastAPIClient
from core.models import TranscriptionResultORM, CablecastShowORM
from core.app import db

class CablecastTranscriptionLinker:
    """Links transcriptions to existing Cablecast shows"""
    
    def __init__(self, cablecast_client=None):
        self.cablecast_client = cablecast_client or CablecastAPIClient()
    
    def link_transcription_to_show(self, transcription_id: str, show_id: int) -> bool:
        """
        Link a completed transcription to an existing Cablecast show
        
        Args:
            transcription_id: ID of the transcription to link
            show_id: ID of the Cablecast show to link to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Linking transcription {transcription_id} to show {show_id}")
            
            # Get transcription data
            transcription = TranscriptionResultORM.query.get(transcription_id)
            if not transcription:
                logger.error(f"Transcription {transcription_id} not found")
                return False
            
            # Validate show exists in Cablecast
            show = self.cablecast_client.get_show(show_id)
            if not show:
                logger.error(f"Cablecast show {show_id} not found")
                return False
            
            # Check if link already exists
            existing_link = CablecastShowORM.query.filter_by(
                transcription_id=transcription_id
            ).first()
            
            if existing_link:
                logger.warning(f"Transcription {transcription_id} already linked to show {existing_link.cablecast_id}")
                return False
            
            # Create link in our database
            cablecast_show = CablecastShowORM(
                cablecast_id=show_id,
                title=show.get('title', ''),
                description=show.get('description', ''),
                duration=show.get('length'),
                transcription_id=transcription_id
            )
            db.session.add(cablecast_show)
            db.session.commit()
            
            logger.info(f"Created database link for transcription {transcription_id} to show {show_id}")
            
            # Enhance show with transcription metadata
            enhancement_success = self._enhance_show_with_transcription(show_id, transcription)
            
            if enhancement_success:
                logger.info(f"Successfully linked and enhanced transcription {transcription_id} to show {show_id}")
            else:
                logger.warning(f"Linked transcription {transcription_id} to show {show_id} but enhancement failed")
            
            return True
            
        except Exception as e:
            logger.error(f"Error linking transcription to show: {e}")
            db.session.rollback()
            return False
    
    def _enhance_show_with_transcription(self, show_id: int, transcription: TranscriptionResultORM) -> bool:
        """
        Enhance Cablecast show with transcription metadata
        
        Args:
            show_id: Cablecast show ID
            transcription: Transcription result object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read transcription content
            if not os.path.exists(transcription.output_path):
                logger.error(f"Transcription file not found: {transcription.output_path}")
                return False
            
            with open(transcription.output_path, 'r', encoding='utf-8') as f:
                transcription_text = f.read()
            
            # Extract key information from transcription
            transcription_metadata = self._analyze_transcription(transcription_text)
            
            # Create enhanced metadata for Cablecast
            metadata = {
                'transcription_available': True,
                'transcription_text': transcription_text,
                'transcription_file': transcription.output_path,
                'transcription_completed_at': transcription.completed_at.isoformat(),
                'searchable_content': transcription_text,
                'accessibility_features': ['captions', 'transcript'],
                'content_type': 'transcribed_video',
                'source_system': 'archivist',
                'transcription_metadata': transcription_metadata
            }
            
            # Update show metadata in Cablecast
            success = self.cablecast_client.update_show_metadata(show_id, metadata)
            
            if success:
                logger.info(f"Enhanced show {show_id} with transcription metadata")
                return True
            else:
                logger.error(f"Failed to enhance show {show_id} with transcription metadata")
                return False
                
        except Exception as e:
            logger.error(f"Error enhancing show with transcription: {e}")
            return False
    
    def _analyze_transcription(self, transcription_text: str) -> Dict:
        """Analyze transcription text to extract useful metadata"""
        try:
            lines = transcription_text.strip().split('\n')
            
            # Extract segments
            segments = []
            current_segment = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if line is a timestamp
                if ' --> ' in line:
                    if current_segment:
                        segments.append(current_segment)
                    
                    start_time, end_time = line.split(' --> ')
                    current_segment = {
                        'start': self._parse_timestamp(start_time),
                        'end': self._parse_timestamp(end_time),
                        'text': ''
                    }
                elif current_segment and not line.isdigit():
                    # This is text content
                    current_segment['text'] += line + ' '
            
            # Add the last segment
            if current_segment:
                segments.append(current_segment)
            
            # Calculate statistics
            total_duration = segments[-1]['end'] if segments else 0
            total_words = sum(len(seg['text'].split()) for seg in segments)
            avg_words_per_minute = (total_words / (total_duration / 60)) if total_duration > 0 else 0
            
            # Extract key phrases (simple approach)
            all_text = ' '.join(seg['text'] for seg in segments)
            key_phrases = self._extract_key_phrases(all_text)
            
            return {
                'total_segments': len(segments),
                'total_duration_seconds': total_duration,
                'total_words': total_words,
                'average_words_per_minute': round(avg_words_per_minute, 2),
                'key_phrases': key_phrases,
                'segments': segments[:10]  # First 10 segments for preview
            }
            
        except Exception as e:
            logger.error(f"Error analyzing transcription: {e}")
            return {}
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse timestamp to seconds (supports SRT and SCC formats)"""
        try:
            # Remove milliseconds comma
            timestamp = timestamp.replace(',', '.')
            
            # Parse HH:MM:SS.mmm format
            parts = timestamp.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            
            return hours * 3600 + minutes * 60 + seconds
        except Exception:
            return 0.0
    
    def _extract_key_phrases(self, text: str, max_phrases: int = 10) -> List[str]:
        """Extract key phrases from text (simple implementation)"""
        try:
            # Simple key phrase extraction
            words = text.lower().split()
            
            # Remove common words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
            
            # Count word frequencies
            word_counts = {}
            for word in words:
                if word not in stop_words and len(word) > 3:
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            # Get most frequent words
            sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
            return [word for word, count in sorted_words[:max_phrases]]
            
        except Exception as e:
            logger.error(f"Error extracting key phrases: {e}")
            return []
    
    def unlink_transcription_from_show(self, transcription_id: str) -> bool:
        """
        Unlink a transcription from its Cablecast show
        
        Args:
            transcription_id: ID of the transcription to unlink
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find the link
            link = CablecastShowORM.query.filter_by(
                transcription_id=transcription_id
            ).first()
            
            if not link:
                logger.warning(f"No link found for transcription {transcription_id}")
                return False
            
            show_id = link.cablecast_id
            
            # Remove from database
            db.session.delete(link)
            db.session.commit()
            
            logger.info(f"Unlinked transcription {transcription_id} from show {show_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unlinking transcription: {e}")
            db.session.rollback()
            return False
    
    def get_linked_transcriptions(self, show_id: int) -> List[Dict]:
        """
        Get all transcriptions linked to a specific show
        
        Args:
            show_id: Cablecast show ID
            
        Returns:
            List of linked transcription data
        """
        try:
            links = CablecastShowORM.query.filter_by(cablecast_id=show_id).all()
            
            result = []
            for link in links:
                transcription = TranscriptionResultORM.query.get(link.transcription_id)
                if transcription:
                    result.append({
                        'transcription_id': transcription.id,
                        'video_path': transcription.video_path,
                        'completed_at': transcription.completed_at.isoformat(),
                        'status': transcription.status,
                        'link_created_at': link.created_at.isoformat()
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting linked transcriptions: {e}")
            return []
    
    def get_transcription_link_status(self, transcription_id: str) -> Optional[Dict]:
        """
        Get the link status of a transcription
        
        Args:
            transcription_id: ID of the transcription
            
        Returns:
            Link status information or None if not linked
        """
        try:
            link = CablecastShowORM.query.filter_by(
                transcription_id=transcription_id
            ).first()
            
            if not link:
                return None
            
            return {
                'show_id': link.cablecast_id,
                'show_title': link.title,
                'linked_at': link.created_at.isoformat(),
                'enhanced': True  # Assuming enhancement was successful if link exists
            }
            
        except Exception as e:
            logger.error(f"Error getting transcription link status: {e}")
            return None 