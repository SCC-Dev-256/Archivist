"""Synchronous wrapper for the Celery WhisperX transcription task."""

import os
import subprocess
import tempfile
from typing import Dict
from loguru import logger
from celery import current_task
from core.config import WHISPER_MODEL, USE_GPU, LANGUAGE, COMPUTE_TYPE, BATCH_SIZE


def _transcribe_with_faster_whisper(video_path: str) -> Dict:
    """Direct transcription using faster-whisper library.
    
    This function performs transcription directly without going through the service layer
    to avoid circular imports. It uses faster-whisper to transcribe the video and
    generates SCC format output.
    
    Args:
        video_path: Path to the video file to transcribe
        
    Returns:
        Dictionary containing transcription results with SCC output path
    """
    try:
        from faster_whisper import WhisperModel
        
        # Initialize the model
        logger.debug(f"Loading Whisper model: {WHISPER_MODEL}")
        model = WhisperModel(
            WHISPER_MODEL,
            device="cuda" if USE_GPU else "cpu",
            compute_type=COMPUTE_TYPE,
            cpu_threads=BATCH_SIZE
        )
        
        # Transcribe the audio
        logger.debug(f"Starting transcription of {video_path}")
        segments, info = model.transcribe(
            video_path,
            language=LANGUAGE,
            beam_size=5,
            word_timestamps=True
        )
        
        # Convert segments to list for processing
        segments_list = list(segments)
        
        # Generate output paths
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_dir = os.path.dirname(video_path)
        
        # Generate SCC file
        scc_path = os.path.join(output_dir, f"{base_name}.scc")
        
        # Write SCC file
        with open(scc_path, 'w', encoding='utf-8') as f:
            f.write("Scenarist_SCC V1.0\n\n")
            
            for i, segment in enumerate(segments_list, 1):
                # Convert timestamps to SCC format (HH:MM:SS:FF)
                start_time = segment.start
                end_time = segment.end
                
                # Convert to SCC timestamp format
                start_scc = _seconds_to_scc_timestamp(start_time)
                end_scc = _seconds_to_scc_timestamp(end_time)
                
                # Write caption entry
                f.write(f"{start_scc}\t{end_scc}\n")
                f.write(f"{segment.text.strip()}\n\n")
        
        logger.debug(f"Transcription completed. SCC saved to: {scc_path}")
        
        return {
            'output_path': scc_path,
            'srt_path': scc_path,  # For backward compatibility
            'segments': len(segments_list),
            'duration': info.duration if hasattr(info, 'duration') else 0,
            'language': info.language if hasattr(info, 'language') else LANGUAGE,
            'status': 'completed'
        }
        
    except Exception as e:
        logger.error(f"Direct transcription failed: {e}")
        raise


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


def run_whisper_transcription(*args, **kwargs):
    """Run WhisperX transcription and return the resulting SCC path.

    This helper submits the ``transcription.run_whisper`` Celery task and
    blocks until the task completes.  When called from within an existing
    Celery worker (``current_task`` is available), the transcription is
    performed directly via faster-whisper to avoid dispatching a nested
    Celery task.

    Parameters
    ----------
    video_path : str
        Path to the video file to transcribe.  This can be passed either as a
        positional argument or via the ``video_path`` keyword.

    Returns
    -------
    Dict
        Result dictionary produced by the Celery task or direct transcription.  The
        ``output_path`` key contains the path to the generated SCC file.
    """

    video_path = kwargs.get("video_path")
    if not video_path and args:
        video_path = args[0]

    if not video_path:
        raise ValueError("video_path is required")

    try:
        # If we already run inside a Celery worker, run transcription directly to
        # prevent spawning a nested task.
        if current_task and getattr(current_task, "request", None):
            logger.debug(
                "Running transcription directly inside Celery worker for %s",
                video_path,
            )
            return _transcribe_with_faster_whisper(video_path)

        # Otherwise dispatch the Celery task and wait for completion.
        from core.tasks.transcription import run_whisper_transcription as task

        async_result = task.delay(video_path)
        logger.debug(
            "Dispatched Celery transcription task %s for %s", async_result.id, video_path
        )
        return async_result.get(timeout=3600)
    except Exception as exc:  # pragma: no cover - fallback path
        logger.error(
            "Celery transcription failed (%s); falling back to direct transcription", exc
        )
        return _transcribe_with_faster_whisper(video_path)

