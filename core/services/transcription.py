"""Transcription service for Archivist application.

This service provides a clean interface for all transcription-related operations,
including WhisperX integration, summarization, and captioning using SCC format.

Key Features:
- WhisperX transcription
- SCC (Scenarist Closed Caption) summarization
- Video captioning
- Error handling and validation
- Progress tracking
- Surface-level flex server file discovery

Example:
    >>> from core.services import TranscriptionService
    >>> service = TranscriptionService()
    >>> result = service.transcribe_file("video.mp4")
"""

import os
import glob
from typing import Dict, Optional, List
from loguru import logger
from core.exceptions import TranscriptionError, handle_transcription_error
from core.transcription import _transcribe_with_faster_whisper
from core.scc_summarizer import summarize_scc
from core.config import WHISPER_MODEL, USE_GPU, LANGUAGE, OUTPUT_DIR, MEMBER_CITIES

class TranscriptionService:
    """Service for handling transcription operations with surface-level flex server support."""
    
    def __init__(self):
        self.model = WHISPER_MODEL
        self.use_gpu = USE_GPU
        self.language = LANGUAGE
    
    def discover_video_files(self, flex_server_id: Optional[str] = None, 
                           file_pattern: str = "*.mp4") -> List[Dict]:
        """Discover video files on flex servers (surface-level E: drive structure).
        
        Args:
            flex_server_id: Specific flex server to scan (flex1, flex2, etc.) or None for all
            file_pattern: File pattern to search for (default: *.mp4)
            
        Returns:
            List of dictionaries containing file information
        """
        discovered_files = []
        
        # Determine which flex servers to scan
        if flex_server_id:
            servers_to_scan = {flex_server_id: MEMBER_CITIES[flex_server_id]}
        else:
            servers_to_scan = MEMBER_CITIES
        
        for server_id, server_config in servers_to_scan.items():
            mount_path = server_config['mount_path']
            city_name = server_config['name']
            
            logger.info(f"Scanning {city_name} ({server_id}) at {mount_path}")
            
            if not os.path.ismount(mount_path):
                logger.warning(f"Flex server {server_id} not mounted at {mount_path}")
                continue
            
            if not os.access(mount_path, os.R_OK):
                logger.warning(f"Flex server {server_id} not readable at {mount_path}")
                continue
            
            try:
                # Surface-level file discovery (E: drive structure)
                # Search directly in the mount root, not in subdirectories
                pattern = os.path.join(mount_path, file_pattern)
                video_files = glob.glob(pattern)
                
                for video_file in video_files:
                    if os.path.isfile(video_file) and os.path.getsize(video_file) > 1024*1024:  # > 1MB
                        file_info = {
                            'file_path': video_file,
                            'file_name': os.path.basename(video_file),
                            'file_size': os.path.getsize(video_file),
                            'modified_time': os.path.getmtime(video_file),
                            'flex_server': server_id,
                            'city_name': city_name,
                            'mount_path': mount_path,
                            'relative_path': os.path.relpath(video_file, mount_path)
                        }
                        discovered_files.append(file_info)
                        logger.debug(f"Found video: {file_info['file_name']} ({file_info['file_size']} bytes)")
                
                logger.info(f"Found {len(video_files)} video files on {city_name}")
                
            except Exception as e:
                logger.error(f"Error scanning {city_name} ({server_id}): {e}")
        
        # Sort by modification time (newest first)
        discovered_files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        logger.info(f"Total video files discovered: {len(discovered_files)}")
        return discovered_files
    
    def find_untranscribed_videos(self, flex_server_id: Optional[str] = None) -> List[Dict]:
        """Find video files that don't have corresponding SCC transcription files.
        
        Args:
            flex_server_id: Specific flex server to scan or None for all
            
        Returns:
            List of video files needing transcription
        """
        all_videos = self.discover_video_files(flex_server_id)
        untranscribed = []
        
        for video_info in all_videos:
            video_path = video_info['file_path']
            base_name = os.path.splitext(video_info['file_name'])[0]
            mount_path = video_info['mount_path']
            
            # Check for existing SCC file (surface-level)
            scc_path = os.path.join(mount_path, f"{base_name}.scc")
            
            if not os.path.exists(scc_path):
                video_info['scc_path'] = scc_path
                video_info['needs_transcription'] = True
                untranscribed.append(video_info)
                logger.debug(f"Needs transcription: {video_info['file_name']}")
            else:
                logger.debug(f"Already transcribed: {video_info['file_name']}")
        
        logger.info(f"Found {len(untranscribed)} videos needing transcription")
        return untranscribed

    def pick_newest_uncaptioned(self, max_per_city: int = 1, scan_limit: int = 50) -> Dict[str, List[str]]:
        """Pick newest uncaptioned videos per city (surface-level), newest-first.

        Args:
            max_per_city: max items to pick per city
            scan_limit: max files to scan per city before picking

        Returns:
            Dict mapping city_id -> list of absolute video paths
        """
        picks: Dict[str, List[str]] = {}
        # Iterate configured member cities; stay surface-level by design
        for city_id, cfg in MEMBER_CITIES.items():
            mount_path = cfg.get('mount_path')
            if not mount_path or not os.path.isdir(mount_path):
                continue
            # Discover surface-level videos newest-first
            videos = []
            try:
                with os.scandir(mount_path) as it:
                    for e in it:
                        if not e.is_file():
                            continue
                        name = e.name.lower()
                        if not (name.endswith('.mp4') or name.endswith('.mkv') or name.endswith('.mov') or name.endswith('.ts')):
                            continue
                        try:
                            st = e.stat()
                            videos.append((st.st_mtime, e.path))
                        except OSError:
                            continue
            except PermissionError:
                continue
            videos.sort(reverse=True)
            if scan_limit:
                videos = videos[:scan_limit]
            # Filter to uncaptioned
            picked: List[str] = []
            for _mtime, path in videos:
                base, _ = os.path.splitext(path)
                if os.path.exists(base + '.scc'):
                    continue
                picked.append(path)
                if len(picked) >= max_per_city:
                    break
            if picked:
                picks[city_id] = picked
        return picks
    
    @handle_transcription_error
    def transcribe_file(self, file_path: str, output_dir: Optional[str] = None) -> Dict:
        """Transcribe a video/audio file using WhisperX, always producing SCC output.
        
        Args:
            file_path: Path to the video/audio file
            output_dir: Output directory for transcription files (defaults to same directory as video)
            
        Returns:
            Dictionary containing transcription results (SCC only)
        """
        if not os.path.exists(file_path):
            raise TranscriptionError(f"File not found: {file_path}")
        
        logger.info(f"Starting transcription of {file_path}")
        
        try:
            # Use the same directory as the video file for output (surface-level structure)
            if output_dir is None:
                output_dir = os.path.dirname(file_path)
            
            # Perform transcription
            result = _transcribe_with_faster_whisper(video_path=file_path)
            
            return {
                'output_path': result.get('output_path', ''),
                'status': 'completed',
                'segments': result.get('segments', 0),
                'duration': result.get('duration', 0),
                'model_used': result.get('model_used', self.model),
                'language': result.get('language', self.language)
            }
            
        except Exception as e:
            logger.error(f"Transcription failed for {file_path}: {e}")
            raise TranscriptionError(f"Transcription failed: {str(e)}")
    
    @handle_transcription_error
    def transcribe_flex_server_videos(self, flex_server_id: str, limit: Optional[int] = None) -> Dict:
        """Transcribe all untranscribed videos on a specific flex server.
        
        Args:
            flex_server_id: Flex server ID (flex1, flex2, etc.)
            limit: Maximum number of videos to transcribe (None for all)
            
        Returns:
            Dictionary containing batch transcription results
        """
        logger.info(f"Starting batch transcription for flex server {flex_server_id}")
        
        # Find untranscribed videos
        untranscribed = self.find_untranscribed_videos(flex_server_id)
        
        if limit:
            untranscribed = untranscribed[:limit]
        
        results = {
            'flex_server': flex_server_id,
            'total_videos': len(untranscribed),
            'completed': 0,
            'failed': 0,
            'results': [],
            'errors': []
        }
        
        for video_info in untranscribed:
            try:
                logger.info(f"Transcribing {video_info['file_name']}")
                
                result = self.transcribe_file(video_info['file_path'])
                
                results['results'].append({
                    'file_name': video_info['file_name'],
                    'file_path': video_info['file_path'],
                    'transcription_result': result,
                    'status': 'completed'
                })
                results['completed'] += 1
                
                logger.info(f"Completed transcription of {video_info['file_name']}")
                
            except Exception as e:
                error_msg = f"Failed to transcribe {video_info['file_name']}: {str(e)}"
                logger.error(error_msg)
                
                results['errors'].append({
                    'file_name': video_info['file_name'],
                    'file_path': video_info['file_path'],
                    'error': error_msg
                })
                results['failed'] += 1
        
        logger.info(f"Batch transcription completed: {results['completed']} successful, {results['failed']} failed")
        return results
    
    @handle_transcription_error
    def summarize_transcription(self, scc_path: str) -> Dict:
        """Summarize an SCC transcription file.
        
        Args:
            scc_path: Path to the SCC file
            
        Returns:
            Dictionary containing summary results
        """
        if not os.path.exists(scc_path):
            raise TranscriptionError(f"SCC file not found: {scc_path}")
        
        logger.info(f"Starting summarization of {scc_path}")
        
        try:
            summary_path = summarize_scc(scc_path)
            if summary_path:
                logger.info(f"Summarization completed for {scc_path}")
                return {'summary_path': summary_path, 'status': 'completed'}
            else:
                raise TranscriptionError("Summarization failed to produce output file")
            
        except Exception as e:
            logger.error(f"Summarization failed for {scc_path}: {e}")
            raise TranscriptionError(f"Summarization failed: {str(e)}")
    
    @handle_transcription_error
    def create_captions(self, video_path: str, scc_path: str, output_path: Optional[str] = None) -> str:
        """Create captioned video from SCC file.
        
        Args:
            video_path: Path to the video file
            scc_path: Path to the SCC file
            output_path: Output path for captioned video
            
        Returns:
            Path to the captioned video file
        """
        if not os.path.exists(video_path):
            raise TranscriptionError(f"Video file not found: {video_path}")
        
        if not os.path.exists(scc_path):
            raise TranscriptionError(f"SCC file not found: {scc_path}")
        
        logger.info(f"Creating captions for {video_path}")
        
        try:
            # For now, return the original video path since captioning is not implemented
            # TODO: Implement actual captioning functionality
            captioned_path = output_path or video_path.replace('.mp4', '_captioned.mp4')
            logger.info(f"Caption creation placeholder: {captioned_path}")
            return captioned_path
            
        except Exception as e:
            logger.error(f"Caption creation failed for {video_path}: {e}")
            raise TranscriptionError(f"Caption creation failed: {str(e)}")
    
    @handle_transcription_error
    def process_video_pipeline(self, video_path: str, output_dir: Optional[str] = None) -> Dict:
        """Complete video processing pipeline: transcribe, summarize, and caption.
        
        Args:
            video_path: Path to the video file
            output_dir: Output directory for all files
            
        Returns:
            Dictionary containing all processing results
        """
        logger.info(f"Starting complete pipeline for {video_path}")
        
        try:
            # Step 1: Transcribe
            transcription_result = self.transcribe_file(video_path, output_dir)
            scc_path = transcription_result.get('output_path')
            
            if not scc_path or not os.path.exists(scc_path):
                raise TranscriptionError("Transcription failed to produce SCC file")
            
            # Step 2: Summarize
            summary_result = self.summarize_transcription(scc_path)
            
            # Step 3: Create captions
            captioned_path = self.create_captions(video_path, scc_path, output_dir)
            
            # Combine results
            pipeline_result = {
                'video_path': video_path,
                'transcription': transcription_result,
                'summary': summary_result,
                'captioned_video': captioned_path,
                'status': 'completed'
            }
            
            logger.info(f"Pipeline completed for {video_path}")
            return pipeline_result
            
        except Exception as e:
            logger.error(f"Pipeline failed for {video_path}: {e}")
            raise TranscriptionError(f"Processing pipeline failed: {str(e)}")
    
    def get_transcription_status(self, file_path: str) -> Dict:
        """Get the status of a transcription job.
        
        Args:
            file_path: Path to the input file
            
        Returns:
            Dictionary containing status information
        """
        # This would typically check against a job queue or database
        # For now, we'll check if output files exist
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_dir = os.path.dirname(file_path)
        
        scc_path = os.path.join(output_dir, f"{base_name}.scc")
        summary_path = os.path.join(output_dir, f"{base_name}_summary.txt")
        
        status = {
            'file_path': file_path,
            'transcription_exists': os.path.exists(scc_path),
            'summary_exists': os.path.exists(summary_path),
            'scc_path': scc_path if os.path.exists(scc_path) else None,
            'summary_path': summary_path if os.path.exists(summary_path) else None
        }
        
        return status 