"""
# PURPOSE: Celery tasks for HELO schedule sync and runtime triggers
# DEPENDENCIES: core.services.helo.HeloService, celery app
# MODIFICATION NOTES: v1 - two periodic tasks
"""

from __future__ import annotations

from typing import Dict
from loguru import logger

from core.tasks import celery_app
from core.app import app
from core.services import HeloService


@celery_app.task(name="helo.sync_schedules")
def sync_schedules() -> Dict[str, int]:
    with app.app_context():
        service = HeloService()
        updated_devices = service.upsert_devices_from_config()
        plans = service.build_plans_from_cablecast()
        created = service.sync_helo_schedules(plans)
        result = {"devices": updated_devices, "schedules": created}
        logger.info(f"HELO sync complete: {result}")
        return result


@celery_app.task(name="helo.trigger_runtime")
def trigger_runtime() -> Dict[str, int]:
    with app.app_context():
        service = HeloService()
        result = service.trigger_due_actions()
        logger.info(f"HELO runtime triggers: {result}")
        return result


