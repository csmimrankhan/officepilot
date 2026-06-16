"""
Windows voice layer service for the Accountant AutoPilot.

Provides:
- Microphone recording (via frontend MediaRecorder or Python sounddevice)
- whisper.cpp transcription via subprocess
- AI Mode text polishing via LLM
- Dictation history management
- Recording lifecycle (start/stop/cleanup)
- whisper.cpp auto-detection from bundled paths
- First-run model download
"""

import json
import logging
import os
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("officepilot.voice_layer")

TEMP_AUDIO_DIR = Path(tempfile.gettempdir()) / "officepilot_voice"
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

AI_MODE_SYSTEM_PROMPT = (
    "You are an office writing assistant. Convert the user's spoken instruction "
    "into a polished response. Do not invent facts. Keep it concise. "
    "Output ONLY the polished text, no explanations, no markdown."
)

# ── Bundle path detection ──────────────────────────────────────────────

WHISPER_BUNDLE_DIRS = [
    # Relative to the sidecar binary or the Tauri resources
    Path(sys.executable).parent / "binaries" if getattr(sys, 'frozen', False) else None,
    # Tauri dev / resource layout
    Path(__file__).resolve().parents[3] / "desktop" / "tauri" / "src-tauri" / "binaries",
    # Fallback: next to the sidecar binary
    Path(sys.argv[0]).parent if sys.argv[0] else None,
    # Project root layout
    Path(__file__).resolve().parents[2] / "binaries",
]

MODEL_DIR_NAMES = ["models", "Models", "whisper-models"]

DEFAULT_MODEL_NAME = "ggml-small.bin"
FALLBACK_MODEL_NAME = "ggml-base.en.bin"
MODEL_HF_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{model_name}"
MODEL_SIZES = {
    "ggml-tiny.en.bin": "~75 MB",
    "ggml-base.en.bin": "~150 MB",
    "ggml-small.bin": "~500 MB (multilingual)",
    "ggml-small.en.bin": "~500 MB",
}


def _find_whisper_cli() -> Optional[str]:
    """Auto-detect whisper-cli.exe in bundled locations."""
    candidates = []
    for d in WHISPER_BUNDLE_DIRS:
        if d and d.exists():
            candidates.append(d / "whisper-cli.exe")
            candidates.append(d / "whisper-cli")

    # Also check PATH
    if sys.platform == "win32":
        for p in os.environ.get("PATH", "").split(";"):
            path = Path(p) / "whisper-cli.exe"
            if path.exists():
                candidates.append(path)

    for c in candidates:
        if c.exists():
            logger.info("whisper-cli auto-detected: %s", c)
            return str(c.resolve())

    logger.info("whisper-cli not found in bundled locations or PATH")
    return None


def _find_whisper_model(model_name: str | None = None) -> Optional[str]:
    """Auto-detect whisper model file in bundled locations.

    Tries model_name first, then DEFAULT_MODEL_NAME (ggml-small.bin),
    then FALLBACK_MODEL_NAME (ggml-base.en.bin).

    WHISPER_MODEL_PATH env var overrides all auto-detection.
    VOICE_WHISPER_MODEL_PATH is also respected (legacy).
    """
    # Check env override first
    env_path = os.environ.get("WHISPER_MODEL_PATH", "") or os.environ.get("VOICE_WHISPER_MODEL_PATH", "")
    if env_path:
        p = Path(env_path)
        if p.exists():
            logger.info("whisper model from WHISPER_MODEL_PATH: %s", p)
            return str(p.resolve())
        logger.warning("WHISPER_MODEL_PATH set but not found: %s", env_path)

    names_to_try = [
        model_name,
        DEFAULT_MODEL_NAME,       # ggml-small.bin
        FALLBACK_MODEL_NAME,      # ggml-base.en.bin
    ]
    names_to_try = [n for n in names_to_try if n]

    for name in names_to_try:
        candidates = []

        # Check alongside whisper-cli
        cli = _find_whisper_cli()
        if cli:
            cli_dir = Path(cli).parent
            for model_dir_name in MODEL_DIR_NAMES:
                candidates.append(cli_dir / model_dir_name / name)
            candidates.append(cli_dir / name)

        # Check all bundle dirs with model subdirs
        for d in WHISPER_BUNDLE_DIRS:
            if d and d.exists():
                for model_dir_name in MODEL_DIR_NAMES:
                    candidates.append(d / model_dir_name / name)
                candidates.append(d / name)

        # Check project root data dir
        project_root = Path(__file__).resolve().parents[2]
        candidates.append(project_root / "data" / "whisper" / name)

        for c in candidates:
            if c.exists():
                logger.info("whisper model auto-detected: %s", c)
                return str(c.resolve())

        logger.info("whisper model '%s' not found in bundled locations", name)

    logger.info("no whisper model found (tried %s)", ", ".join(names_to_try))
    return None


