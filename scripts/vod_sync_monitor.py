#!/usr/bin/env python3
"""Monitor VOD sync status periodically."""

import logging
import os
import time

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/vod_sync_monitor.log"),
        logging.StreamHandler(),
    ],
)

API_BASE_URL = os.getenv("ARCHIVIST_URL", "http://localhost:5000")
CHECK_INTERVAL = int(os.getenv("VOD_SYNC_CHECK_INTERVAL", "300"))


def check_sync_status() -> None:
    """Query the /api/vod/sync-status endpoint and log results."""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/vod/sync-status", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            logging.info(
                "Synced %s/%s transcriptions (%.1f%%)",
                data.get("synced_transcriptions"),
                data.get("total_transcriptions"),
                data.get("sync_percentage"),
            )
        else:
            logging.error("Sync status request failed with status %s", resp.status_code)
    except Exception as exc:
        logging.error("Error checking sync status: %s", exc)


def main() -> None:
    while True:
        check_sync_status()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
