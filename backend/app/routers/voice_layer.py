"""
Phase 27 — Windows Voice Layer Router.

Endpoints for dictation, AI mode, agent command mode, transcription,
paste, and dictation history management.

Phase 28 — adds auto-detect whisper status, model download, test transcription.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..config import get_settings, Settings
from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services import windows_voice_layer as voice_svc
from ..services import windows_paste as paste_svc

logger = logging.getLogger("officepilot.voice_layer")

router = APIRouter(prefix="/api/voice-layer", tags=["voice-layer"])


@router.get("/status")
def get_status(
    settings: Settings = Depends(get_settings),
):
    """Get voice layer configuration and status.

    Phase 28: includes auto-detected whisper paths and detailed status.
    """
    whisper_status = voice_svc.detect_whisper_status()

    # Env paths take precedence over auto-detected
    cli_path = settings.voice_whisper_cli_path or whisper_status["whisper_cli_path"]
    model_path = settings.voice_whisper_model_path or whisper_status["whisper_model_path"]
    whisper_configured = bool(cli_path and model_path)

    return {
        "ok": True,
        "enabled": settings.voice_layer_enabled,
        "mode_default": settings.voice_mode_default,
        "whisper_configured": whisper_configured,
        "whisper_cli_path": cli_path,
        "whisper_model_path": model_path,
        "whisper_cli_found": whisper_status["whisper_cli_found"],
        "whisper_model_found": whisper_status["whisper_model_found"],
        "whisper_message": whisper_status["message"],
        "default_model_name": whisper_status["default_model_name"],
        "language": settings.voice_language,
        "push_to_talk": settings.voice_push_to_talk,
        "shortcuts": {
            "dictation": settings.voice_shortcut_dictation,
            "ai_mode": settings.voice_shortcut_ai,
            "agent": settings.voice_shortcut_agent,
        },
        "confirm_before_paste": settings.voice_confirm_before_paste,
        "save_history": settings.voice_save_history,
        "history_limit": settings.voice_history_limit,
        "beep_enabled": settings.voice_beep_enabled,
        "overlay_enabled": settings.voice_overlay_enabled,
        "ai_mode": {
            "configured": bool(settings.ai_mode_api_key),
            "allow_cloud": settings.ai_mode_allow_cloud,
            "provider": settings.ai_mode_provider,
        },
        "recording": {
            "active": voice_svc._recording_state["active"],
            "mode": voice_svc._recording_state["mode"],
        },
    }


@router.post("/dictate")
def dictate_start(
    current_user: User = Depends(get_current_user),
):
    """Start dictation mode recording."""
    result = voice_svc.start_recording(mode="dictation")
    if not result["ok"]:
        raise HTTPException(400, result["error"])
    return result


@router.post("/ai-mode")
def ai_mode_start(
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Start AI Mode recording."""
    if not settings.ai_mode_allow_cloud:
        raise HTTPException(400, "AI Mode requires cloud LLM access. Set AI_MODE_ALLOW_CLOUD=true.")
    if not settings.ai_mode_api_key:
        raise HTTPException(400, "AI Mode API key not configured.")
    result = voice_svc.start_recording(mode="ai_mode")
    if not result["ok"]:
        raise HTTPException(400, result["error"])
    return result


@router.post("/agent-command")
def agent_command_start(
    current_user: User = Depends(get_current_user),
):
    """Start agent command mode recording (transcript goes to agent)."""
    result = voice_svc.start_recording(mode="agent_command")
    if not result["ok"]:
        raise HTTPException(400, result["error"])
    return result