def detect_whisper_status() -> dict:
    """Detect whisper-cli and model paths, return status dict."""
    cli_path = _find_whisper_cli()
    model_path = _find_whisper_model()

    actual_model_name = Path(model_path).name if model_path else DEFAULT_MODEL_NAME
    status = {
        "whisper_cli_found": cli_path is not None,
        "whisper_cli_path": cli_path or "",
        "whisper_model_found": model_path is not None,
        "whisper_model_path": model_path or "",
        "whisper_configured": cli_path is not None and model_path is not None,
        "default_model_name": DEFAULT_MODEL_NAME,
        "fallback_model_name": FALLBACK_MODEL_NAME,
        "model_size": MODEL_SIZES.get(actual_model_name, "unknown"),
        "auto_detected": cli_path is not None or model_path is not None,
    }

    if cli_path and model_path:
        status["message"] = "Local Whisper Ready"
    elif cli_path and not model_path:
        status["message"] = f"whisper-cli found at {cli_path} but model not found. Download {DEFAULT_MODEL_NAME} (multilingual) or set WHISPER_MODEL_PATH."
    elif not cli_path and model_path:
        status["message"] = f"Model found at {model_path} but whisper-cli not found."
    else:
        status["message"] = "Whisper not configured. Download whisper-cli.exe and a model file."

    return status


def download_model(model_name: str = DEFAULT_MODEL_NAME, target_dir: Optional[str] = None) -> dict:
    """Download a whisper.cpp model from HuggingFace."""
    if target_dir:
        dest = Path(target_dir)
    else:
        # Default: project data/whisper/
        project_root = Path(__file__).resolve().parents[2]
        dest = project_root / "data" / "whisper"

    dest.mkdir(parents=True, exist_ok=True)
    target_path = dest / model_name

    if target_path.exists():
        return {
            "ok": True,
            "message": f"Model already exists at {target_path}",
            "path": str(target_path),
            "size_bytes": target_path.stat().st_size,
        }

    url = MODEL_HF_URL.format(model_name=model_name)
    logger.info("Downloading model %s from %s", model_name, url)

    try:
        urllib.request.urlretrieve(url, str(target_path))
        size = target_path.stat().st_size
        logger.info("Model downloaded: %s (%d bytes)", target_path, size)
        return {
            "ok": True,
            "message": f"Model downloaded to {target_path}",
            "path": str(target_path),
            "size_bytes": size,
        }
    except Exception as exc:
        logger.error("Model download failed: %s", exc)
        return {
            "ok": False,
            "error": f"Failed to download model: {exc}",
        }


# ── Recording ─────────────────────────────────────────────────────────────────

_recording_state = {"active": False, "started_at": None, "mode": None, "temp_audio": None}


def start_recording(mode: str = "dictation") -> dict:
    """Start a voice recording session."""
    if _recording_state["active"]:
        return {"ok": False, "error": "Already recording."}
    _recording_state["active"] = True
    _recording_state["started_at"] = datetime.utcnow().isoformat()
    _recording_state["mode"] = mode
    _recording_state["temp_audio"] = None
    logger.info("Voice recording started (mode=%s)", mode)
    return {"ok": True, "status": "recording", "mode": mode}


def stop_recording() -> dict:
    """Stop recording and return the temp audio path."""
    if not _recording_state["active"]:
        return {"ok": False, "error": "No active recording."}
    _recording_state["active"] = False
    audio_path = _recording_state.get("temp_audio")
    _recording_state["started_at"] = None
    _recording_state["mode"] = None
    logger.info("Voice recording stopped")
    return {"ok": True, "status": "stopped", "audio_path": audio_path}


