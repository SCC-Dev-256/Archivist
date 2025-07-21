"""Synchronous wrapper for the Celery WhisperX transcription task."""

import os
import subprocess
import tempfile
import time
from typing import Dict
from loguru import logger
from celery import current_task
from core.config import WHISPER_MODEL, USE_GPU, LANGUAGE, COMPUTE_TYPE, BATCH_SIZE


def _transcribe_with_faster_whisper(video_path: str) -> Dict:
    """Direct transcription using faster-whisper library.
    
    This function performs transcription directly without going through the service layer
    to avoid circular imports. It uses faster-whisper to transcribe the video and
    generates SCC format output for automatic captioning.
    
    Args:
        video_path: Path to the video file to transcribe
        
    Returns:
        Dictionary containing transcription results with SCC output path
    """
    try:
        from faster_whisper import WhisperModel
        
        # Initialize the model with optimized settings for caption generation
        logger.info(f"Loading Whisper model: {WHISPER_MODEL}")
        model = WhisperModel(
            WHISPER_MODEL,
            device="cuda" if USE_GPU else "cpu",
            compute_type=COMPUTE_TYPE,
            cpu_threads=BATCH_SIZE
        )
        
        # Transcribe the audio with optimized settings for captions
        logger.info(f"Starting transcription of {video_path}")
        segments, info = model.transcribe(
            video_path,
            language=LANGUAGE,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,  # Filter out non-speech segments
            vad_parameters=dict(min_silence_duration_ms=500)  # Reduce silence gaps
        )
        
        # Convert segments to list for processing
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
                'language': info.language if hasattr(info, 'language') else LANGUAGE,
                'status': 'completed',
                'warning': 'No speech detected'
            }
        
        # Generate output paths
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_dir = os.path.dirname(video_path)
        
        # Generate SCC file
        scc_path = os.path.join(output_dir, f"{base_name}.scc")
        
        # Write SCC file with proper formatting for broadcast captions
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
            'language': info.language if hasattr(info, 'language') else LANGUAGE,
            'status': 'completed',
            'model_used': WHISPER_MODEL,
            'processing_time': time.time() if 'time' in globals() else None
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

