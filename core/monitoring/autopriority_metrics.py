"""
# PURPOSE: Shared helper to emit Redis-backed counters for caption autopriority
# DEPENDENCIES: redis, core.config.REDIS_URL
# MODIFICATION NOTES: v1.0 extracted from task and direct scheduler for reuse
"""

from __future__ import annotations

from typing import Dict

try:
    import redis  # type: ignore
except Exception:
    redis = None

try:
    from core.config import REDIS_URL  # type: ignore
except Exception:  # pragma: no cover - minimal import path for isolated use
    REDIS_URL = "redis://127.0.0.1:6379/0"


def _get_redis_client():
    if redis is None:
        return None
    try:
        return redis.Redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


def increment_counters(scanned: int, enqueued: int, skipped_captioned: int, skipped_seen: int, city_enqueued: Dict[str, int] | None = None) -> None:
    """
    # PURPOSE: Increment global and per-city counters for autopriority actions
    # DEPENDENCIES: Redis; safely no-op if unavailable
    # MODIFICATION NOTES: Use consistent key names across producers/consumers
    """
    r = _get_redis_client()
    if r is None:
        return
    try:
        r.incrby('caption_autopriority_scanned_total', int(scanned))
        r.incrby('caption_autopriority_enqueued_total', int(enqueued))
        r.incrby('caption_autopriority_skipped_captioned_total', int(skipped_captioned))
        r.incrby('caption_autopriority_skipped_alreadyqueued_total', int(skipped_seen))
        if city_enqueued:
            for city_id, count in city_enqueued.items():
                if count:
                    r.hincrby('caption_autopriority_city_enqueued_total', city_id, int(count))
    except Exception:
        # Best-effort; never raise from metrics
        return


