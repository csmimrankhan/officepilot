"""Phase 7 — local desktop shell API.

- ``GET    /api/health``            (also defined in :mod:`app.routers.health`)
- ``GET    /api/local/status``      — runtime status of this agent
- ``PATCH  /api/local/settings``    — mutate a small allow-list of settings
- ``GET    /api/local/storage``     — directory layout + size summary
- ``POST   /api/local/export-audit``— write the audit log to CSV
- ``POST   /api/local/export-logs`` — package logs + diagnostics into ZIP
- ``POST   /api/local/clear-cache`` — wipe the cache subdir only

The endpoints never expose anything outside the local machine
(no auth required because they only run when bound to
``127.0.0.1``); the CORS allow-list is the same as the rest of
the API.
"""

from __future__ import annotations

import logging
import os
import datetime
import platform
import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..models.audit_log import AuditLog
from ..services import agent_status, storage_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/local", tags=["local"])


# Phase / version constants must match main.py so the response is
# consistent regardless of which endpoint the UI calls.
APP_VERSION = "0.36.1"
APP_PHASE = 12


# --------------------------------------------------------------- schemas


class SettingsPatch(BaseModel):
    patch: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------- endpoints


@router.get("/status", summary="Local agent runtime status")
def get_status(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> dict:
    return agent_status.build_status(settings, APP_VERSION, APP_PHASE, db=db)


@router.get("/settings", summary="View mutable settings")
def get_settings_view(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "settings": agent_status.build_settings_view(settings),
        "mutable": sorted(agent_status.MUTABLE_SETTINGS),
    }


@router.patch("/settings", summary="Patch mutable settings (in-memory only)")
def patch_settings(
    body: SettingsPatch,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> dict:
    result = agent_status.apply_settings_patch(settings, body.patch)
    # Audit the change so the operator can see who tweaked the
    # local settings and when.
    if result["applied"]:
        from ..services.audit import log_action
        try:
            log_action(
                db=db,
                actor="local",
                action="local.settings.update",
                entity_type="local",
                entity_id=0,
                details=f"applied: {result['applied']}",
            )
            db.commit()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("could not audit local settings patch: %s", exc)
    return result


@router.get("/storage", summary="Local storage directory summary")
def get_storage(settings: Settings = Depends(get_settings)) -> dict:
    return storage_manager.summarize(settings)


@router.post("/export-audit", summary="Export the audit log to a local CSV")
def export_audit(
    limit: int = 1000,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> dict:
    rows = (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .all()
    )
    row_dicts = [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "actor": r.actor,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "details": r.details,
            "before_data_json": r.before_data_json,
            "after_data_json": r.after_data_json,
        }
        for r in rows
    ]
    path, count = storage_manager.export_audit_csv(settings, row_dicts)
    return {
        "path": path,
        "rows_exported": count,
        "limit": limit,
    }


@router.post("/export-logs", summary="Package logs into a downloadable ZIP")
def export_logs(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> dict:
    logs_dir = settings.logs_dir
    import io, zipfile, datetime, platform, json

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "exported_at": datetime.datetime.utcnow().isoformat(),
            "version": APP_VERSION,
            "phase": APP_PHASE,
            "platform": platform.platform(),
            "python": platform.python_version(),
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        if logs_dir and Path(logs_dir).exists():
            log_files = sorted(Path(logs_dir).iterdir(), key=os.path.getmtime, reverse=True)
            for lf in log_files[:5]:
                if lf.is_file() and lf.stat().st_size > 0:
                    try:
                        data = lf.read_bytes()
                        zf.writestr(f"logs/{lf.name}", data)
                    except OSError:
                        pass
        try:
            audit_rows = (
                db.query(AuditLog)
                .order_by(AuditLog.id.desc())
                .limit(200)
                .all()
            )
            audit_data = [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "actor": r.actor,
                    "action": r.action,
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                }
                for r in audit_rows
            ]
            zf.writestr("recent_audit_log.json", json.dumps(audit_data, indent=2))
        except Exception:
            pass

    import base64
    b64 = base64.b64encode(buf.getvalue()).decode()
    return {"filename": f"officepilot_logs_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip", "content_base64": b64, "size_bytes": len(buf.getvalue())}


@router.post("/clear-cache", summary="Wipe transient cache directories")
def clear_cache(
    confirm: bool = False,
    settings: Settings = Depends(get_settings),
) -> dict:
    if not confirm:
        return {
            "cleared": False,
            "message": "pass ?confirm=true to clear the cache",
        }
    result = storage_manager.clear_cache(settings)
    return {"cleared": True, **result}