@router.post("/stop")
def stop_recording(
    current_user: User = Depends(get_current_user),
):
    """Stop recording and return status."""
    result = voice_svc.stop_recording()
    return result


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    mode: str = Form("dictation"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Upload audio file, save as temp WAV, transcribe with whisper.cpp,
    optionally run AI Mode, and save to history.
    """
    if not settings.voice_layer_enabled:
        raise HTTPException(400, "Voice layer is disabled")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(400, "Empty audio file")

    audio_path = voice_svc.save_temp_wav(audio_bytes)

    transcribe_result = voice_svc.transcribe_with_whisper_cpp(
        audio_path,
        language=language,
    )

    if not transcribe_result.get("ok"):
        voice_svc.cleanup_current_temp_audio()
        raise HTTPException(500, transcribe_result.get("error", "Transcription failed"))

    transcript = transcribe_result["transcript"]

    ai_output = None
    if mode == "ai_mode":
        ai_result = voice_svc.run_ai_mode(transcript)
        if ai_result.get("ok"):
            ai_output = ai_result.get("output")

    if settings.voice_save_history:
        voice_svc.save_dictation_history(
            db,
            current_user.id,
            mode=mode,
            transcript=transcript,
            ai_output=ai_output,
            language=language,
        )

    if not settings.voice_save_history:
        voice_svc.cleanup_current_temp_audio()

    result = {
        "ok": True,
        "transcript": transcript,
        "ai_output": ai_output,
        "engine": transcribe_result.get("engine", "mock"),
        "mode": mode,
    }
    return result


@router.post("/paste")
def paste_text(
    text: str = Form(...),
    confirm: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Paste text at cursor with safety checks."""
    result = paste_svc.paste_text_at_cursor(
        text,
        confirm_before_paste=not confirm and settings.voice_confirm_before_paste,
    )
    return result


@router.post("/paste/confirm")
def confirm_paste(
    text: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm and execute paste after user approval."""
    result = paste_svc.paste_text_at_cursor(text, confirm_before_paste=False)
    if result.get("ok"):
        from ..models.dictation_history import DictationHistory
        entry = db.query(DictationHistory).filter(
            DictationHistory.transcript == text[:500],
            DictationHistory.user_id == current_user.id,
        ).order_by(DictationHistory.created_at.desc()).first()
        if entry:
            entry.pasted = True
            db.commit()
    return result


@router.get("/history")
def get_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    mode: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get dictation history for the current user."""
    return voice_svc.get_dictation_history(db, current_user.id, limit, offset, mode)


@router.delete("/history/{entry_id}")
def delete_history_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a single dictation history entry."""
    result = voice_svc.delete_dictation_entry(db, entry_id, current_user.id)
    if not result["ok"]:
        raise HTTPException(404, result["error"])
    return result


@router.delete("/history")
def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear all dictation history for the current user."""
    return voice_svc.clear_dictation_history(db, current_user.id)


@router.post("/settings")
def update_settings(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update voice layer settings in the DB settings store."""
    from ..services.settings import get_or_create, set_setting

    current = get_or_create(db, "voice_layer", {})
    current_val = current.value if hasattr(current, "value") else current
    if isinstance(current_val, str):
        import json
        current_val = json.loads(current_val)
    merged = {**(current_val or {}), **payload}
    result = set_setting(db, "voice_layer", merged)
    return {"ok": True, "settings": result}


@router.get("/settings")
def read_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Read voice layer settings from the DB settings store."""
    from ..services.settings import get_or_create

    current = get_or_create(db, "voice_layer", {})
    current_val = current.value if hasattr(current, "value") else current
    if isinstance(current_val, str):
        import json
        current_val = json.loads(current_val)
    return {"ok": True, "settings": current_val or {}}


# ── Phase 28: Whisper auto-detect & test transcription ─────────────────


@router.get("/whisper-detect")
def detect_whisper():
    """Auto-detect whisper-cli.exe and model file in bundled locations."""
    result = voice_svc.detect_whisper_status()
    return {"ok": True, **result}


@router.post("/whisper-download-model")
def download_whisper_model(
    model_name: str = Form(voice_svc.DEFAULT_MODEL_NAME),
    current_user: User = Depends(get_current_user),
):
    """Download a whisper.cpp model file from HuggingFace."""
    result = voice_svc.download_model(model_name=model_name)
    return result


@router.post("/test-transcribe")
def test_transcribe(
    current_user: User = Depends(get_current_user),
):
    """Generate a test tone and transcribe it to verify whisper.cpp setup."""
    # Generate test audio
    try:
        audio_path = voice_svc.generate_test_audio(duration_seconds=2)
    except Exception as exc:
        raise HTTPException(500, f"Failed to generate test audio: {exc}")

    # Transcribe it
    result = voice_svc.transcribe_test_audio(audio_path)

    # Cleanup test file
    try:
        Path(audio_path).unlink(missing_ok=True)
    except Exception:
        pass

    return result
