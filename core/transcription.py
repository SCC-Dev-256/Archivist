"""Synchronous wrapper for the Celery WhisperX transcription task."""

import os
import subprocess
import tempfile
from typing import Dict
from loguru import logger
from celery import current_task

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

