#!/usr/bin/env python3
"""
# PURPOSE: Probe AJA HELO REST API for connectivity and extract RTMP settings safely
# DEPENDENCIES: requests
# MODIFICATION NOTES: v1 - GET-only checks; no start/stop to avoid impacting live.
"""

from __future__ import annotations

import json
import sys
from typing import Dict, Any, Optional

import requests


DEVICES: Dict[str, Dict[str, str]] = {
    # name: {ip, username, password}
    "birchwood": {"ip": "192.168.121.86", "username": "admin", "password": "admin"},
    "grant": {"ip": "98.59.110.70", "username": "admin", "password": "admin"},
    "heritage_hall": {"ip": "192.168.183.174", "username": "admin", "password": "admin"},
    "lake_elmo": {"ip": "192.168.183.209", "username": "admin", "password": "admin"},
    "mahtomedi": {"ip": "192.168.183.78", "username": "admin", "password": "admin"},
    "oakdale": {"ip": "192.168.183.118", "username": "admin", "password": "admin"},
    "white_bear_lake": {"ip": "192.168.183.157", "username": "admin", "password": "admin"},
}


def http_json(method: str, url: str, auth: Optional[tuple[str, str]], timeout: int = 6) -> Optional[Dict[str, Any]]:
    try:
        r = requests.request(method, url, auth=auth, timeout=timeout)
        if r.status_code in (200, 204):
            try:
                return r.json() if r.content else {}
            except Exception:
                return {"raw": r.text[:500]}
        return None
    except requests.RequestException:
        return None


def probe_device(name: str, ip: str, user: str, pw: str) -> Dict[str, Any]:
    base = f"http://{ip}"
    auth = (user, pw) if user or pw else None

    result: Dict[str, Any] = {"device": name, "ip": ip, "reachable": False}

    status = http_json("GET", f"{base}/status", auth)
    if status is not None:
        result["reachable"] = True
        result["status"] = status

    # Try to get RTMP settings from common endpoints
    rtmp = http_json("GET", f"{base}/api/rtmp", auth)
    if not rtmp:
        rtmp = http_json("GET", f"{base}/rtmp", auth)
    if not rtmp:
        rtmp = http_json("GET", f"{base}/config?action=rtmp_url", auth)
    if rtmp:
        result["rtmp"] = rtmp

    # Check control endpoints existence (without triggering)
    # Some servers return 405 for GET where POST is required; presence still indicates URL exists
    ctrl_record = http_json("GET", f"{base}/config?action=record&value=status", auth) or http_json(
        "GET", f"{base}/config?action=record", auth
    )
    ctrl_stream = http_json("GET", f"{base}/config?action=stream&value=status", auth) or http_json(
        "GET", f"{base}/config?action=stream", auth
    )
    result["control_record_endpoint_detected"] = ctrl_record is not None
    result["control_stream_endpoint_detected"] = ctrl_stream is not None

    return result


def main() -> int:
    summary = []
    for name, conf in DEVICES.items():
        out = probe_device(name, conf["ip"], conf.get("username", ""), conf.get("password", ""))
        summary.append(out)
        print(json.dumps(out, indent=2))
    # Derive a clean report of RTMP settings
    print("\n=== RTMP SUMMARY ===")
    for item in summary:
        rtmp = item.get("rtmp") or {}
        print(f"{item['device']:16} {item['ip']:>15} -> url={rtmp.get('rtmp_url') or rtmp.get('url') or ''} key={rtmp.get('stream_key') or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


