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

# Member city mount points with descriptions
member_city_mounts = [
    "/mnt/flex-1",  # Birchwood City Council
    "/mnt/flex-2",  # Dellwood Grant Willernie
    "/mnt/flex-3",  # Lake Elmo City Council
    "/mnt/flex-4",  # Mahtomedi City Council
    "/mnt/flex-5",  # Spare Record Storage 1
    "/mnt/flex-6",  # Spare Record Storage 2
    "/mnt/flex-7",  # Oakdale City Council
    "/mnt/flex-8",  # White Bear Lake City Council
    "/mnt/flex-9",  # White Bear Township Council
]

all_mounts = member_city_mounts + ["/mnt/smb_share"]

def test_verify_all_mounts_present(monkeypatch):
    """Test that all member city mount points are verified"""
    calls = []
    monkeypatch.setattr(os.path, "ismount", lambda p: calls.append(p) or True)
    assert verify_critical_mounts() is True
    assert set(calls) == set(all_mounts)


def test_verify_missing_member_city_mount(monkeypatch):
    """Test that missing member city mount points are detected"""
    messages = []

    def fake_ismount(path):
        # Simulate missing Birchwood mount point
        return path != "/mnt/flex-1"

    monkeypatch.setattr(os.path, "ismount", fake_ismount)
    monkeypatch.setattr(logger, "critical", lambda msg: messages.append(msg))

    assert verify_critical_mounts() is False
    assert any("/mnt/flex-1" in m for m in messages)
    assert any("Birchwood" in m for m in messages)


def test_verify_missing_spare_storage_mount(monkeypatch):
    """Test that missing spare storage mount points are detected"""
    messages = []

    def fake_ismount(path):
        # Simulate missing spare storage mount point
        return path != "/mnt/flex-5"

    monkeypatch.setattr(os.path, "ismount", fake_ismount)
    monkeypatch.setattr(logger, "critical", lambda msg: messages.append(msg))

    assert verify_critical_mounts() is False
    assert any("/mnt/flex-5" in m for m in messages)
    assert any("Spare Record Storage" in m for m in messages)