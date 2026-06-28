"""Phase 18 — About page endpoint."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user

logger = logging.getLogger("officepilot.about_router")

router = APIRouter(prefix="/api/about", tags=["about"])


@router.get("")
def about(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = get_settings()
    data_dir = settings.data_dir
    logs_path = data_dir / "logs"
    build_date = "unknown"
    build_file = settings.project_root / "BUILD_DATE"
    if build_file.exists():
        build_date = build_file.read_text(encoding="utf-8").strip()
    sidecar_path = settings.project_root / "desktop" / "tauri" / "src-tauri" / "binaries"
    sidecar_exe = None
    if sidecar_path.exists():
        for f in sidecar_path.glob("officepilot-agent-*.exe"):
            sidecar_exe = str(f)
            break

    return {
        "version": "1.0.0",
        "phase": 19,
        "app_name": "OfficePilot AI",
        "backend_healthy": True,
        "sidecar_status": "found" if sidecar_exe else "not_found",
        "sidecar_path": sidecar_exe,
        "database_path": settings.database_url.replace("sqlite:///", ""),
        "storage_path": str(settings.storage_root),
        "data_dir": str(data_dir),
        "logs_path": str(logs_path),
        "build_date": build_date,
        "demo_mode": settings.demo_mode,
    }
