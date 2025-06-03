import json
import os

import pytest
from fastapi.testclient import TestClient

import core.main_fastapi_server as server


@pytest.fixture()
def client(monkeypatch):
    """Create a TestClient with startup checks mocked."""
    monkeypatch.setattr(server, "verify_critical_mounts", lambda: True)
    return TestClient(server.app)


def test_list_files(monkeypatch, client):
    """List files without relying on the real NAS."""
    monkeypatch.setattr(server.os, "listdir", lambda path: ["video.mp4"])
    response = client.get("/files")
    assert response.status_code == 200
    assert response.json() == ["video.mp4"]


def test_transcription_endpoint(monkeypatch, client):
    """Transcribe endpoint returns a job ID with mocks applied."""
    monkeypatch.setattr(server.os.path, "exists", lambda p: True)
    monkeypatch.setattr(server, "enqueue_transcription", lambda p: "job123")
    response = client.post("/transcribe", json={"video_path": "video.mp4"})
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job123"


def test_get_status_unknown_job(monkeypatch, client):
    """Status endpoint returns unknown when job is not found."""
    monkeypatch.setattr(server, "get_job_status", lambda job_id: {"status": "unknown"})
    response = client.get("/status/unknownjobid")
    assert response.status_code == 200
    assert response.json()["status"] == "unknown"