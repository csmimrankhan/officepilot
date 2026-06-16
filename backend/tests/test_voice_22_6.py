"""Phase 22 voice command tests (updated for Phase 17 auth)."""

import pytest
from app.config import get_settings


pytestmark = pytest.mark.usefixtures("_reset_settings_cache_and_fake_client")


@pytest.fixture()
def client_with_auth(client, db_session):
    resp = client.post("/api/auth/register", json={
        "email": "voice-test-22@test.com", "password": "Test@123456", "full_name": "Voice Test",
    })
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_transcribe_mock(client):
    fake_audio = b"fake audio content"
    files = {"file": ("recording.webm", fake_audio, "audio/webm")}
    response = client.post("/api/voice/transcribe", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["transcript"] == "show pending invoices"
    assert data["provider"] == "mock"


def test_transcribe_cloud_blocked_by_default():
    settings = get_settings()
    assert settings.voice_allow_cloud_stt is False


def test_parser_natural_variations(client_with_auth):
    # Phase 23+ parser delegates to build_accountant_plan()
    cases = [
        ("show me pending invoices", "general", "Execute Task"),
        ("read this screen", "general", "Execute Task"),
        ("export approved invoices to excel", "general", "Execute Task"),
        ("stop everything", "general", "Execute Task"),
    ]
    for text, expected_domain, expected_intent in cases:
        response = client_with_auth.post("/api/voice/parse-command", json={"raw_text": text})
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == expected_domain
        assert data["intent"] == expected_intent


def test_parser_blocked_commands(client_with_auth):
    response = client_with_auth.post("/api/voice/parse-command", json={"raw_text": "delete all my invoices"})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "blocked"


def test_parser_clarification(client_with_auth):
    response = client_with_auth.post("/api/voice/parse-command", json={"raw_text": "send it"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "Execute Task"
    assert data["risk_level"] == "low"


def test_voice_history_captures_metadata(client_with_auth):
    client_with_auth.post("/api/voice/parse-command", json={"raw_text": "show pending"})
    response = client_with_auth.get("/api/voice/history")
    assert response.status_code == 200
    data = response.json()
    latest = data["commands"][0]
    assert "provider" in latest
    assert "confidence" in latest
    assert "clarification_needed" in latest
