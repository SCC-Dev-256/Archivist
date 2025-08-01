"""Legacy wrapper for transcription operations.

This module provides backward compatibility for existing code that imports
from core.transcription. It delegates to the service layer for all operations.
"""

import os
from typing import Dict
from loguru import logger
from celery import current_task


def _transcribe_with_faster_whisper(video_path: str) -> Dict:
    """Legacy function for direct transcription.
    
    This function is maintained for backward compatibility and delegates
    to the TranscriptionService for actual processing.
    
    Args:
        video_path: Path to the video file to transcribe
        
    Returns:
        Dictionary containing transcription results with SCC output path
    """
    from core.services import TranscriptionService
    service = TranscriptionService()
    return service._transcribe_with_faster_whisper(video_path)


def _seconds_to_scc_timestamp(seconds: float) -> str:
    """Convert seconds to SCC timestamp format (HH:MM:SS:FF).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        SCC timestamp string in format HH:MM:SS:FF
    """
    from core.services.transcription import _seconds_to_scc_timestamp as service_timestamp
    return service_timestamp(seconds)


def run_whisper_transcription(*args, **kwargs):
    """Run WhisperX transcription and return the resulting SCC path.

    This helper delegates to the service layer when possible, falling back to
    direct transcription when called from within a Celery worker to avoid
    circular imports.

    Parameters
    ----------
    video_path : str
        Path to the video file to transcribe.  This can be passed either as a
        positional argument or via the ``video_path`` keyword.

    Returns
    -------
    Dict
        Result dictionary produced by the transcription.  The
        ``output_path`` key contains the path to the generated SCC file.
    """

    video_path = kwargs.get("video_path")
    if not video_path and args:
        video_path = args[0]

    if not video_path:
        raise ValueError("video_path is required")

    try:
        # If we're inside a Celery worker, use direct transcription to avoid circular imports
        if current_task:
            logger.debug(
                "Running transcription directly inside Celery worker for %s",
                video_path,
            )
            return _transcribe_with_faster_whisper(video_path)

        # Otherwise use the service layer
        from core.services import TranscriptionService
        service = TranscriptionService()
        return service.transcribe_file(video_path)
        
    except Exception as exc:
        logger.error(
            "Service layer transcription failed (%s); falling back to direct transcription", exc
        )
        return _transcribe_with_faster_whisper(video_path)

