from __future__ import annotations

"""Daily caption check task.

This task runs once per day (scheduled via Celery beat) and verifies that the
most-recent VOD asset for each member city has captions.  If captions are
missing, it logs an error and notifies the alerting channel.
"""

from datetime import datetime
from loguru import logger
from core.tasks import celery_app
from core.config import MEMBER_CITIES
from core.cablecast_client import CablecastAPIClient

try:
    from core.utils.alerts import send_alert  # type: ignore
except ImportError:
    # Fallback no-op implementation if alerts helper is missing
    def send_alert(level: str, message: str, **kwargs):  # type: ignore
        logger.warning(f"[ALERT-{level.upper()}] {message} | Extra: {kwargs}")

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def check_city_latest_vod(city_id: str, client: CablecastAPIClient) -> bool:
    """Return True if latest VOD for *city_id* has captions, else False."""
    try:
        latest = client.get_latest_vod(city_id)
        if not latest:
            logger.warning(f"No VOD found for city {city_id}")
            return True  # Nothing to check
        vod_id = latest.get("id")
        has_captions = client.get_vod_captions(vod_id)
        return bool(has_captions)
    except Exception as exc:  # pragma: no cover
        logger.error(f"Caption check failed for {city_id}: {exc}")
        return False

# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(name="caption_checks.check_latest_vod_captions")
def check_latest_vod_captions() -> None:
    """Celery entry-point: run daily caption verification for each city."""
    client = CablecastAPIClient()
    missing: list[tuple[str, int]] = []

    for city_id in MEMBER_CITIES.keys():
        ok = check_city_latest_vod(city_id, client)
        if not ok:
            # get latest again to obtain vod_id for alert context
            latest = client.get_latest_vod(city_id) or {}
            vod_id = latest.get("id", -1)
            missing.append((city_id, vod_id))

    if missing:
        for city_id, vod_id in missing:
            city_name = MEMBER_CITIES[city_id]["name"]
            msg = f"Captions missing for latest VOD (id={vod_id}) in {city_name}"
            send_alert("error", msg, city=city_name, vod_id=vod_id, ts=datetime.utcnow().isoformat())
            logger.error(msg)
    else:
        logger.info("Daily caption check: all cities OK") 