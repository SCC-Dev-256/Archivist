from __future__ import annotations

# PURPOSE: Strict, validated configuration loading for site scraping
# DEPENDENCIES: pydantic (v2), json, pathlib
# MODIFICATION NOTES: v2.0 - Add schema validation, robust error handling, and type safety

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from pydantic import BaseModel, HttpUrl, ValidationError, field_validator


class SiteConfigModel(BaseModel):
    url: HttpUrl
    city: str
    selectors: List[str]
    google_drive: bool = False
    notes: str = ""
    allowed_domains: List[str] | None = None

    @field_validator("city")
    @classmethod
    def validate_city(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("city must be a non-empty string")
        return value

    @field_validator("selectors")
    @classmethod
    def validate_selectors(cls, selectors: List[str]) -> List[str]:
        if not isinstance(selectors, list):
            raise ValueError("selectors must be a list of CSS selectors")
        clean = []
        for sel in selectors:
            if not isinstance(sel, str):
                raise ValueError("each selector must be a string")
            s = sel.strip()
            if not s:
                continue
            clean.append(s)
        if not clean:
            raise ValueError("selectors must contain at least one non-empty selector")
        return clean


@dataclass
class SiteConfig:
    url: str
    city: str
    selectors: List[str]
    google_drive: bool = False
    notes: str = ""
    allowed_domains: List[str] | None = None


def load_config(path: str | Path) -> List[SiteConfig]:
    """Load and validate site configuration from *path* (JSON array).

    Raises ValueError with detailed context on malformed JSON or schema errors.
    """

    config_path = Path(path)
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Configuration file not found: {config_path}") from exc
    except OSError as exc:
        raise ValueError(f"Cannot read configuration file: {config_path}: {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in configuration {config_path} at line {exc.lineno} column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, list):
        raise ValueError("Configuration root must be a JSON array of site objects")

    sites: List[SiteConfig] = []
    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry at index {idx} must be an object, got {type(entry).__name__}")
        try:
            model = SiteConfigModel.model_validate(entry)
        except ValidationError as exc:
            raise ValueError(f"Invalid site configuration at index {idx}: {exc}") from exc

        sites.append(
            SiteConfig(
                url=str(model.url),
                city=model.city,
                selectors=model.selectors,
                google_drive=model.google_drive,
                notes=model.notes,
                allowed_domains=model.allowed_domains,
            )
        )

    return sites
