"""Transcription service for Archivist application.

This service provides a clean interface for all transcription-related operations,
including WhisperX integration, summarization, and captioning using SCC format.

Key Features:
- WhisperX transcription
- SCC (Scenarist Closed Caption) summarization
- Video captioning
- Error handling and validation
- Progress tracking

Example:
    >>> from core.services import TranscriptionService
    >>> service = TranscriptionService()
    >>> result = service.transcribe_file("video.mp4")
"""

import os
from typing import Dict, Optional, List
from loguru import logger
from core.exceptions import TranscriptionError, handle_transcription_error
# Removed circular import - will use direct WhisperX implementation
from core.scc_summarizer import summarize_scc
from core.config import WHISPER_MODEL, USE_GPU, LANGUAGE, OUTPUT_DIR

class TranscriptionService:
    """Service for handling transcription operations."""
    
    def __init__(self):
        self.model = WHISPER_MODEL
        self.use_gpu = USE_GPU
        self.language = LANGUAGE
    
    @handle_transcription_error
    def transcribe_file(self, file_path: str, output_dir: Optional[str] = None) -> Dict:
        """Transcribe a video/audio file using WhisperX, always producing SCC output.
        Args:
            file_path: Path to the video/audio file
            output_dir: Output directory for transcription files
        Returns:
            Dictionary containing transcription results (SCC only)
        """
        if not os.path.exists(file_path):
            raise TranscriptionError(f"File not found: {file_path}")
        logger.info(f"Starting transcription of {file_path}")
        try:
            from core.whisperx_helper import transcribe_with_whisperx

            result = transcribe_with_whisperx(file_path, output_dir or OUTPUT_DIR)
            return {
                'output_path': result.get('output_path', ''),
                'status': 'completed',
                'segments': result.get('segments', 0),
                'duration': result.get('duration', 0)
            }
        except Exception as e:
            logger.error(f"Transcription failed for {file_path}: {e}")
            raise TranscriptionError(f"Transcription failed: {str(e)}")
    
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