def save_temp_wav(audio_data: bytes, sample_rate: int = 16000) -> str:
    """Save raw audio bytes as a temporary WAV file for whisper.cpp."""
    timestamp = int(time.time())
    filename = f"voice_{timestamp}.wav"
    filepath = str(TEMP_AUDIO_DIR / filename)
    try:
        import wave
        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)
        _recording_state["temp_audio"] = filepath
        logger.debug("Temp audio saved: %s (%d bytes)", filepath, len(audio_data))
        return filepath
    except Exception as exc:
        logger.error("Failed to save temp audio: %s", exc)
        raise


# ── Transcription ──────────────────────────────────────────────────────────────


def _build_whisper_cpp_command(
    audio_path: str,
    model_path: str,
    cli_path: str,
    language: str = "auto",
) -> list[str]:
    """Build the whisper-cli.exe command line arguments."""
    cmd = [cli_path, "-f", audio_path, "-m", model_path, "--no-timestamps"]
    if language and language != "auto":
        cmd.extend(["-l", language])
    return cmd


def transcribe_with_whisper_cpp(
    audio_path: str,
    model_path: str | None = None,
    cli_path: str | None = None,
    language: str = "auto",
) -> dict:
    """
    Transcribe audio using whisper-cli.exe subprocess.
    
    Falls back to mock transcription if whisper.cpp is not configured.
    """
    settings = _get_voice_settings()

    cli = cli_path or settings.get("voice_whisper_cli_path") or ""
    model = model_path or settings.get("voice_whisper_model_path") or ""

    if cli and model:
        cmd = _build_whisper_cpp_command(audio_path, model, cli, language)
        logger.info("Running whisper.cpp: %s", " ".join(cmd))
        start_ts = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            elapsed = time.time() - start_ts
            model_size_mb = Path(model).stat().st_size / (1024 * 1024) if Path(model).exists() else 0
            logger.info("whisper.cpp transcription took %.2fs (model: %.0fMB, audio: %s)", elapsed, model_size_mb, audio_path)
            if proc.returncode == 0 and proc.stdout.strip():
                transcript = proc.stdout.strip()
                return {"ok": True, "transcript": transcript, "engine": "whisper_cpp", "duration_s": round(elapsed, 2)}
            else:
                logger.warning("whisper.cpp stderr: %s", proc.stderr[:500])
                transcript = proc.stderr.strip() or proc.stdout.strip() or ""
                if transcript:
                    return {"ok": True, "transcript": transcript, "engine": "whisper_cpp_fallback", "duration_s": round(elapsed, 2)}
        except FileNotFoundError:
            elapsed = time.time() - start_ts
            logger.warning("whisper-cli.exe not found at: %s (%.2fs)", cli, elapsed)
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_ts
            logger.error("whisper.cpp timed out after 120s (took %.2fs before timeout)", elapsed)
        except Exception as exc:
            elapsed = time.time() - start_ts
            logger.error("whisper.cpp error after %.2fs: %s", elapsed, exc)

    logger.info("Whisper.cpp not available, using mock transcription")
    return transcribe_mock(audio_path)


def transcribe_mock(audio_path: str) -> dict:
    """Mock transcription for testing when whisper.cpp is not configured."""
    filename = Path(audio_path).stem
    timestamp = filename.replace("voice_", "")
    return {
        "ok": True,
        "transcript": f"Mock transcription of recording at {timestamp}.",
        "engine": "mock",
        "duration_s": 0.01,
        "note": "whisper.cpp not configured. Set VOICE_WHISPER_CLI_PATH and VOICE_WHISPER_MODEL_PATH.",
    }


# ── AI Mode ────────────────────────────────────────────────────────────────────


