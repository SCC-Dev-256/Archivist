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

# VOD Processing Schedules
# Primary daily processing run (morning UTC)
VOD_PROCESSING_TIME = os.getenv("VOD_PROCESSING_TIME", "04:00")
# Secondary run (evening/local window) – set to HH:MM or "" to disable
VOD_PROCESSING_TIME_2 = os.getenv("VOD_PROCESSING_TIME_2", "23:00")

def _parse_hhmm(value: str, default: tuple[int, int]) -> tuple[int, int]:
    try:
        h, m = map(int, value.split(":"))
        return h, m
    except Exception:
        logger.error(f"Invalid time format '{value}' – expected HH:MM")
        return default

vod_hour, vod_minute = _parse_hhmm(VOD_PROCESSING_TIME, (4, 0))
vod2 = VOD_PROCESSING_TIME_2.strip()
vod2_parsed = _parse_hhmm(vod2, (23, 0)) if vod2 else None

tz = celery_app.conf.timezone

schedule_updates = {
        "daily-caption-check": {
            "task": "caption_checks.check_latest_vod_captions",
            "schedule": crontab(minute=minute, hour=hour),
            "options": {"timezone": tz},
        },
        "daily-vod-processing": {
            "task": "vod_processing.process_recent_vods",
            "schedule": crontab(minute=vod_minute, hour=vod_hour),
            "options": {"timezone": tz},
        },
        "vod-cleanup": {
            "task": "vod_processing.cleanup_temp_files",
            "schedule": crontab(minute=30, hour=2),  # Run at 2:30 AM UTC daily
            "options": {"timezone": tz},
        },
        "transcription-linking-queue": {
            "task": "transcription_linking.process_queue",
            "schedule": crontab(minute=15, hour="*/2"),  # Run every 2 hours at :15
            "options": {"timezone": tz},
        },
        "transcription-linking-cleanup": {
            "task": "transcription_linking.cleanup_orphaned",
            "schedule": crontab(minute=45, hour=3),  # Run at 3:45 AM UTC daily
            "options": {"timezone": tz},
        },
        "system-health-check": {
            "task": "health_checks.run_scheduled_health_check",
            "schedule": crontab(minute=0, hour="*/1"),  # Run every hour
            "options": {"timezone": tz},
        },
        # Backfill transcription when idle: every 10 minutes
        "transcription-backfill": {
            "task": "transcription.backfill",
            "schedule": crontab(minute="*/10"),
            "options": {"timezone": tz},
        },
}

if vod2_parsed is not None:
    schedule_updates["second-daily-vod-processing"] = {
        "task": "vod_processing.process_recent_vods",
        "schedule": crontab(minute=vod2_parsed[1], hour=vod2_parsed[0]),
        "options": {"timezone": tz},
    }

celery_app.conf.beat_schedule.update(schedule_updates)

logger.info(
    f"Registered daily caption check task at {hour:02d}:{minute:02d} UTC via Celery beat"
)
logger.info(
    f"Registered daily VOD processing task at {vod_hour:02d}:{vod_minute:02d} UTC via Celery beat"
)
if vod2_parsed is not None:
    logger.info(
        f"Registered second daily VOD processing task at {vod2_parsed[0]:02d}:{vod2_parsed[1]:02d} UTC via Celery beat"
    )
logger.info("Registered VOD cleanup task at 02:30 UTC via Celery beat")
logger.info("Registered transcription linking queue processing task every 2 hours via Celery beat")
logger.info("Registered transcription linking cleanup task at 03:45 UTC via Celery beat")
logger.info("Registered system health check task every hour via Celery beat") 