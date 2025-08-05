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
import os

celery_app = Celery(
    "archivist",
    include=[
        "core.tasks.caption_checks",
        "core.tasks.vod_processing",
        "core.tasks.transcription",
        "core.tasks.transcription_linking",
        "core.tasks.health_checks",
    ],
)

# Set configuration explicitly
celery_app.conf.broker_url = REDIS_URL
celery_app.conf.result_backend = REDIS_URL
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_expires = 86400
celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True

# Allow running tasks synchronously when a broker isn't available
if os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() == "true":
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    logger.warning("Celery configured for eager execution; tasks run synchronously")

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

# Ensure transcription linking tasks are imported and registered
try:
    import core.tasks.transcription_linking  # noqa: E402,F401
    logger.info("Transcription linking tasks imported successfully")
except Exception as e:
    logger.error(f"Failed to import transcription linking tasks: {e}")

# Ensure health check tasks are imported and registered
try:
    import core.tasks.health_checks  # noqa: E402,F401
    logger.info("Health check tasks imported successfully")
except Exception as e:
    logger.error(f"Failed to import health check tasks: {e}")

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