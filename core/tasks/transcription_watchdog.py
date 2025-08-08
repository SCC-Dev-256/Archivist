from __future__ import annotations

"""
# PURPOSE: Ensure captioning stays active by backfilling transcription jobs when none are running
# DEPENDENCIES: celery_app, core.config.MEMBER_CITIES, core.tasks.transcription.run_whisper_transcription
# MODIFICATION NOTES: v1.0 - Initial watchdog/backfill task
"""

import os
import glob
from typing import List

from loguru import logger

from core.tasks import celery_app
from core.config import MEMBER_CITIES


def _is_any_transcription_running() -> bool:
    """Return True if any run_whisper transcription task is active or reserved across workers."""
    try:
        i = celery_app.control.inspect()
        active = i.active() or {}
        reserved = i.reserved() or {}

        def has_transcription(entries):
            for worker, tasks in (entries or {}).items():
                for t in tasks or []:
                    if t.get("name") == "transcription.run_whisper":
                        return True
            return False

        if has_transcription(active):
            return True
        if has_transcription(reserved):
            return True
    except Exception as exc:
        logger.warning(f"Watchdog inspect failed: {exc}")
    return False


def _find_candidate_videos(max_total: int) -> List[str]:
    """Find up to max_total surface-level videos on writable mounts that lack SCC."""
    candidates: List[str] = []
    video_exts = ("*.mp4", "*.mov", "*.mkv", "*.m4v", "*.avi", "*.wmv")
    for city_id, cfg in MEMBER_CITIES.items():
        mount = cfg.get("mount_path")
        if not mount or not os.path.ismount(mount):
            continue
        if not os.access(mount, os.W_OK):
            logger.debug(f"Mount not writable, skip backfill: {mount}")
            continue
        # surface-level only
        files: List[str] = []
        for ext in video_exts:
            files.extend(glob.glob(os.path.join(mount, ext)))
        files = [p for p in files if os.path.isfile(p) and os.path.getsize(p) > 5 * 1024 * 1024]
        # prefer newest first
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for p in files:
            base, _ = os.path.splitext(p)
            scc = base + ".scc"
            if not os.path.exists(scc):
                candidates.append(p)
                if len(candidates) >= max_total:
                    return candidates
    return candidates


@celery_app.task(name="transcription.backfill")
def transcription_backfill() -> dict:
    """Backfill transcription jobs when none are running.

    - If any run_whisper tasks are active or reserved, do nothing
    - Otherwise, enqueue up to N candidate surface-level videos with no SCC on writable mounts
    """
    max_total = int(os.getenv("TRANSCRIPTION_BACKFILL_MAX", "3"))
    if _is_any_transcription_running():
        logger.info("Backfill skipped: transcription already running")
        return {"enqueued": 0, "skipped": "active_or_reserved"}

    videos = _find_candidate_videos(max_total)
    if not videos:
        logger.info("Backfill found no eligible videos")
        return {"enqueued": 0, "videos": []}

    from core.tasks.transcription import run_whisper_transcription as transcribe_task

    task_ids: List[str] = []
    for path in videos:
        try:
            res = transcribe_task.delay(path)
            task_ids.append(res.id)
            logger.info(f"Backfill queued transcription: {path} -> {res.id}")
        except Exception as exc:
            logger.error(f"Backfill failed to queue {path}: {exc}")

    return {"enqueued": len(task_ids), "task_ids": task_ids, "videos": videos}


