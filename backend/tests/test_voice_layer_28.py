"""
Phase 28 — Real Voice EXE Hardening tests.

Covers:
- whisper-cli path detection
- model path detection
- missing model warning
- transcribe mock fallback
- temp audio cleanup
- AI mode blocked if cloud disabled
- paste blocked in password/OTP window
- test transcription endpoint
- model download endpoint
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.services import windows_voice_layer as voice_svc
from app.services import windows_paste as paste_svc

client = TestClient(app)


# ── Whisper path detection ─────────────────────────────────────────────


def test_find_whisper_cli_not_found():
    """When whisper-cli is not in any bundled location, return None."""
    with patch.object(voice_svc, "WHISPER_BUNDLE_DIRS", [Path("/nonexistent")]):
        result = voice_svc._find_whisper_cli()
        assert result is None


def test_find_whisper_cli_found():
    """When whisper-cli exists in a bundle dir, return its path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cli_path = tmp / "whisper-cli.exe"
        cli_path.write_text("fake binary")
        with patch.object(voice_svc, "WHISPER_BUNDLE_DIRS", [tmp]):
            result = voice_svc._find_whisper_cli()
            assert result == str(cli_path.resolve())


# ── Model path detection ────────────────────────────────────────────────


def test_find_whisper_model_not_found():
    """When model is not in any bundled location, return None."""
    with patch.object(voice_svc, "WHISPER_BUNDLE_DIRS", [Path("/nonexistent")]):
        result = voice_svc._find_whisper_model()
        assert result is None


def test_find_whisper_model_found():
    """When model exists in a bundle models dir, return its path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        model_dir = tmp / "models"
        model_dir.mkdir()
        model_path = model_dir / "ggml-base.en.bin"
        model_path.write_text("fake model")
        with patch.object(voice_svc, "WHISPER_BUNDLE_DIRS", [tmp]):
            result = voice_svc._find_whisper_model()
            assert result == str(model_path.resolve())


# ── Missing model warning ────────────────────────────────────────────────


def test_detect_whisper_status_both_missing():
    """When both cli and model are missing, status reflects it."""
    with patch.object(voice_svc, "_find_whisper_cli", return_value=None):
        with patch.object(voice_svc, "_find_whisper_model", return_value=None):
            status = voice_svc.detect_whisper_status()
            assert status["whisper_configured"] is False
            assert status["whisper_cli_found"] is False
            assert status["whisper_model_found"] is False


def test_detect_whisper_status_cli_only():
    """When only cli is found, status shows model missing."""
    with patch.object(voice_svc, "_find_whisper_cli", return_value="C:\\whisper-cli.exe"):
        with patch.object(voice_svc, "_find_whisper_model", return_value=None):
            status = voice_svc.detect_whisper_status()
            assert status["whisper_configured"] is False
            assert status["whisper_cli_found"] is True
            assert status["whisper_model_found"] is False


def test_detect_whisper_status_both_found():
    """When both cli and model are found, status says ready."""
    with patch.object(voice_svc, "_find_whisper_cli", return_value="C:\\whisper-cli.exe"):
        with patch.object(voice_svc, "_find_whisper_model", return_value="C:\\ggml-base.en.bin"):
            status = voice_svc.detect_whisper_status()
            assert status["whisper_configured"] is True
            assert status["whisper_cli_found"] is True
            assert status["whisper_model_found"] is True


# ── Transcribe mock fallback ─────────────────────────────────────────────


def test_transcribe_mock_returns_expected():
    """Mock transcription returns expected fields."""
    result = voice_svc.transcribe_mock("/tmp/test.wav")
    assert result["ok"] is True
    assert "transcript" in result
    assert result["engine"] == "mock"


def test_transcribe_with_whisper_cpp_fallback():
    """When whisper is not configured, falls back to mock."""
    with patch.object(voice_svc, "_get_voice_settings", return_value={
        "voice_whisper_cli_path": "",
        "voice_whisper_model_path": "",
    }):
        result = voice_svc.transcribe_with_whisper_cpp("/tmp/test.wav")
        assert result["engine"] == "mock"
        assert result["ok"] is True


# ── Temp audio cleanup ───────────────────────────────────────────────────


def test_cleanup_temp_audio():
    """Temp audio cleanup removes old files and returns count."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import time
        tmp_path = Path(tmpdir)

        # Create an old file
        old_file = tmp_path / "voice_old.wav"
        old_file.write_text("data")
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(str(old_file), (old_time, old_time))

        # Create a recent file
        new_file = tmp_path / "voice_new.wav"
        new_file.write_text("data")

        with patch.object(voice_svc, "TEMP_AUDIO_DIR", tmp_path):
            count = voice_svc.cleanup_temp_audio(max_age_seconds=3600)
            assert count >= 1
            assert not old_file.exists()
            assert new_file.exists()


def test_cleanup_current_temp_audio():
    """Cleaning up current temp audio sets state to None."""
    voice_svc._recording_state["temp_audio"] = "/tmp/test_voice.wav"
    with patch("pathlib.Path.unlink"):
        voice_svc.cleanup_current_temp_audio()
        assert voice_svc._recording_state["temp_audio"] is None


# ── AI mode blocked if cloud disabled ─────────────────────────────────────


def test_ai_mode_cloud_disabled():
    """When AI_MODE_ALLOW_CLOUD is false, AI mode returns blocked."""
    result = voice_svc.run_ai_mode("test transcript", settings_override={
        "ai_mode_allow_cloud": False,
        "ai_mode_api_key": "",
    })
    assert result.get("blocked") is True
    assert result.get("ok") is False


