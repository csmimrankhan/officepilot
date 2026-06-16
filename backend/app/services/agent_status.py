"""Phase 7 / Phase 8 — local agent status.

Reports runtime info about the FastAPI process that is currently
serving the API: when it started, the configured host/port, the
Phase number, the OCR engine, the Gmail config state, the parser
engine, and a small health snapshot. This is what the Tauri shell
embeds in its title bar / status pill, and what the
**Local Agent** page in the React UI shows.

The status is computed on every call; nothing is cached, so the
UI always sees up-to-date values.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path

from ..config import Settings

logger = logging.getLogger(__name__)


# The module's ``_STARTED_AT`` is set the first time the function
# is called; this is "when did this Python process boot" from the
# API's point of view.
_STARTED_AT: datetime | None = None
_PID: int | None = None
_PYTHON: str | None = None


def _ensure_init() -> None:
    global _STARTED_AT, _PID, _PYTHON
    if _STARTED_AT is None:
        _STARTED_AT = datetime.utcnow()
    if _PID is None:
        _PID = os.getpid()
    if _PYTHON is None:
        _PYTHON = sys.executable or "python"


def _uptime_seconds() -> float:
    _ensure_init()
    if _STARTED_AT is None:
        return 0.0
    return (datetime.utcnow() - _STARTED_AT).total_seconds()


def _uptime_human(seconds: float) -> str:
    s = int(seconds)
    days, s = divmod(s, 86400)
    hours, s = divmod(s, 3600)
    minutes, secs = divmod(s, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def _try_db_status(db) -> dict:
    """Best-effort DB health snapshot. Never raises."""
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error", "error": str(exc)}


def build_status(settings: Settings, app_version: str, phase: int, db=None) -> dict:
    _ensure_init()
    db_status = _try_db_status(db) if db is not None else {"status": "unknown"}
    uptime = _uptime_seconds()
    # Phase 8: detect whether the agent was launched as a bundled
    # PyInstaller sidecar (``frozen`` attribute is set by
    # PyInstaller / cx_Freeze / Nuitka) or as system Python. The
    # Tauri shell sets ``OFFICEPILOT_SIDECAR=1`` in the sidecar's
    # environment so the UI can also detect the bundled case even
    # when ``getattr(sys, 'frozen', None)`` is not set.
    is_frozen = bool(getattr(sys, "frozen", False))
    sidecar_env = os.environ.get("OFFICEPILOT_SIDECAR", "")
    is_sidecar = is_frozen or sidecar_env.lower() in ("1", "true", "yes", "on")
    sidecar_info = {
        "bundled": is_sidecar,
        "frozen": is_frozen,
        "mode": "bundled" if is_sidecar else "system-python",
    }
    return {
        "app": "officepilot-ai",
        "version": app_version,
        "phase": phase,
        # Phase 8: lifecycle state. In the dev/web case the API is
        # responding, so by definition we are "online". The bundled
        # Tauri supervisor owns the canonical state (starting /
        # failed / offline) and overrides this via a Tauri-side
        # event that the React UI subscribes to. The string here is
        # the *fallback* state the UI uses when no supervisor is
        # present.
        "state": "online",
        "started_at": _STARTED_AT.isoformat() if _STARTED_AT else None,
        "uptime_seconds": int(uptime),
        "uptime_human": _uptime_human(uptime),
        "host": settings.agent_host,
        "port": settings.agent_port,
        "url": f"http://{settings.agent_host}:{settings.agent_port}",
        "pid": _PID,
        "python": _PYTHON,
        "platform": platform.platform(),
        "env": settings.app_env,
        "parser_engine": settings.parser_engine,
        "ocr_enabled": settings.ocr_enabled,
        "gmail_configured": settings.gmail_configured,
        "gmail_allow_real": settings.gmail_allow_real,
        "data_dir": str(settings.data_dir),
        "storage_root": str(settings.storage_root),
        "logs_dir": str(settings.logs_dir),
        "sidecar": sidecar_info,
        "database": db_status,
    }


def build_settings_view(settings: Settings) -> dict:
    """Settings that the user is allowed to view / tweak from the
    Privacy Dashboard. The values that can be changed via PATCH are
    listed in :func:`apply_settings_patch`."""
    return {
        "data_dir": str(settings.data_dir),
        "storage_root": str(settings.storage_root),
        "agent_host": settings.agent_host,
        "agent_port": settings.agent_port,
        "ocr_enabled": settings.ocr_enabled,
        "gmail_allow_real": settings.gmail_allow_real,
        "max_upload_mb": settings.max_upload_mb,
        "parser_engine": settings.parser_engine,
        "app_env": settings.app_env,
    }


# Settings that may be overridden at runtime via PATCH. Changing
# them is a *view-time* operation; the next process restart reverts
# to whatever the environment variable says.
MUTABLE_SETTINGS = {
    "agent_host",
    "agent_port",
    "ocr_enabled",
    "gmail_allow_real",
    "max_upload_mb",
}


def apply_settings_patch(settings: Settings, patch: dict) -> dict:
    """Apply a PATCH to the in-memory settings.

    Only keys in :data:`MUTABLE_SETTINGS` are honoured. We do *not*
    persist the change to disk — restarting the agent reverts to
    the env var defaults, which is the safe behaviour for an
    audit-friendly local tool.
    """
    if not isinstance(patch, dict):
        raise ValueError("patch must be a JSON object")
    applied: dict = {}
    rejected: dict = {}
    for key, value in patch.items():
        if key not in MUTABLE_SETTINGS:
            rejected[key] = "not mutable"
            continue
        try:
            if key in ("ocr_enabled", "gmail_allow_real"):
                applied[key] = bool(value)
            elif key in ("agent_port", "max_upload_mb"):
                applied[key] = int(value)
            else:
                applied[key] = str(value)
        except (TypeError, ValueError) as exc:
            rejected[key] = f"invalid value: {exc}"

    if applied:
        # The Settings dataclass is frozen; we can't mutate it.
        # We do the conservative thing: write the new value back
        # to ``os.environ`` so any future ``get_settings()`` call
        # inside this process sees it.
        for k, v in applied.items():
            os.environ[f"OFFICEPILOT_{k.upper()}"] = str(v)
    return {"applied": applied, "rejected": rejected}
