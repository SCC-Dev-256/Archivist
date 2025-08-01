from __future__ import annotations

"""Celery application factory for Archivist tasks.

This module exposes a shared Celery instance configured to use the REDIS_URL
from `core.config`.  All task modules under `core/tasks/` should import the
`celery_app` object and register their tasks via the standard decorator.

Example:
    from core.tasks import celery_app

    @celery_app.task
    def my_task():
        ...
"""

from celery import Celery
from core.config import REDIS_URL
from loguru import logger

# Lazy Celery app initialization
_celery_app = None

def get_celery_app():
    """Get the Celery app instance with lazy initialization."""
    global _celery_app
    if _celery_app is None:
        _celery_app = _create_celery_app()
    return _celery_app

def _create_celery_app():
    """Create and configure the Celery app."""
    app = Celery(
        "archivist",
        broker=REDIS_URL,
        backend=REDIS_URL,
        include=[
            "core.tasks.caption_checks",
            "core.tasks.vod_processing",
            "core.tasks.transcription",
        ],
    )

    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        result_expires=86400,
        timezone="UTC",
        enable_utc=True,
    )

    logger.info(f"Celery app initialised with broker {REDIS_URL}")
    return app

def _import_task_modules():
    """Import task modules lazily when needed."""
    # Import scheduler after app creation
    import core.tasks.scheduler  # noqa: E402,F401

    # Ensure VOD processing tasks are imported and registered
    try:
        import core.tasks.vod_processing  # noqa: E402,F401
        logger.info("VOD processing tasks imported successfully")
    except Exception as e:
        logger.error(f"Failed to import VOD processing tasks: {e}")

    # Ensure transcription tasks are imported and registered
    try:
        import core.tasks.transcription  # noqa: E402,F401
        logger.info("Transcription tasks imported successfully")
    except Exception as e:
        logger.error(f"Failed to import transcription tasks: {e}")

    # Verify task registration
    registered_tasks = _celery_app.tasks.keys()
    vod_tasks = [task for task in registered_tasks if any(vod_task in task for vod_task in ['process_recent_vods', 'download_vod_content', 'generate_vod_captions', 'retranscode_vod', 'upload_captioned_vod', 'validate_vod_quality', 'cleanup_temp_files'])]
    transcription_tasks = [task for task in registered_tasks if any(trans_task in task for trans_task in ['transcription', 'whisper', 'batch_transcription'])]
    logger.info(f"Registered VOD processing tasks: {len(vod_tasks)}")
    logger.info(f"Registered transcription tasks: {len(transcription_tasks)}")
    for task in vod_tasks:
        logger.debug(f"  - {task}")
    for task in transcription_tasks:
        logger.debug(f"  - {task}")

# For backward compatibility, create a property that lazy loads
class LazyCeleryApp:
    """Lazy loading wrapper for Celery app."""
    
    def __init__(self):
        self._modules_imported = False
    
    def __getattr__(self, name):
        app = get_celery_app()
        # Import task modules when first accessed
        if not self._modules_imported:
            _import_task_modules()
            self._modules_imported = True
        return getattr(app, name)
    
    def __call__(self, *args, **kwargs):
        app = get_celery_app()
        # Import task modules when first accessed
        if not self._modules_imported:
            _import_task_modules()
            self._modules_imported = True
        return app(*args, **kwargs)

# Create the lazy app instance
celery_app = LazyCeleryApp()

# For Celery CLI compatibility
celery = celery_app 