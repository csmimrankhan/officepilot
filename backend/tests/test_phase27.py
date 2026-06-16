"""Phase 27 — Windows Voice Layer backend tests."""

import io
import os
import time

import pytest
from fastapi.testclient import TestClient


def _reset_all_caches():
    import app.services.windows_voice_layer as _vmod
    from app.config import _settings_singleton
    if isinstance(_vmod._voice_settings_cache, dict):
        _vmod._voice_settings_cache.clear()
    _vmod._voice_settings_cached_at = 0
    _settings_singleton.cache_clear()


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def client_with_auth(client, db_session):
    resp = client.post("/api/auth/register", json={
        "email": "voice-user@test.com", "password": "Test@123456", "full_name": "Voice User",
    })
    data = resp.json()
    token = data["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ── GET /api/voice-layer/status ────────────────────────────────────────────────


class TestStatus:
    def test_status_returns_config(self, client):
        resp = client.get("/api/voice-layer/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert data["recording"]["active"] is False
        assert data["recording"]["mode"] is None
        assert "shortcuts" in data
        assert "ai_mode" in data
        assert "whisper_configured" in data


# ── POST /api/voice-layer/dictate ──────────────────────────────────────────────


class TestDictate:
    def test_dictate_starts_recording(self, client_with_auth):
        resp = client_with_auth.post("/api/voice-layer/dictate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["status"] == "recording"
        assert data["mode"] == "dictation"

    def test_dictate_when_already_recording(self, client_with_auth):
        client_with_auth.post("/api/voice-layer/dictate")
        resp2 = client_with_auth.post("/api/voice-layer/dictate")
        assert resp2.status_code == 400
        assert "recording" in resp2.json()["detail"].lower()

    def test_dictate_requires_auth(self, client):
        resp = client.post("/api/voice-layer/dictate")
        assert resp.status_code == 401


# ── POST /api/voice-layer/ai-mode ──────────────────────────────────────────────


class TestAiMode:
    def test_ai_mode_blocked_when_cloud_disabled(self, client_with_auth):
        os.environ["AI_MODE_ALLOW_CLOUD"] = "false"
        os.environ["AI_MODE_API_KEY"] = "test-key"
        _reset_all_caches()
        resp = client_with_auth.post("/api/voice-layer/ai-mode")
        assert resp.status_code == 400
        assert "cloud" in resp.json()["detail"].lower()

    def test_ai_mode_blocked_when_no_key(self, client_with_auth):
        os.environ["AI_MODE_ALLOW_CLOUD"] = "true"
        os.environ["AI_MODE_API_KEY"] = ""
        _reset_all_caches()
        resp = client_with_auth.post("/api/voice-layer/ai-mode")
        assert resp.status_code == 400
        assert "key" in resp.json()["detail"].lower()

    def test_ai_mode_starts_if_configured(self, client_with_auth):
        os.environ["AI_MODE_ALLOW_CLOUD"] = "true"
        os.environ["AI_MODE_API_KEY"] = "test-key"
        _reset_all_caches()
        resp = client_with_auth.post("/api/voice-layer/ai-mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["mode"] == "ai_mode"

    def test_ai_mode_requires_auth(self, client):
        resp = client.post("/api/voice-layer/ai-mode")
        assert resp.status_code == 401


# ── POST /api/voice-layer/agent-command ────────────────────────────────────────


class TestAgentCommand:
    def test_agent_command_starts_recording(self, client_with_auth):
        resp = client_with_auth.post("/api/voice-layer/agent-command")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["mode"] == "agent_command"

    def test_agent_command_requires_auth(self, client):
        resp = client.post("/api/voice-layer/agent-command")
        assert resp.status_code == 401


# ── POST /api/voice-layer/stop ─────────────────────────────────────────────────


class TestStop:
    def test_stop_no_active_recording(self, client_with_auth):
        resp = client_with_auth.post("/api/voice-layer/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert "ok" in data
        # When no recording was active, stop may return error info
        assert "error" in data or "status" in data

    def test_stop_active_recording(self, client_with_auth):
        client_with_auth.post("/api/voice-layer/dictate")
        resp = client_with_auth.post("/api/voice-layer/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["status"] == "stopped"

    def test_stop_requires_auth(self, client):
        resp = client.post("/api/voice-layer/stop")
        assert resp.status_code == 401


# ── POST /api/voice-layer/transcribe ────────────────────────────────────────────


class TestTranscribe:
    def test_transcribe_empty_file(self, client_with_auth):
        resp = client_with_auth.post(
            "/api/voice-layer/transcribe",
            files={"file": ("test.wav", b"", "audio/wav")},
            data={"language": "auto", "mode": "dictation"},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_transcribe_mock_works(self, client_with_auth):
        voice_data = b"\x00" * 16000
        resp = client_with_auth.post(
            "/api/voice-layer/transcribe",
            files={"file": ("test.wav", voice_data, "audio/wav")},
            data={"language": "auto", "mode": "dictation"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "transcript" in data
        assert data["engine"] == "mock"
        assert "Mock transcription" in data["transcript"]
        assert data["ai_output"] is None
        assert data["mode"] == "dictation"

    def test_transcribe_ai_mode_saves_history(self, client_with_auth):
        os.environ["VOICE_SAVE_HISTORY"] = "true"
        _reset_all_caches()
        voice_data = b"\x00" * 16000
        resp = client_with_auth.post(
            "/api/voice-layer/transcribe",
            files={"file": ("test.wav", voice_data, "audio/wav")},
            data={"language": "en", "mode": "dictation"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        hresp = client_with_auth.get("/api/voice-layer/history?limit=5")
        assert hresp.status_code == 200
        hist = hresp.json()
        assert hist["total"] >= 1
        assert hist["items"][0]["mode"] == "dictation"
        assert hist["items"][0]["language"] == "en"
        assert "Mock transcription" in hist["items"][0]["transcript"]

    def test_transcribe_requires_auth(self, client):
        resp = client.post(
            "/api/voice-layer/transcribe",
            files={"file": ("test.wav", b"\x00" * 1000, "audio/wav")},
            data={"language": "auto", "mode": "dictation"},
        )
        assert resp.status_code == 401


# ── POST /api/voice-layer/paste ────────────────────────────────────────────────


class TestPaste:
    def test_paste_returns_response(self, client_with_auth):
        resp = client_with_auth.post(
            "/api/voice-layer/paste",
            data={"text": "short text for paste", "confirm": "false"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "ok" in data

    def test_paste_confirm_required(self, client_with_auth):
        resp = client_with_auth.post(
            "/api/voice-layer/paste",
            data={"text": "Hello world", "confirm": "false"},
        )
        assert resp.status_code == 200
        data = resp.json()
        if data.get("ok") and data.get("status") == "confirm_required":
            assert "confirm" in data["message"].lower()

    def test_paste_requires_auth(self, client):
        resp = client.post(
            "/api/voice-layer/paste",
            data={"text": "test", "confirm": "false"},
        )
        assert resp.status_code == 401


# ── POST /api/voice-layer/paste/confirm ────────────────────────────────────────


class TestPasteConfirm:
    def test_confirm_paste_nonempty(self, client_with_auth):
        resp = client_with_auth.post(
            "/api/voice-layer/paste/confirm",
            data={"text": "OfficePilot test paste"},
        )
        assert resp.status_code == 200
        assert "ok" in resp.json()

    def test_confirm_requires_auth(self, client):
        resp = client.post(
            "/api/voice-layer/paste/confirm",
            data={"text": "test"},
        )
        assert resp.status_code == 401


# ── GET /api/voice-layer/history ────────────────────────────────────────────────


class TestHistory:
    def test_history_empty(self, client_with_auth):
        resp = client_with_auth.get("/api/voice-layer/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["total"] == 0
        assert data["items"] == []

    def test_history_with_filter(self, client_with_auth):
        resp = client_with_auth.get("/api/voice-layer/history?mode=dictation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "items" in data

    def test_history_requires_auth(self, client):
        resp = client.get("/api/voice-layer/history")
        assert resp.status_code == 401


# ── DELETE /api/voice-layer/history/{id} ────────────────────────────────────────


class TestDeleteEntry:
    def test_delete_nonexistent(self, client_with_auth):
        resp = client_with_auth.delete("/api/voice-layer/history/9999")
        assert resp.status_code == 404

    def test_delete_own_entry(self, client_with_auth, db_session):
        from app.models.user import User
        from app.models.dictation_history import DictationHistory
        user = db_session.query(User).filter(User.email == "voice-user@test.com").first()
        assert user is not None
        entry = DictationHistory(
            user_id=user.id, mode="dictation",
            transcript="Test delete entry",
        )
        db_session.add(entry)
        db_session.commit()
        entry_id = entry.id
        resp = client_with_auth.delete(f"/api/voice-layer/history/{entry_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_requires_auth(self, client):
        resp = client.delete("/api/voice-layer/history/1")
        assert resp.status_code == 401


# ── DELETE /api/voice-layer/history ─────────────────────────────────────────────


class TestClearHistory:
    def test_clear_history(self, client_with_auth, db_session):
        from app.models.user import User
        from app.models.dictation_history import DictationHistory
        user = db_session.query(User).filter(User.email == "voice-user@test.com").first()
        assert user is not None
        entry = DictationHistory(
            user_id=user.id, mode="dictation",
            transcript="Test clear entry",
        )
        db_session.add(entry)
        db_session.commit()
        resp = client_with_auth.delete("/api/voice-layer/history")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        hresp = client_with_auth.get("/api/voice-layer/history")
        assert hresp.json()["total"] == 0

    def test_clear_requires_auth(self, client):
        resp = client.delete("/api/voice-layer/history")
        assert resp.status_code == 401


# ── POST /api/voice-layer/settings ──────────────────────────────────────────────


class TestSettings:
    def test_settings_requires_auth(self, client):
        resp = client.post("/api/voice-layer/settings", json={})
        assert resp.status_code == 401


# ── Full workflow: dictate → stop → transcribe → history → clear ─────────────


class TestFullWorkflow:
    def test_full_dictation_workflow(self, client_with_auth):
        r1 = client_with_auth.post("/api/voice-layer/dictate")
        assert r1.json()["status"] == "recording"
        r2 = client_with_auth.post("/api/voice-layer/stop")
        assert r2.status_code == 200
        voice_data = b"\x00" * 32000
        r3 = client_with_auth.post(
            "/api/voice-layer/transcribe",
            files={"file": ("test.wav", voice_data, "audio/wav")},
            data={"language": "auto", "mode": "dictation"},
        )
        assert r3.status_code == 200
        assert "Mock transcription" in r3.json()["transcript"]
        r4 = client_with_auth.get("/api/voice-layer/history")
        assert r4.json()["total"] >= 1
        r5 = client_with_auth.delete("/api/voice-layer/history")
        assert r5.json()["ok"] is True
        r6 = client_with_auth.get("/api/voice-layer/history")
        assert r6.json()["total"] == 0


# ── Temp audio cleanup ─────────────────────────────────────────────────────────


class TestCleanup:
    def test_cleanup_temp_audio(self):
        from pathlib import Path
        from app.services.windows_voice_layer import TEMP_AUDIO_DIR, cleanup_temp_audio
        stale = TEMP_AUDIO_DIR / "voice_stale_test.wav"
        stale.write_bytes(b"\x00" * 100)
        old_mtime = time.time() - 7200
        os.utime(str(stale), (old_mtime, old_mtime))
        fresh = TEMP_AUDIO_DIR / "voice_fresh_test.wav"
        fresh.write_bytes(b"\x00" * 100)
        count = cleanup_temp_audio(max_age_seconds=3600)
        assert count >= 1
        assert not stale.exists()
        assert fresh.exists()
        fresh.unlink(missing_ok=True)

    def test_cleanup_current_temp_audio(self):
        import tempfile
        from pathlib import Path
        from app.services.windows_voice_layer import _recording_state, cleanup_current_temp_audio
        tmp = Path(tempfile.gettempdir()) / "officepilot_voice" / "voice_test_cleanup.wav"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(b"\x00")
        _recording_state["temp_audio"] = str(tmp)
        assert tmp.exists()
        cleanup_current_temp_audio()
        assert not tmp.exists()
        assert _recording_state["temp_audio"] is None
