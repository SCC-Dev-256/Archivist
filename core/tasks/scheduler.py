from __future__ import annotations

"""Celery beat scheduler for periodic Archivist tasks."""

import os
from celery.schedules import crontab
from core.tasks import celery_app
from loguru import logger

# Pull time from env or default 03:00
CAPTION_CHECK_TIME = os.getenv("CAPTION_CHECK_TIME", "03:00")

try:
    hour, minute = map(int, CAPTION_CHECK_TIME.split(":"))
except ValueError:
    logger.error("Invalid CAPTION_CHECK_TIME format – expected HH:MM")
    hour, minute = 3, 0

celery_app.conf.beat_schedule.update(
    {
        "daily-caption-check": {
            "task": "caption_checks.check_latest_vod_captions",
            "schedule": crontab(minute=minute, hour=hour),
            "options": {"timezone": "UTC"},
        },
        "daily-vod-processing": {
            "task": "vod_processing.process_recent_vods",
            "schedule": crontab(minute=0, hour=4),  # Run at 4 AM UTC daily
            "options": {"timezone": "UTC"},
        },
        "vod-cleanup": {
            "task": "vod_processing.cleanup_temp_files",
            "schedule": crontab(minute=30, hour=2),  # Run at 2:30 AM UTC daily
            "options": {"timezone": "UTC"},
        }
    }
)

logger.info(
    f"Registered daily caption check task at {hour:02d}:{minute:02d} UTC via Celery beat"
)
logger.info("Registered daily VOD processing task at 04:00 UTC via Celery beat")
logger.info("Registered VOD cleanup task at 02:30 UTC via Celery beat") 