def run_ai_mode(transcript: str, settings_override: dict | None = None) -> dict:
    """Send transcript to AI mode LLM for polish/conversion."""
    settings = settings_override or _get_voice_settings()

    provider = settings.get("ai_mode_provider", "openai_compatible")
    allow_cloud = settings.get("ai_mode_allow_cloud", False)
    api_key = settings.get("ai_mode_api_key", "")
    model = settings.get("ai_mode_model", "gpt-4o-mini")

    if not allow_cloud:
        return {
            "ok": False,
            "error": "AI Mode requires cloud LLM access. Enable AI_MODE_ALLOW_CLOUD=true or set AI_MODE_API_KEY.",
            "transcript": transcript,
            "blocked": True,
        }

    if not api_key:
        return {
            "ok": False,
            "error": "AI Mode API key not configured. Set AI_MODE_API_KEY.",
            "transcript": transcript,
            "blocked": True,
        }

    try:
        api_base = settings.get("ai_mode_api_base_url", "https://api.openai.com/v1")
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": AI_MODE_SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
            "temperature": 0.3,
            "max_tokens": 500,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{api_base.rstrip('/')}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            polished = data["choices"][0]["message"]["content"].strip()

        return {
            "ok": True,
            "transcript": transcript,
            "output": polished,
            "engine": provider,
        }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        logger.error("AI Mode HTTP %s: %s", e.code, error_body)
        return {"ok": False, "error": f"AI Mode API error: {e.code}", "transcript": transcript}
    except Exception as exc:
        logger.error("AI Mode error: %s", exc)
        return {"ok": False, "error": str(exc), "transcript": transcript}


# ── Dictation History ─────────────────────────────────────────────────────────


def save_dictation_history(
    db: Session,
    user_id: int,
    mode: str,
    transcript: str,
    ai_output: str | None = None,
    language: str = "auto",
    pasted: bool = False,
    target_app: str | None = None,
) -> dict:
    """Save a dictation entry to the history table."""
    from ..models.dictation_history import DictationHistory

    record = DictationHistory(
        user_id=user_id,
        mode=mode,
        transcript=transcript,
        ai_output=ai_output,
        language=language,
        pasted=pasted,
        target_app=target_app,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "ok": True,
        "id": record.id,
        "created_at": record.created_at.isoformat(),
    }


