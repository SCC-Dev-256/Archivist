"""
Centralized config entry point for Archivist.

Exports:
- get_env_config: Load environment variables from the appropriate .env file
- get_docker_compose_path: Return path to docker-compose.yml
- get_systemd_service_path: Return path to systemd service file
"""

import os
from pathlib import Path

def get_env_config(env: str = "development") -> str:
    """Return the path to the .env file for the given environment."""
    base = Path(__file__).parent
    if env == "production":
        return str(base / "production" / ".env")
    return str(base / "development" / ".env")

def get_docker_compose_path() -> str:
    return str(Path(__file__).parent / "docker" / "docker-compose.yml")

def get_systemd_service_path() -> str:
    return str(Path(__file__).parent / "systemd" / "archivist-vod.service") 