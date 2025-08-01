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
import time
from typing import Dict, List, Optional

from loguru import logger

from core.config import (
    BATCH_SIZE,
    COMPUTE_TYPE,
    LANGUAGE,
    OUTPUT_DIR,
    USE_GPU,
    WHISPER_MODEL
)
from core import TranscriptionError, handle_transcription_error
from core.scc_summarizer import summarize_scc


def _seconds_to_scc_timestamp(seconds: float) -> str:
    """Convert seconds to SCC timestamp format (HH:MM:SS:FF).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        SCC timestamp string in format HH:MM:SS:FF
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    frames = int((seconds % 1) * 30)  # 30 fps for SCC
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


class TranscriptionService:
    """Service for handling transcription operations."""
    
    def __init__(self):
        self.model = WHISPER_MODEL
        self.use_gpu = USE_GPU
        self.language = LANGUAGE
    
    def _transcribe_with_faster_whisper(self, video_path: str) -> Dict:
        """
        Transcribe video using Faster Whisper with optimized settings for caption generation.
        
        This method uses the Faster Whisper library with settings optimized for
        generating high-quality captions suitable for broadcast use.
        
        Args:
            video_path: Path to the video file to transcribe
            
        Returns:
            Dictionary containing transcription results with SCC output path
        """
        try:
            from faster_whisper import WhisperModel
            
            # Initialize the model with optimized settings for caption generation
            logger.info(f"Loading Whisper model: {self.model}")
            model = WhisperModel(
                self.model,
                device="cuda" if self.use_gpu else "cpu",
                compute_type=COMPUTE_TYPE,
                cpu_threads=BATCH_SIZE
            )
            
            logger.info(f"Whisper model loaded successfully. Starting transcription...")
            
            # Transcribe the audio with optimized settings for captions
            logger.info(f"Starting transcription of {video_path}")
            segments, info = model.transcribe(
                video_path,
                language=self.language,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,  # Filter out non-speech segments
                vad_parameters=dict(min_silence_duration_ms=500)  # Reduce silence gaps
            )
            
            # Convert segments to list for processing
            logger.info("Converting transcription segments...")
            segments_list = list(segments)
            
            if not segments_list:
                logger.warning(f"No speech segments found in {video_path}")
                # Create empty SCC file
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                output_dir = os.path.dirname(video_path)
                scc_path = os.path.join(output_dir, f"{base_name}.scc")
                
                with open(scc_path, 'w', encoding='utf-8') as f:
                    f.write("Scenarist_SCC V1.0\n\n")
                    f.write("00:00:00:00\t00:00:05:00\n")
                    f.write("[No speech detected]\n\n")
                
                return {
                    'output_path': scc_path,
                    'srt_path': scc_path,  # For backward compatibility
                    'segments': 0,
                    'duration': info.duration if hasattr(info, 'duration') else 0,
                    'language': info.language if hasattr(info, 'language') else self.language,
                    'status': 'completed',
                    'warning': 'No speech detected'
                }
            
            # Generate output paths
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_dir = os.path.dirname(video_path)
            
            # Generate SCC file
            scc_path = os.path.join(output_dir, f"{base_name}.scc")
            
            # Write SCC file with proper formatting for broadcast captions
            logger.info(f"Writing SCC file to: {scc_path}")
            with open(scc_path, 'w', encoding='utf-8') as f:
                f.write("Scenarist_SCC V1.0\n\n")
                
                for i, segment in enumerate(segments_list, 1):
                    # Convert timestamps to SCC format (HH:MM:SS:FF)
                    start_time = segment.start
                    end_time = segment.end
                    
                    # Convert to SCC timestamp format
                    start_scc = _seconds_to_scc_timestamp(start_time)
                    end_scc = _seconds_to_scc_timestamp(end_time)
                    
                    # Clean and format text for captions
                    caption_text = segment.text.strip()
                    # Remove extra whitespace and normalize
                    caption_text = ' '.join(caption_text.split())
                    
                    # Write caption entry
                    f.write(f"{start_scc}\t{end_scc}\n")
                    f.write(f"{caption_text}\n\n")
            
            logger.info(f"Transcription completed. SCC saved to: {scc_path}")
            logger.info(f"Generated {len(segments_list)} caption segments")
            
            return {
                'output_path': scc_path,
                'srt_path': scc_path,  # For backward compatibility
                'segments': len(segments_list),
                'duration': info.duration if hasattr(info, 'duration') else 0,
                'language': info.language if hasattr(info, 'language') else self.language,
                'status': 'completed',
                'model_used': self.model
            }
            
        except Exception as e:
            logger.error(f"Direct transcription failed: {e}")
            raise
    
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
            # Use the direct transcription function
            result = self._transcribe_with_faster_whisper(file_path)
            # The function now generates SCC captions and returns the output path.
            return {
                'output_path': result.get('output_path', ''),
                'status': 'completed',
                'segments': result.get('segments', 0),
                'duration': result.get('duration', 0),
                'language': result.get('language', self.language),
                'model_used': result.get('model_used', self.model)
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
        """Create SCC sidecar file for video.
        
        This method validates that the SCC file exists and is properly formatted
        as a sidecar file for the original video. No video processing is performed.
        
        Args:
            video_path: Path to the video file
            scc_path: Path to the SCC file
            output_path: Not used (kept for API compatibility)
        
        Returns:
            Path to the SCC sidecar file
        """
        if not os.path.exists(video_path):
            raise TranscriptionError(f"Video file not found: {video_path}")
        if not os.path.exists(scc_path):
            raise TranscriptionError(f"SCC file not found: {scc_path}")
        logger.info(f"Validating SCC sidecar file for {video_path}")
        try:
            # Validate SCC file format
            self._validate_scc_file(scc_path)
            # Ensure SCC file is in the same directory as video
            video_dir = os.path.dirname(video_path)
            scc_dir = os.path.dirname(scc_path)
            if video_dir != scc_dir:
                logger.warning(f"SCC file not in same directory as video: {scc_path}")
                logger.info(f"Video directory: {video_dir}, SCC directory: {scc_dir}")
            logger.info(f"SCC sidecar file validated: {scc_path}")
            return scc_path
        except Exception as e:
            logger.error(f"SCC validation failed for {video_path}: {e}")
            raise TranscriptionError(f"SCC validation failed: {str(e)}")
    
    def _validate_scc_file(self, scc_path: str) -> None:
        """Validate that an SCC file is properly formatted.
        
        Args:
            scc_path: Path to the SCC file to validate
            
        Raises:
            TranscriptionError: If the SCC file is invalid
        """
        try:
            with open(scc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Check for Scenarist_SCC header
            if not any(line.strip().startswith('Scenarist_SCC') for line in lines):
                raise TranscriptionError("SCC file missing Scenarist_SCC header")
            
            # Check for at least one timestamp entry
            timestamp_lines = [line for line in lines if line.strip().startswith('00:')]
            if not timestamp_lines:
                raise TranscriptionError("SCC file contains no timestamp entries")
            
            # Validate timestamp format (HH:MM:SS:FF)
            for line in timestamp_lines:
                time_part = line.split()[0] if line.split() else ""
                if not self._is_valid_scc_timestamp(time_part):
                    raise TranscriptionError(f"Invalid SCC timestamp format: {time_part}")
            
            logger.info(f"SCC file validation passed: {len(timestamp_lines)} timestamp entries found")
            
        except UnicodeDecodeError:
            raise TranscriptionError("SCC file encoding error - must be UTF-8")
        except Exception as e:
            if "TranscriptionError" in str(type(e)):
                raise
            raise TranscriptionError(f"SCC file validation failed: {str(e)}")
    
    def _is_valid_scc_timestamp(self, timestamp: str) -> bool:
        """Validate SCC timestamp format (HH:MM:SS:FF).
        
        Args:
            timestamp: Timestamp string to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not timestamp or ':' not in timestamp:
                return False
            
            parts = timestamp.split(':')
            if len(parts) != 4:
                return False
            
            hours, minutes, seconds, frames = parts
            
            # Validate ranges
            if not (0 <= int(hours) <= 23):
                return False
            if not (0 <= int(minutes) <= 59):
                return False
            if not (0 <= int(seconds) <= 59):
                return False
            if not (0 <= int(frames) <= 29):  # SCC uses 30fps
                return False
            
            return True
        except (ValueError, IndexError):
            return False
    
    @handle_transcription_error
    def process_video_pipeline(self, video_path: str, output_dir: Optional[str] = None) -> Dict:
        """Complete video processing pipeline: transcribe, summarize, and validate sidecar files.
        
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
            
            # Step 3: Validate SCC sidecar file
            validated_scc_path = self.create_captions(video_path, scc_path, output_dir)
            
            # Combine results
            pipeline_result = {
                'video_path': video_path,
                'transcription': transcription_result,
                'summary': summary_result,
                'scc_sidecar': validated_scc_path,
                'status': 'completed'
            }
            
            logger.info(f"Pipeline completed for {video_path}")
            logger.info(f"SCC sidecar file ready: {validated_scc_path}")
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