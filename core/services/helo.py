"""
# PURPOSE: Service to sync Cablecast shows into AJA HELO schedules and trigger start/stop
# DEPENDENCIES: core.cablecast_client, core.helo_client, core.models, core.config, SQLAlchemy session
# MODIFICATION NOTES: v1 - schedule creation, idempotent sync, run-time triggers
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from loguru import logger
from sqlalchemy import and_

from core.cablecast_client import CablecastAPIClient
from core.helo_client import HeloClient
from core.models import HeloDeviceORM, HeloScheduleORM, CablecastShowORM
from core.database import db
from core.config import HELO_DEVICES, HELO_ENABLE_RUNTIME_TRIGGERS, HELO_SCHEDULE_LOOKAHEAD_MIN
from core.config import CABLECAST_LOCATION_ID, CITY_ALIASES_TO_HELO
from core.config import CABLECAST_CHANNEL_ID, CABLECAST_DEFAULT_RUN_SECONDS
try:
    from core.config import CABLECAST_CHANNEL_TO_CITY  # optional mapping
except Exception:
    CABLECAST_CHANNEL_TO_CITY = {}
try:
    from core.config import CABLECAST_LOCATION_TO_CITY  # optional mapping
except Exception:
    CABLECAST_LOCATION_TO_CITY = {}


@dataclass
class SchedulePlan:
    city_key: str
    device: HeloDeviceORM
    show: CablecastShowORM
    start_time: datetime
    end_time: datetime
    action: str  # 'record' | 'stream' | 'record+stream'


class HeloService:
    def __init__(self):
        self.cablecast = CablecastAPIClient()

    # Device registry -------------------------------------------------------
    def upsert_devices_from_config(self) -> int:
        updated = 0
        for city_key, conf in HELO_DEVICES.items():
            device = HeloDeviceORM.query.filter_by(city_key=city_key).first()
            if not device:
                device = HeloDeviceORM(city_key=city_key, ip=conf.get("ip", ""))
                db.session.add(device)
            # Update fields
            device.ip = conf.get("ip", device.ip)
            device.username = conf.get("username", device.username)
            device.password = conf.get("password", device.password)
            device.rtmp_url = conf.get("rtmp_url", device.rtmp_url)
            device.stream_key = conf.get("stream_key", device.stream_key)
            updated += 1
        # Optional: tie devices to configured channel ids for index/reporting
        for ch, city in (CABLECAST_CHANNEL_TO_CITY or {}).items():
            dev = HeloDeviceORM.query.filter_by(city_key=city).first()
            if not dev:
                continue
            try:
                ch_int = int(ch)
            except Exception:
                continue
            if getattr(dev, "cablecast_channel_id", None) != ch_int:
                dev.cablecast_channel_id = ch_int
                updated += 1
        db.session.commit()
        return updated

    # Planning --------------------------------------------------------------
    def build_plans_from_cablecast(self, lookahead_minutes: int | None = None) -> List[SchedulePlan]:
        lookahead = lookahead_minutes or HELO_SCHEDULE_LOOKAHEAD_MIN
        now = datetime.now(timezone.utc)
        horizon = now + timedelta(minutes=lookahead)
        # Pre-roll so streams start a bit early
        preroll_seconds = int(os.getenv("HELO_PREROLL_SECONDS", "60"))
        preroll_delta = timedelta(seconds=preroll_seconds)

        # Prefer precise runs from Cablecast if available
        runs = self.cablecast.get_runs(
            start=now,
            end=horizon,
            channel_id=int(CABLECAST_CHANNEL_ID) if CABLECAST_CHANNEL_ID else None,
            location_id=int(CABLECAST_LOCATION_ID) if CABLECAST_LOCATION_ID else None,
        )
        if runs:
            return self._plans_from_runs(runs, preroll_delta)

        # Fallback to heuristic on shows in local DB
        shows: List[CablecastShowORM] = (
            CablecastShowORM.query
            .filter(CablecastShowORM.created_at <= horizon)
            .all()
        )
        devices = {d.city_key: d for d in HeloDeviceORM.query.all()}
        plans: List[SchedulePlan] = []
        for show in shows:
            city_key = self._infer_city_key_from_show(show)
            if not city_key:
                continue
            device = devices.get(city_key)
            if not device:
                logger.warning(f"No HELO device registered for city {city_key} – skipping show {show.id}")
                continue
            start_time = (show.created_at.replace(tzinfo=timezone.utc))
            end_time = start_time + timedelta(seconds=show.duration or 7200)
            plans.append(SchedulePlan(city_key, device, show, start_time, end_time, "record+stream"))
        return plans

    def _plans_from_runs(self, runs: List[dict], preroll_delta: timedelta) -> List[SchedulePlan]:
        devices = {d.city_key: d for d in HeloDeviceORM.query.all()}
        plans: List[SchedulePlan] = []
        for r in runs:
            show_id = r.get('show') or r.get('show_id')
            start_str = r.get('starts_at') or r.get('start')
            end_str = r.get('ends_at') or r.get('end')
            loc_id = r.get('location_id') or r.get('location')
            chan_id = r.get('channel_id') or r.get('channel')
            if not (show_id and start_str and end_str):
                continue
            show = CablecastShowORM.query.filter_by(cablecast_id=show_id).first()
            if not show:
                # optionally pull from API; skip for now
                continue
            try:
                start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                # If ends_at equals starts_at, synthesize a default window
                end_iso = end_str or start_str
                end_time = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
                if end_time <= start_time:
                    end_time = start_time + timedelta(seconds=CABLECAST_DEFAULT_RUN_SECONDS)
            except Exception:
                continue
            start_time = start_time - preroll_delta
            city_key = (
                self._city_from_channel(chan_id)
                or self._city_from_location(loc_id)
                or self._infer_city_key_from_show(show)
            )
            if not city_key:
                continue
            device = devices.get(city_key)
            if not device:
                logger.warning(f"No HELO device for city {city_key} – skipping run for show {show.id}")
                continue
            plans.append(SchedulePlan(city_key, device, show, start_time, end_time, "record+stream"))
        return plans

    def _infer_city_key_from_show(self, show: CablecastShowORM) -> Optional[str]:
        # Prefer alias mapping for multi-city devices
        title = (show.title or "").lower()
        for alias, city_key in (CITY_ALIASES_TO_HELO or {}).items():
            if alias.lower() in title:
                return city_key
        # Fallback: city key present in title
        for city_key in HELO_DEVICES.keys():
            if city_key.lower() in title:
                return city_key
        # Fallback: single device setup
        if len(HELO_DEVICES) == 1:
            return list(HELO_DEVICES.keys())[0]
        return None

    def _city_from_location(self, loc_id: Any) -> Optional[str]:
        try:
            if loc_id is None:
                return None
            # direct mapping if configured
            if CABLECAST_LOCATION_TO_CITY and str(loc_id) in CABLECAST_LOCATION_TO_CITY:
                return CABLECAST_LOCATION_TO_CITY[str(loc_id)]
        except Exception:
            pass
        return None

    def _city_from_channel(self, channel_id: Any) -> Optional[str]:
        try:
            if channel_id is None:
                return None
            if CABLECAST_CHANNEL_TO_CITY and str(channel_id) in CABLECAST_CHANNEL_TO_CITY:
                return CABLECAST_CHANNEL_TO_CITY[str(channel_id)]
        except Exception:
            pass
        return None

    # Scheduling (idempotent) ----------------------------------------------
    def sync_helo_schedules(self, plans: List[SchedulePlan]) -> int:
        created_or_updated = 0
        for plan in plans:
            existing = HeloScheduleORM.query.filter(
                and_(
                    HeloScheduleORM.device_id == plan.device.id,
                    HeloScheduleORM.cablecast_show_id == plan.show.id,
                    HeloScheduleORM.start_time == plan.start_time,
                    HeloScheduleORM.end_time == plan.end_time,
                )
            ).first()

            if not existing:
                sched = HeloScheduleORM(
                    device_id=plan.device.id,
                    cablecast_show_id=plan.show.id,
                    start_time=plan.start_time,
                    end_time=plan.end_time,
                    action=plan.action,
                    status="scheduled",
                )
                db.session.add(sched)
                created_or_updated += 1
            else:
                # keep status if already queued/completed
                if existing.action != plan.action:
                    existing.action = plan.action
                    created_or_updated += 1
        db.session.commit()
        return created_or_updated

    # Runtime triggers ------------------------------------------------------
    def trigger_due_actions(self) -> Dict[str, int]:
        if not HELO_ENABLE_RUNTIME_TRIGGERS:
            return {"started": 0, "stopped": 0}

        now = datetime.now(timezone.utc)
        started = 0
        stopped = 0

        due_to_start = HeloScheduleORM.query.filter(
            and_(HeloScheduleORM.start_time <= now, HeloScheduleORM.status == "scheduled")
        ).all()
        for sched in due_to_start:
            device = HeloDeviceORM.query.get(sched.device_id)
            if not device:
                continue
            client = HeloClient(device.ip, device.username, device.password)
            ok_rec = ok_stream = True
            if "record" in sched.action:
                ok_rec = client.start_record()
            if "stream" in sched.action:
                # configure rtmp if we have defaults
                if device.rtmp_url:
                    client.set_rtmp(device.rtmp_url, device.stream_key)
                ok_stream = client.start_stream()
            if ok_rec and ok_stream:
                sched.status = "queued"
                started += 1
            else:
                sched.status = "failed"
                sched.last_error = "Failed to start one or more actions"

        due_to_stop = HeloScheduleORM.query.filter(
            and_(HeloScheduleORM.end_time <= now, HeloScheduleORM.status.in_(["scheduled", "queued"]))
        ).all()
        for sched in due_to_stop:
            device = HeloDeviceORM.query.get(sched.device_id)
            if not device:
                continue
            client = HeloClient(device.ip, device.username, device.password)
            ok_rec = ok_stream = True
            if "record" in sched.action:
                ok_rec = client.stop_record()
            if "stream" in sched.action:
                ok_stream = client.stop_stream()
            if ok_rec and ok_stream:
                sched.status = "completed"
                stopped += 1
            else:
                sched.status = "failed"
                sched.last_error = "Failed to stop one or more actions"

        db.session.commit()
        return {"started": started, "stopped": stopped}


