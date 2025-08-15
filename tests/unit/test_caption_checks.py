from unittest.mock import patch, MagicMock
from core.tasks.caption_checks import check_latest_vod_captions
from core.config import MEMBER_CITIES


def _mock_client(has_captions: bool):
    client = MagicMock()
    # Each city returns latest vod id 1
    client.get_latest_vod.side_effect = lambda city_id: {"id": 1}
    client.get_vod_captions.return_value = has_captions
    return client


def test_all_captions_present(monkeypatch):
    # Mock CablecastAPIClient inside task to simulate captions present
    monkeypatch.setattr(
        "core.tasks.caption_checks.CablecastAPIClient", lambda: _mock_client(True)
    )

    # Should not raise and log info
    check_latest_vod_captions()


def test_missing_captions(monkeypatch):
    monkeypatch.setattr(
        "core.tasks.caption_checks.CablecastAPIClient", lambda: _mock_client(False)
    )

    missing = []

    def fake_alert(level, message, **ctx):
        missing.append((level, message))

    monkeypatch.setattr("core.tasks.caption_checks.send_alert", fake_alert)

    check_latest_vod_captions()
    # Ensure an alert was sent for first city
    assert missing, "Alert should be sent when captions missing"
    assert missing[0][0] == "error" 