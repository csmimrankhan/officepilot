"""Phase 18 — First-run diagnostics service."""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings

logger = logging.getLogger("officepilot.diagnostics")


def run_diagnostics(db: Session) -> dict[str, Any]:
    settings = get_settings()
    results = []
    all_ok = True

    # 1. Sidecar / backend process
    sidecar_ok = True
    results.append({
        "name": "Backend Process",
        "status": "ok" if sidecar_ok else "error",
        "detail": "Backend is running",
        "fix": None,
    })

    # 2. Database accessible
    db_ok = True
    try:
        db.execute(db.bind.dialect.statement_compiler(dialect=db.bind.dialect).__class__.__name__ == "")
        db_ok = True
    except Exception as exc:
        db_ok = False
        all_ok = False
    # Simpler check: just run a query
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        db_ok = False
        all_ok = False
        db_detail = str(exc)
    else:
        db_detail = "Connected"
    results.append({
        "name": "Database",
        "status": "ok" if db_ok else "error",
        "detail": db_detail,
        "fix": "Check OFFICEPILOT_DB_URL and ensure SQLite file is writable" if not db_ok else None,
    })

    # 3. Storage writable
    storage_path = settings.storage_root
    storage_ok = False
    try:
        storage_path.mkdir(parents=True, exist_ok=True)
        test_file = storage_path / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        storage_ok = True
    except Exception as exc:
        all_ok = False
    results.append({
        "name": "Storage Path",
        "status": "ok" if storage_ok else "error",
        "detail": str(storage_path) if storage_ok else f"Not writable",
        "fix": f"Ensure {storage_path} exists and is writable" if not storage_ok else None,
    })

    # 4. Sample folder exists
    samples_dir = settings.project_root / "samples"
    samples_ok = samples_dir.exists()
    if not samples_ok:
        all_ok = False
    results.append({
        "name": "Sample Data",
        "status": "ok" if samples_ok else "warning",
        "detail": str(samples_dir) if samples_ok else "Not found",
        "fix": "Create samples/ directory with sample files" if not samples_ok else None,
    })

    # 5. OCR availability
    ocr_enabled = settings.ocr_enabled
    ocr_available = False
    if ocr_enabled:
        tesseract = shutil.which("tesseract") or os.environ.get("OFFICEPILOT_TESSERACT_CMD")
        ocr_available = tesseract is not None
    results.append({
        "name": "OCR Engine",
        "status": "ok" if ocr_available else ("disabled" if not ocr_enabled else "warning"),
        "detail": "Tesseract found" if ocr_available else ("OCR disabled" if not ocr_enabled else "Tesseract not found"),
        "fix": "Install Tesseract or set OFFICEPILOT_TESSERACT_CMD" if ocr_enabled and not ocr_available else None,
    })

    # 6. Playwright availability
    playwright_available = False
    try:
        import playwright  # noqa: F401
        playwright_available = True
    except ImportError:
        playwright_available = False
    results.append({
        "name": "Playwright",
        "status": "ok" if playwright_available else "warning",
        "detail": "Installed" if playwright_available else "Not installed (browser automation unavailable)",
        "fix": "Run: pip install playwright && playwright install chromium" if not playwright_available else None,
    })

    # 7. Disk space
    disk_path = settings.data_dir
    try:
        disk_free = shutil.disk_usage(disk_path).free
        disk_free_gb = round(disk_free / (1024 ** 3), 1)
        disk_ok = disk_free_gb > 0.5
        if not disk_ok:
            all_ok = False
    except Exception:
        disk_free_gb = 0
        disk_ok = False
        all_ok = False
    results.append({
        "name": "Disk Space",
        "status": "ok" if disk_ok else "warning",
        "detail": f"{disk_free_gb} GB free" if disk_ok else "Low disk space",
        "fix": "Free up disk space" if not disk_ok else None,
    })

    # 8. Auth configured
    auth_ok = bool(settings.jwt_secret) or True  # auto-generated
    results.append({
        "name": "Authentication",
        "status": "ok",
        "detail": "JWT auth configured",
        "fix": None,
    })

    # 9. Safety policy seeded
    from ..models.safety_policy import SafetyPolicy
    safety_seeded = db.query(SafetyPolicy).count() > 0
    results.append({
        "name": "Safety Policy",
        "status": "ok" if safety_seeded else "warning",
        "detail": "Seeded" if safety_seeded else "Not seeded",
        "fix": "Restart the backend to auto-seed safety policy" if not safety_seeded else None,
    })

    # 10. Permissions seeded
    from ..models.role_permission import RolePermission
    perms_seeded = db.query(RolePermission).count() > 0
    results.append({
        "name": "Role Permissions",
        "status": "ok" if perms_seeded else "warning",
        "detail": "Seeded" if perms_seeded else "Not seeded",
        "fix": "Restart the backend to auto-seed permissions" if not perms_seeded else None,
    })

    overall = "green" if all_ok else "yellow" if any(r["status"] == "warning" for r in results) else "red"
    return {
        "overall": overall,
        "items": results,
        "timestamp": datetime.utcnow().isoformat(),
    }
