from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class SiteConfig:
    """Configuration for a single site to scrape."""

    url: str
    city: str
    selectors: List[str]
    google_drive: bool = False
    notes: str = ""


def load_config(path: str | Path) -> List[SiteConfig]:
    """Load site configuration from *path*.

    The configuration file is expected to contain a JSON array of objects with
    ``url``, ``city`` and ``selectors`` keys. Missing optional keys fall back to
    defaults.
    """

    data = json.loads(Path(path).read_text())
    sites: List[SiteConfig] = []
    for entry in data:
        sites.append(
            SiteConfig(
                url=entry["url"],
                city=entry["city"],
                selectors=entry.get("selectors", []),
                google_drive=entry.get("google_drive", False),
                notes=entry.get("notes", ""),
            )
        )
    return sites
