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