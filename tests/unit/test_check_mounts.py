import os
import importlib.util
from pathlib import Path
import sys
import types

if 'loguru' not in sys.modules:
    dummy_logger = types.SimpleNamespace(
        logger=types.SimpleNamespace(
            critical=lambda *a, **k: None,
            error=lambda *a, **k: None,
            info=lambda *a, **k: None,
            warning=lambda *a, **k: None,
        )
    )
    sys.modules['loguru'] = dummy_logger

from loguru import logger
from core.services import FileService

# Use the service layer instead of direct import
file_service = FileService()
verify_critical_mounts = file_service.verify_critical_mounts

all_mounts = [
    "/mnt/flex-1",
    "/mnt/flex-2",
    "/mnt/flex-3",
    "/mnt/flex-4",
    "/mnt/flex-5",
    "/mnt/flex-6",
    "/mnt/flex-7",
    "/mnt/flex-8",
    "/mnt/flex-9",
    "/mnt/smb_share",
]

def test_verify_all_mounts_present(monkeypatch):
    calls = []
    monkeypatch.setattr(os.path, "ismount", lambda p: calls.append(p) or True)
    assert verify_critical_mounts() is True
    assert set(calls) == set(all_mounts)


def test_verify_missing_mount(monkeypatch):
    messages = []

    def fake_ismount(path):
        return path != "/mnt/flex-2"

    monkeypatch.setattr(os.path, "ismount", fake_ismount)
    monkeypatch.setattr(logger, "critical", lambda msg: messages.append(msg))

    assert verify_critical_mounts() is False
    assert any("/mnt/flex-2" in m for m in messages)