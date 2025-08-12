#!/usr/bin/env python3
# PURPOSE: One-shot health script for flex servers and queue/celery ordering checks
# DEPENDENCIES: Python 3.10+, local project imports, optional Redis; run within Archivist venv
# MODIFICATION NOTES: v1.0 (2025-08-12) initial script covering RW checks, Celery beat, ordering, Redis metrics

"""
Description
    Tech-friendly verifier that checks:
    - RW access on all configured flex servers (`/mnt/flex-*`)
    - Celery beat schedule includes autopriority tasks
    - Captioning discovery orders newest → oldest (validation)
    - Optional: reads Redis metrics to ensure all cities enqueue

Imports
    Standard lib + local modules (`core.config`, `core.tasks`, `core.tasks.transcription`)

Constants/config
    Pulls `MEMBER_CITIES`, `REDIS_URL` from `core.config`.
    CLI flags:
      --skip-write: don't attempt write probes
      --as-user USER: attempt write probes via sudo -u USER (if running as root)
      --check-redis: include Redis metrics check
      --max-scan N: limit recent file scan per city when validating ordering

Service or DB calls
    - Celery app config introspection (beat schedule)
    - Optional Redis read of autopriority metrics

Main logic
    Runs checks, prints a concise summary, exits non-zero on failures unless --no-fail

Return value
    Exit code conveys overall pass/fail; prints JSON-like summary lines for tooling.

# NEXT STEP: wire this into an admin endpoint and a systemd timer to run daily with artifact log export.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


# Ensure repository root is on sys.path when invoked from any CWD
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Local project imports
try:
    from core.config import MEMBER_CITIES, REDIS_URL
    from core.tasks import celery_app
    # Internal helper for newest-first listing
    from core.tasks.transcription import _list_recent_videos_for_city  # type: ignore
except Exception as import_err:
    print(f"[FATAL] Failed to import project modules: {import_err}", file=sys.stderr)
    sys.exit(2)


@dataclass
class FlexProbeResult:
    # PURPOSE: Result for a single flex server probe
    # DEPENDENCIES: os, subprocess (optional sudo), filesystem
    # MODIFICATION NOTES: v1.0 initial
    city_id: str
    name: str
    mount_path: str
    is_mount: bool
    can_read: bool
    can_write: bool
    write_test_path: Optional[str]
    error: Optional[str]


@dataclass
class CeleryBeatCheck:
    # PURPOSE: Report of Celery beat schedule expectations
    # DEPENDENCIES: core.tasks.celery_app
    # MODIFICATION NOTES: v1.0 initial
    has_autopriority: bool
    autopriority_entries: List[str]
    schedule_keys: List[str]


@dataclass
class OrderingValidation:
    # PURPOSE: Validate newest→oldest ordering on discovery helper
    # DEPENDENCIES: core.tasks.transcription._list_recent_videos_for_city
    # MODIFICATION NOTES: v1.0 initial
    city_id: str
    mount_path: str
    scanned: int
    is_sorted_desc: Optional[bool]
    error: Optional[str]


def _run_sudo_touch(as_user: str, path: str, timeout_sec: int = 5) -> Tuple[bool, Optional[str]]:
    # PURPOSE: Attempt a write with sudo -u <user> touch <path>
    # DEPENDENCIES: subprocess, sudo
    # MODIFICATION NOTES: v1.0 initial
    try:
        proc = subprocess.run(
            ["sudo", "-u", as_user, "bash", "-lc", f"touch '{path}' && rm -f '{path}'"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        if proc.returncode == 0:
            return True, None
        return False, proc.stderr.strip() or proc.stdout.strip()
    except Exception as e:
        return False, str(e)


def probe_flex_server(city_id: str, cfg: Dict[str, Any], skip_write: bool, as_user: Optional[str]) -> FlexProbeResult:
    # PURPOSE: Probe a single flex server for RW
    # DEPENDENCIES: os, subprocess
    # MODIFICATION NOTES: v1.0 initial
    name = cfg.get("name", city_id)
    mount_path = cfg.get("mount_path", f"/mnt/{city_id}")
    is_mount = os.path.ismount(mount_path)
    can_read = os.access(mount_path, os.R_OK) if is_mount else False
    can_write = False
    write_test_path: Optional[str] = None
    error: Optional[str] = None

    if is_mount and can_read and not skip_write:
        # Try to create a temp file
        write_test_path = os.path.join(mount_path, f".rw_probe_{int(time.time())}.tmp")
        try:
            if as_user:
                ok, err = _run_sudo_touch(as_user, write_test_path)
                can_write = ok
                if not ok:
                    error = f"sudo-touch-failed: {err}"
            else:
                with open(write_test_path, "w", encoding="utf-8") as f:
                    f.write("probe")
                os.remove(write_test_path)
                can_write = True
        except Exception as e:
            error = str(e)
            can_write = False

    return FlexProbeResult(
        city_id=city_id,
        name=name,
        mount_path=mount_path,
        is_mount=is_mount,
        can_read=can_read,
        can_write=can_write if not skip_write else False,
        write_test_path=write_test_path,
        error=error,
    )


def check_celery_beat() -> CeleryBeatCheck:
    # PURPOSE: Verify beat schedule contains autopriority
    # DEPENDENCIES: core.tasks.celery_app
    # MODIFICATION NOTES: v1.0 initial
    schedule = getattr(celery_app.conf, "beat_schedule", {}) or {}
    keys = list(schedule.keys())
    autopriority_keys = [k for k in keys if "autoprioritize" in k or "auto-prioritize" in k]
    has = any("transcription.autoprioritize_newest" == schedule[k].get("task") for k in schedule)
    return CeleryBeatCheck(has_autopriority=has, autopriority_entries=autopriority_keys, schedule_keys=keys)


def validate_ordering_for_city(mount_path: str, city_id: str, max_scan: int) -> OrderingValidation:
    # PURPOSE: Validate newest→oldest ordering using helper
    # DEPENDENCIES: _list_recent_videos_for_city
    # MODIFICATION NOTES: v1.0 initial
    try:
        if not os.path.ismount(mount_path) or not os.access(mount_path, os.R_OK):
            return OrderingValidation(city_id=city_id, mount_path=mount_path, scanned=0, is_sorted_desc=None, error="mount-not-readable")
        paths = _list_recent_videos_for_city(mount_path, max_scan=max_scan)
        # Helper returns list of file paths; ensure modification time is descending
        mtimes: List[float] = []
        for p in paths:
            try:
                mtimes.append(os.path.getmtime(p))
            except Exception:
                mtimes.append(0.0)
        is_sorted_desc = mtimes == sorted(mtimes, reverse=True)
        return OrderingValidation(city_id=city_id, mount_path=mount_path, scanned=len(paths), is_sorted_desc=is_sorted_desc, error=None)
    except Exception as e:
        return OrderingValidation(city_id=city_id, mount_path=mount_path, scanned=0, is_sorted_desc=None, error=str(e))


def read_redis_autopriority_metrics() -> Dict[str, Any]:
    # PURPOSE: Pull per-city enqueue counters from Redis
    # DEPENDENCIES: redis, core.config.REDIS_URL
    # MODIFICATION NOTES: v1.0 initial
    try:
        import redis  # lazy import
        r = redis.from_url(REDIS_URL)
        city_hash = r.hgetall("caption_autopriority_city_enqueued_total") or {}
        # Decode bytes to str/int
        decoded: Dict[str, int] = {}
        for k, v in city_hash.items():
            key = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
            try:
                decoded[key] = int(v)
            except Exception:
                decoded[key] = int(v.decode()) if isinstance(v, (bytes, bytearray)) else 0
        totals = {
            "scanned_total": int(r.get("caption_autopriority_scanned_total") or 0),
            "enqueued_total": int(r.get("caption_autopriority_enqueued_total") or 0),
        }
        return {"per_city_enqueued": decoded, **totals}
    except Exception as e:
        return {"error": str(e)}


def main(argv: Optional[List[str]] = None) -> int:
    # PURPOSE: Entry point
    # DEPENDENCIES: argparse
    # MODIFICATION NOTES: v1.0 initial
    parser = argparse.ArgumentParser(description="Flex + Celery/Queue health check")
    parser.add_argument("--skip-write", action="store_true", help="Skip write probes on flex mounts")
    parser.add_argument("--as-user", default=None, help="Use sudo -u <user> for write probes (requires root)")
    parser.add_argument("--check-redis", action="store_true", help="Read Redis autopriority metrics")
    parser.add_argument("--max-scan", type=int, default=25, help="Max files to scan per city when validating ordering")
    parser.add_argument("--no-fail", action="store_true", help="Always exit 0; useful for dashboards")
    args = parser.parse_args(argv)

    print(f"== Flex server RW checks (effective uid={os.geteuid()}) ==")
    flex_results: List[FlexProbeResult] = []
    for city_id, cfg in MEMBER_CITIES.items():
        res = probe_flex_server(city_id, cfg, skip_write=args.skip_write, as_user=args.as_user)
        flex_results.append(res)
        status = "OK" if (res.is_mount and res.can_read and (args.skip_write or res.can_write)) else "FAIL"
        print(json.dumps({"component": "flex", "city": res.city_id, "name": res.name, "mount": res.mount_path, "status": status, "detail": asdict(res)}))

    print("\n== Celery beat schedule check ==")
    beat = check_celery_beat()
    print(json.dumps({"component": "celery_beat", "has_autopriority": beat.has_autopriority, "entries": beat.autopriority_entries, "total_entries": len(beat.schedule_keys)}))

    print("\n== Ordering validation (newest→oldest) ==")
    ordering: List[OrderingValidation] = []
    for city_id, cfg in MEMBER_CITIES.items():
        mount_path = cfg.get("mount_path")
        v = validate_ordering_for_city(mount_path, city_id, max_scan=args.max_scan)
        ordering.append(v)
        print(json.dumps({"component": "ordering", "city": city_id, "mount": mount_path, "scanned": v.scanned, "sorted_desc": v.is_sorted_desc, "error": v.error}))

    if args.check_redis:
        print("\n== Redis autopriority metrics ==")
        metrics = read_redis_autopriority_metrics()
        print(json.dumps({"component": "redis_metrics", **metrics}))

    # Decide overall status
    failures: List[str] = []
    for r in flex_results:
        if not r.is_mount:
            failures.append(f"not-mounted:{r.city_id}")
        if not r.can_read:
            failures.append(f"not-readable:{r.city_id}")
        if not args.skip_write and not r.can_write:
            failures.append(f"not-writable:{r.city_id}")
    if not beat.has_autopriority:
        failures.append("beat-missing-autopriority")
    for v in ordering:
        if v.is_sorted_desc is False:
            failures.append(f"ordering-bad:{v.city_id}")

    summary = {"component": "summary", "failures": failures, "failure_count": len(failures)}
    print("\n== Summary ==")
    print(json.dumps(summary))

    if args.no_fail:
        return 0
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())


