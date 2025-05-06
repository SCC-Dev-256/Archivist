from fastapi.testclient import TestClient
from core.main_fastapi_server import app
import os
import json

client = TestClient(app)

def test_list_files():
    # Ensure NAS_PATH has at least one .mp4 for this test
    response = client.get("/files")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_transcription_endpoint():
    fake_path = "/mnt/nas/test_video.mp4"
    response = client.post("/transcribe", json={"video_path": fake_path})
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data

def test_get_status_unknown_job():
    response = client.get("/status/unknownjobid")
    assert response.status_code == 200
    assert response.json()["status"] == "unknown"