def test_ai_mode_api_key_missing():
    """When AI mode API key is missing, it reports blocked."""
    result = voice_svc.run_ai_mode("test transcript", settings_override={
        "ai_mode_allow_cloud": True,
        "ai_mode_api_key": "",
    })
    assert result.get("blocked") is True
    assert "API key" in result.get("error", "")


# ── Paste blocked in password/OTP window ──────────────────────────────────


def test_detect_sensitive_window_password():
    """Window title containing 'password' should be detected as sensitive."""
    assert paste_svc.SENSITIVE_WINDOW_KEYWORDS is not None
    assert 'password' in paste_svc.SENSITIVE_WINDOW_KEYWORDS


def test_detect_sensitive_window_safe():
    """Sensitive window list does not contain non-sensitive words."""
    assert 'password' in paste_svc.SENSITIVE_WINDOW_KEYWORDS
    assert 'excel' not in paste_svc.SENSITIVE_WINDOW_KEYWORDS
    assert 'notepad' not in paste_svc.SENSITIVE_WINDOW_KEYWORDS


def test_paste_blocked_in_sensitive_window():
    """paste_text_at_cursor returns blocked when sensitive window detected."""
    with patch.object(paste_svc, "_detect_sensitive_window", return_value=True):
        result = paste_svc.paste_text_at_cursor("test text", confirm_before_paste=False)
        assert result.get("blocked") is True
        assert "safety" in result.get("error", "").lower()


def test_paste_empty_text():
    """paste_text_at_cursor returns error for empty text."""
    result = paste_svc.paste_text_at_cursor("", confirm_before_paste=False)
    assert result.get("ok") is False
    assert "empty" in result.get("error", "").lower()


# ── Test transcription endpoint ───────────────────────────────────────────


def test_transcribe_test_audio_no_config():
    """When whisper is not configured, test transcription returns error."""
    with patch.object(voice_svc, "_get_voice_settings", return_value={
        "voice_whisper_cli_path": "",
        "voice_whisper_model_path": "",
    }):
        result = voice_svc.transcribe_test_audio("/tmp/test.wav")
        assert result.get("ok") is False
        assert "not configured" in result.get("error", "")


def test_transcribe_test_audio_cli_not_found():
    """When whisper-cli path doesn't exist, test transcription returns error."""
    with patch.object(voice_svc, "_get_voice_settings", return_value={
        "voice_whisper_cli_path": "C:\\nonexistent\\whisper-cli.exe",
        "voice_whisper_model_path": "C:\\model.bin",
    }):
        result = voice_svc.transcribe_test_audio("/tmp/test.wav")
        assert result.get("ok") is False
        assert "not found" in result.get("error", "")


# ── Model download ────────────────────────────────────────────────────────


def test_download_model_already_exists():
    """If model already exists, download returns early with success."""
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "ggml-small.bin"
        model_path.write_text("fake model data")
        result = voice_svc.download_model(target_dir=tmpdir)
        assert result.get("ok") is True
        assert "already exists" in result.get("message", "")


# ── Recording lifecycle ──────────────────────────────────────────────────


def test_start_recording():
    """start_recording sets active state."""
    voice_svc._recording_state["active"] = False
    result = voice_svc.start_recording(mode="dictation")
    assert result.get("ok") is True
    assert voice_svc._recording_state["active"] is True
    assert voice_svc._recording_state["mode"] == "dictation"


def test_start_recording_already_active():
    """start_recording returns error when already recording."""
    voice_svc._recording_state["active"] = True
    result = voice_svc.start_recording(mode="dictation")
    assert result.get("ok") is False
    assert "already" in result.get("error", "").lower()


def test_stop_recording():
    """stop_recording clears active state."""
    voice_svc._recording_state["active"] = True
    voice_svc._recording_state["mode"] = "dictation"
    voice_svc._recording_state["started_at"] = "2024-01-01T00:00:00"
    result = voice_svc.stop_recording()
    assert result.get("ok") is True
    assert voice_svc._recording_state["active"] is False
    assert voice_svc._recording_state["mode"] is None


def test_stop_recording_not_active():
    """stop_recording returns error when not recording."""
    voice_svc._recording_state["active"] = False
    result = voice_svc.stop_recording()
    assert result.get("ok") is False


# ── Endpoint-level tests ──────────────────────────────────────────────────


def test_voice_layer_status_endpoint():
    """GET /api/voice-layer/status returns expected fields."""
    response = client.get("/api/voice-layer/status")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "whisper_configured" in data
    assert "shortcuts" in data


def test_whisper_detect_endpoint():
    """GET /api/voice-layer/whisper-detect returns detection results."""
    response = client.get("/api/voice-layer/whisper-detect")
    assert response.status_code == 200
    data = response.json()
    assert "whisper_cli_found" in data
    assert "whisper_model_found" in data
    assert "whisper_configured" in data


def test_test_transcribe_no_auth():
    """POST /api/voice-layer/test-transcribe without auth returns 401."""
    response = client.post("/api/voice-layer/test-transcribe")
    assert response.status_code == 401


# ── Audio generation ──────────────────────────────────────────────────────


def test_generate_test_audio():
    """generate_test_audio creates a valid WAV file."""
    with patch.object(voice_svc, "TEMP_AUDIO_DIR", Path(tempfile.mkdtemp())):
        path = voice_svc.generate_test_audio(duration_seconds=1)
        assert Path(path).exists()
        assert Path(path).stat().st_size > 44  # WAV header size
        Path(path).unlink(missing_ok=True)
