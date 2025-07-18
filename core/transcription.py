"""Synchronous wrapper for the Celery WhisperX transcription task."""

from loguru import logger
from celery import current_task


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
        # prevent spawning a nested task.  The stubbed Celery implementation
        # used during testing sets ``current_task.request.id`` to ``'dummy'``
        # outside of a worker, so check for a non-dummy ID to detect a real
        # worker environment.
        if (
            current_task
            and getattr(current_task, "request", None)
            and getattr(current_task.request, "id", "dummy") != "dummy"
        ):
            from core.services.transcription import TranscriptionService

            logger.debug(
                "Running transcription synchronously inside Celery worker for %s",
                video_path,
            )
            return TranscriptionService().transcribe_file(video_path)

        # Otherwise dispatch the Celery task and wait for completion.
        from core.tasks.transcription import run_whisper_transcription as task

        async_result = task.delay(video_path)
        logger.debug(
            "Dispatched Celery transcription task %s for %s", async_result.id, video_path
        )
        return async_result.get(timeout=3600)
    except Exception as exc:  # pragma: no cover - fallback path
        logger.error(
            "Celery transcription failed (%s); falling back to direct service", exc
        )
        from core.services.transcription import TranscriptionService

        return TranscriptionService().transcribe_file(video_path)