def get_dictation_history(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    mode: str | None = None,
) -> dict:
    """Get dictation history for a user."""
    from ..models.dictation_history import DictationHistory

    query = db.query(DictationHistory).filter(DictationHistory.user_id == user_id)
    if mode:
        query = query.filter(DictationHistory.mode == mode)
    total = query.count()
    items = (
        query
        .order_by(DictationHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "ok": True,
        "total": total,
        "items": [
            {
                "id": item.id,
                "mode": item.mode,
                "transcript": item.transcript[:500],
                "ai_output": item.ai_output[:500] if item.ai_output else None,
                "language": item.language,
                "pasted": item.pasted,
                "target_app": item.target_app,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
    }


def delete_dictation_entry(db: Session, entry_id: int, user_id: int) -> dict:
    """Delete a single dictation history entry."""
    from ..models.dictation_history import DictationHistory

    entry = db.query(DictationHistory).filter(
        DictationHistory.id == entry_id,
        DictationHistory.user_id == user_id,
    ).first()
    if not entry:
        return {"ok": False, "error": "Entry not found"}
    db.delete(entry)
    db.commit()
    return {"ok": True, "message": "Entry deleted"}


def clear_dictation_history(db: Session, user_id: int) -> dict:
    """Clear all dictation history for a user."""
    from ..models.dictation_history import DictationHistory

    db.query(DictationHistory).filter(DictationHistory.user_id == user_id).delete()
    db.commit()
    return {"ok": True, "message": "History cleared"}


# ── Helpers ────────────────────────────────────────────────────────────────────


_voice_settings_cache = None
_voice_settings_cached_at = 0


def _get_voice_settings() -> dict:
    """Get current voice layer settings (cached 30s).

    Merges env config with auto-detected bundled paths.
    Env-provided paths take precedence over auto-detected ones.
    """
    global _voice_settings_cache, _voice_settings_cached_at
    now = time.time()
    if _voice_settings_cache and (now - _voice_settings_cached_at) < 30:
        return _voice_settings_cache

    from ..config import get_settings
    s = get_settings()

    # Use env config if set, otherwise auto-detect
    cli_path = s.voice_whisper_cli_path or _find_whisper_cli() or ""
    # WHISPER_MODEL_PATH takes priority over VOICE_WHISPER_MODEL_PATH (legacy)
    whisper_model_env = os.environ.get("WHISPER_MODEL_PATH", "") or s.voice_whisper_model_path
    model_path = whisper_model_env or _find_whisper_model() or ""

    _voice_settings_cache = {
        "voice_layer_enabled": s.voice_layer_enabled,
        "voice_mode_default": s.voice_mode_default,
        "voice_local_engine": s.voice_local_engine,
        "voice_whisper_cli_path": cli_path,
        "voice_whisper_model_path": model_path,
        "voice_language": s.voice_language,
        "voice_push_to_talk": s.voice_push_to_talk,
        "voice_shortcut_dictation": s.voice_shortcut_dictation,
        "voice_shortcut_ai": s.voice_shortcut_ai,
        "voice_shortcut_agent": s.voice_shortcut_agent,
        "voice_confirm_before_paste": s.voice_confirm_before_paste,
        "voice_save_history": s.voice_save_history,
        "voice_history_limit": s.voice_history_limit,
        "voice_beep_enabled": s.voice_beep_enabled,
        "voice_overlay_enabled": s.voice_overlay_enabled,
        "ai_mode_provider": s.ai_mode_provider,
        "ai_mode_model": s.ai_mode_model,
        "ai_mode_api_key": s.ai_mode_api_key,
        "ai_mode_allow_cloud": s.ai_mode_allow_cloud,
    }
    _voice_settings_cached_at = now
    return _voice_settings_cache


# ── Test Transcription (Phase 28) ──────────────────────────────────────


def transcribe_test_audio(audio_path: str) -> dict:
    """Transcribe a test audio file and return detailed results."""
    settings = _get_voice_settings()
    cli = settings.get("voice_whisper_cli_path", "")
    model = settings.get("voice_whisper_model_path", "")

    if not cli or not model:
        return {
            "ok": False,
            "error": "whisper.cpp not configured. Set whisper-cli and model paths.",
        }

    if not Path(cli).exists():
        return {"ok": False, "error": f"whisper-cli not found at: {cli}"}

    if not Path(model).exists():
        return {"ok": False, "error": f"Model not found at: {model}"}

    cmd = [cli, "-f", audio_path, "-m", model, "--no-timestamps"]
    try:
        start = time.time()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        elapsed = time.time() - start

        if proc.returncode == 0 and proc.stdout.strip():
            return {
                "ok": True,
                "transcript": proc.stdout.strip(),
                "duration_ms": int(elapsed * 1000),
                "engine": "whisper_cpp",
                "cli_path": cli,
                "model_path": model,
            }
        else:
            return {
                "ok": False,
                "error": f"whisper.cpp exited with code {proc.returncode}: {proc.stderr[:500]}",
                "stderr": proc.stderr[:500],
                "duration_ms": int(elapsed * 1000),
            }
    except FileNotFoundError:
        return {"ok": False, "error": f"whisper-cli not found: {cli}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "whisper.cpp timed out after 120s"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def generate_test_audio(duration_seconds: int = 2) -> str:
    """Generate a simple test WAV file (silence or sine tone) for testing.

    Creates a 440 Hz sine wave tone at 16kHz mono 16-bit PCM.
    """
    sample_rate = 16000
    num_samples = sample_rate * duration_seconds

    filepath = str(TEMP_AUDIO_DIR / f"test_tone_{int(time.time())}.wav")
    try:
        import wave
        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            # Generate a 440 Hz sine wave (audible test tone)
            data = b""
            for i in range(num_samples):
                sample = int(16384 * (i / num_samples))  # gentle sweep
                data += struct.pack("<h", sample)
            wf.writeframes(data)
        logger.info("Generated test audio: %s (%d samples)", filepath, num_samples)
        return filepath
    except Exception as exc:
        logger.error("Failed to generate test audio: %s", exc)
        raise


def cleanup_temp_audio(max_age_seconds: int = 3600) -> int:
    """Delete old temp audio files. Returns count deleted."""
    now = time.time()
    count = 0
    for f in TEMP_AUDIO_DIR.glob("voice_*.wav"):
        try:
            if now - f.stat().st_mtime > max_age_seconds:
                f.unlink()
                count += 1
        except Exception:
            pass
    return count


def cleanup_current_temp_audio() -> None:
    """Delete the current recording's temp audio file."""
    audio_path = _recording_state.get("temp_audio")
    if audio_path:
        try:
            Path(audio_path).unlink(missing_ok=True)
        except Exception:
            pass
        _recording_state["temp_audio"] = None
