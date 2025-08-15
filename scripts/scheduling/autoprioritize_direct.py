#!/usr/bin/env python3
"""
# PURPOSE: Run a direct, Celery-free auto-prioritization that scans all flex servers,
#          selects newest uncaptioned videos (surface-level), and transcribes them
#          using the existing TranscriptionService. Designed for systemd/cron.
# DEPENDENCIES: core.config.MEMBER_CITIES, core.services.transcription.TranscriptionService,
#               redis (optional, for idempotence and counters)
# MODIFICATION NOTES: v1.0 initial direct scheduler to bridge until Celery workers are available
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List

try:
    from dotenv import load_dotenv
    # Load project .env if present
    load_dotenv(os.environ.get('ARCHIVIST_DOTENV', '/opt/Archivist/.env'), override=True)
except Exception:
    pass

from loguru import logger

try:
    import redis  # type: ignore
except Exception:
    redis = None  # Optional

try:
    # Local project imports
    from core.config import MEMBER_CITIES, REDIS_URL  # type: ignore
    from core.services.transcription import TranscriptionService  # type: ignore
except Exception as e:
    print(f"Failed to import project modules: {e}")
    sys.exit(1)


def _has_scc(path: str) -> bool:
    """Kept for backward compatibility; no longer used (service filters SCC)."""
    base, _ = os.path.splitext(path)
    return os.path.exists(base + '.scc')


def _get_redis():
    """
    # PURPOSE: Build a Redis client if redis is installed and available.
    # DEPENDENCIES: redis, REDIS_URL
    # MODIFICATION NOTES: Optional; falls back to local state file
    """
    if redis is None:
        return None
    try:
        return redis.Redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


def _load_state(path: str) -> Dict[str, float]:
    """
    # PURPOSE: Load local state file of seen paths for idempotence.
    # DEPENDENCIES: json
    # MODIFICATION NOTES: Minimal JSON format { path: last_seen_epoch }
    """
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        return {}
    return {}


def _save_state(path: str, data: Dict[str, float]) -> None:
    """
    # PURPOSE: Save local state file of seen paths.
    # DEPENDENCIES: json
    # MODIFICATION NOTES: best-effort write
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass


def run(max_per_city: int, scan_limit: int, dry_run: bool = False) -> Dict:
    """
    # PURPOSE: Core logic to pick newest uncaptioned videos from all flex servers
    #          and transcribe them directly.
    # DEPENDENCIES: MEMBER_CITIES, TranscriptionService, Redis (optional)
    # MODIFICATION NOTES: v1.0 direct execution; sequential to avoid overload
    """
    r = _get_redis()
    seen_key = 'caption_direct_seen_paths'
    state_path = '/opt/Archivist/.state/autoprioritize_direct.json'
    local_state = _load_state(state_path)

    svc = TranscriptionService()

    scanned_total = 0
    enqueued_total = 0
    skipped_captioned_total = 0
    skipped_seen_total = 0

    results: Dict[str, Dict] = {}

    # Use service-layer selection to avoid duplication
    city_to_picks = svc.pick_newest_uncaptioned(max_per_city=max_per_city, scan_limit=scan_limit)
    for city_id, picked in city_to_picks.items():
        city_name = MEMBER_CITIES.get(city_id, {}).get('name', city_id)
        scanned_total += len(picked)

        filtered: List[str] = []
        for path in picked:
            # seen via Redis?
            if r is not None:
                try:
                    if r.sismember(seen_key, path):
                        skipped_seen_total += 1
                        continue
                except Exception:
                    pass
            # seen via local state?
            if path in local_state:
                skipped_seen_total += 1
                continue
            filtered.append(path)

        processed: List[Dict[str, str]] = []
        for path in picked:
            if dry_run:
                processed.append({'video_path': path, 'output_path': '', 'status': 'dry_run'})
                enqueued_total += 1
                continue
            try:
                res = svc.transcribe_file(path)
                processed.append({'video_path': path, 'output_path': res.get('output_path', ''), 'status': res.get('status', 'unknown')})
                enqueued_total += 1
                # mark seen
                if r is not None:
                    try:
                        r.sadd(seen_key, path)
                        r.expire(seen_key, 7 * 24 * 3600)
                    except Exception:
                        pass
                local_state[path] = time.time()
            except Exception as e:
                logger.error(f"Direct transcription failed for {path}: {e}")

        results[city_id] = {
            'city_name': city_name,
            'scanned': len(picked),
            'picked': filtered,
            'processed': processed,
        }

    # emit counters to Redis if available
    if r is not None:
        try:
            r.incrby('caption_autopriority_scanned_total', scanned_total)
            r.incrby('caption_autopriority_enqueued_total', enqueued_total)
            r.incrby('caption_autopriority_skipped_captioned_total', skipped_captioned_total)
            r.incrby('caption_autopriority_skipped_alreadyqueued_total', skipped_seen_total)
        except Exception:
            pass

    _save_state(state_path, local_state)

    return {
        'timestamp': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'max_per_city': max_per_city,
        'scan_limit': scan_limit,
        'scanned_total': scanned_total,
        'enqueued_total': enqueued_total,
        'skipped_captioned_total': skipped_captioned_total,
        'skipped_seen_total': skipped_seen_total,
        'results': results,
    }


def main() -> int:
    """
    # PURPOSE: CLI entrypoint for systemd/cron invocation.
    # DEPENDENCIES: argparse
    # MODIFICATION NOTES: prints JSON to stdout
    """
    parser = argparse.ArgumentParser(description='Direct autoprioritize transcription (no Celery)')
    parser.add_argument('--max-per-city', type=int, default=1, help='Max new items per city')
    parser.add_argument('--scan-limit', type=int, default=50, help='Max files to scan per city')
    parser.add_argument('--dry-run', action='store_true', help='Do not transcribe, just list picks')
    args = parser.parse_args()

    report = run(args.max_per_city, args.scan_limit, args.dry_run)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())


