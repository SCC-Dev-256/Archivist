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

celery_app = Celery(
    "archivist",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "core.tasks.caption_checks",
        "core.tasks.vod_processing",
        "core.tasks.transcription",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=86400,
    timezone="UTC",
    enable_utc=True,
)

logger.info(f"Celery app initialised with broker {REDIS_URL}")

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
registered_tasks = celery_app.tasks.keys()
vod_tasks = [task for task in registered_tasks if any(vod_task in task for vod_task in ['process_recent_vods', 'download_vod_content', 'generate_vod_captions', 'retranscode_vod', 'upload_captioned_vod', 'validate_vod_quality', 'cleanup_temp_files'])]
transcription_tasks = [task for task in registered_tasks if 'transcription' in task]
logger.info(f"Registered VOD processing tasks: {len(vod_tasks)}")
logger.info(f"Registered transcription tasks: {len(transcription_tasks)}")
for task in vod_tasks:
    logger.debug(f"  - {task}")
for task in transcription_tasks:
    logger.debug(f"  - {task}") 