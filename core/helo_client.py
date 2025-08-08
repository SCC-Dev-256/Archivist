"""
# PURPOSE: Minimal AJA HELO REST client for scheduling and run-time triggers
# DEPENDENCIES: requests, core.config (HELO_*), loguru
# MODIFICATION NOTES: v1 - record/stream control, preset config, status
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import time
import requests
from loguru import logger

from core.config import HELO_REQUEST_TIMEOUT, HELO_MAX_RETRIES


class HeloClient:
    def __init__(self, ip: str, username: str | None = None, password: str | None = None):
        self.base_url = f"http://{ip}"
        self.auth = (username, password) if username and password else None

    def _request(self, method: str, path: str, **kwargs) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        for attempt in range(1, HELO_MAX_RETRIES + 1):
            try:
                resp = requests.request(method, url, auth=self.auth, timeout=HELO_REQUEST_TIMEOUT, **kwargs)
                if resp.status_code in (200, 204):
                    try:
                        return resp.json() if resp.content else {}
                    except Exception:
                        return {}
                logger.warning(f"HELO request {path} failed {resp.status_code}: {resp.text[:200]}")
                return None
            except requests.RequestException as e:
                logger.warning(f"HELO request error attempt {attempt}/{HELO_MAX_RETRIES}: {e}")
                if attempt == HELO_MAX_RETRIES:
                    return None
                time.sleep(1.5 * attempt)
        return None

    # Basic controls based on AJA public REST docs (GitLab reference)
    # See: `https://gitlab.aja.com/pub/rest_api`
    def start_record(self) -> bool:
        r = self._request("POST", "/config?action=record&value=start")
        return r is not None

    def stop_record(self) -> bool:
        r = self._request("POST", "/config?action=record&value=stop")
        return r is not None

    def start_stream(self) -> bool:
        r = self._request("POST", "/config?action=stream&value=start")
        return r is not None

    def stop_stream(self) -> bool:
        r = self._request("POST", "/config?action=stream&value=stop")
        return r is not None

    def set_rtmp(self, rtmp_url: str, stream_key: str | None = None) -> bool:
        # Many deployments require full RTMP url including key; expose both
        payload = {
            "rtmp_url": rtmp_url,
            "stream_key": stream_key or ""
        }
        r = self._request("POST", "/api/rtmp", json=payload)
        return r is not None

    def status(self) -> Optional[Dict[str, Any]]:
        return self._request("GET", "/status")


