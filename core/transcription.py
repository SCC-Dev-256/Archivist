"""Synchronous wrapper for the Celery WhisperX transcription task."""

from loguru import logger
from celery import current_task
from typing import Dict
import os

from core.config import (
    WHISPER_MODEL,
    USE_GPU,
    COMPUTE_TYPE,
    BATCH_SIZE,
    NUM_WORKERS,
    LANGUAGE,
    OUTPUT_DIR,
)


def _whisperx_transcribe(video_path: str) -> Dict:
    """Transcribe ``video_path`` with faster-whisper and return result dict."""
    from faster_whisper import WhisperModel  # Imported lazily for tests

    device = "cuda" if USE_GPU else "cpu"
    model = WhisperModel(WHISPER_MODEL, device=device, compute_type=COMPUTE_TYPE)

    segments, info = model.transcribe(
        video_path,
        batch_size=BATCH_SIZE,
        num_workers=NUM_WORKERS,
        language=LANGUAGE,
    )

    base = os.path.splitext(os.path.basename(video_path))[0]
    srt_path = os.path.join(OUTPUT_DIR, f"{base}.srt")

    def fmt(ts: float) -> str:
        h = int(ts // 3600)
        m = int((ts % 3600) // 60)
        s = int(ts % 60)
        ms = int((ts - int(ts)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(srt_path, "w", encoding="utf-8") as fh:
        for idx, seg in enumerate(segments, start=1):
            fh.write(f"{idx}\n{fmt(seg.start)} --> {fmt(seg.end)}\n{seg.text.strip()}\n\n")

    return {
        "output_path": srt_path,
        "status": "completed",
        "segments": idx,
        "duration": getattr(info, "duration", 0),
    }


def run_whisper_transcription(*args, **kwargs):
    """Run WhisperX transcription and return the resulting SCC path.

    This helper submits the ``transcription.run_whisper`` Celery task and
    blocks until the task completes.  When called from within an existing
    Celery worker (``current_task`` is available), the transcription is
    performed directly via :class:`~core.services.transcription.TranscriptionService`
    to avoid dispatching a nested Celery task.

    Parameters
    ----------
    video_path : str
        Path to the video file to transcribe.  This can be passed either as a
        positional argument or via the ``video_path`` keyword.

    Returns
    -------
    Dict
        Result dictionary produced by the Celery task or service layer.  The
        ``output_path`` key contains the path to the generated SCC file.
    """

    video_path = kwargs.get("video_path")
    if not video_path and args:
        video_path = args[0]

    if not video_path:
        raise ValueError("video_path is required")

    try:
        # If we already run inside a Celery worker, run the service directly to
        # prevent spawning a nested task.
        if current_task and getattr(current_task, "request", None):
            logger.debug(
                "Running transcription synchronously inside Celery worker for %s",
                video_path,
            )
            return _whisperx_transcribe(video_path)

        # Otherwise dispatch the Celery task and wait for completion.
        from core.tasks.transcription import run_whisper_transcription as task

        async_result = task.delay(video_path)
        logger.debug(
            "Dispatched Celery transcription task %s for %s", async_result.id, video_path
        )
        return async_result.get(timeout=3600)
    except Exception as exc:  # pragma: no cover - fallback path
        logger.error(
            "Celery transcription failed (%s); running directly", exc
        )
        return _whisperx_transcribe(video_path)

