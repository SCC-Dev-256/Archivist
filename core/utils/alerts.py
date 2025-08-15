from __future__ import annotations

"""Alert utilities for Archivist.

Currently supports Slack webhook notifications but can be extended to email,
SMS, etc.  The helper is intentionally lightweight so it can be used inside
Celery tasks without heavy dependencies.
"""

import os
import json
import requests
from loguru import logger
from typing import Any, Dict

SLACK_WEBHOOK = os.getenv("ALERT_SLACK_WEBHOOK")


def _post_json(url: str, payload: Dict[str, Any]) -> None:  # pragma: no cover
    try:
        headers = {"Content-Type": "application/json"}
        requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to send alert to {url}: {exc}")


def send_alert(level: str, message: str, **context: Any) -> None:
    """Send an alert.

    Parameters
    ----------
    level: str
        e.g. "info", "warning", "error".
    message: str
        Human-readable message.
    context: dict
        Extra key/value pairs to embed in JSON payload.
    """
    logger.bind(alert_level=level).log(level.upper(), message)

    payload = {
        "text": f"[{level.upper()}] {message}",
        "attachments": [
            {
                "color": "#ff0000" if level == "error" else "#439FE0",
                "fields": [
                    {"title": k, "value": str(v), "short": True}
                    for k, v in context.items()
                ],
            }
        ],
    }

    if SLACK_WEBHOOK:
        _post_json(SLACK_WEBHOOK, payload)
    else:
        logger.warning("SLACK_WEBHOOK not configured; alert logged locally only") 