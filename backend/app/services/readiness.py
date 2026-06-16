"""Phase 16B — Production readiness checks."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.audit_export import AuditExport
from ..services.safety import get_or_create_safety_policy, is_kill_switch_active


def _green(msg: str) -> dict:
    return {"name": "", "status": "green", "message": msg}


def _yellow(msg: str) -> dict:
    return {"name": "", "status": "yellow", "message": msg}


def _red(msg: str) -> dict:
    return {"name": "", "status": "red", "message": msg}


def build_readiness_report(db: Session) -> dict:
    settings = get_settings()
    items = []
    overall = "green"

    # Sidecar / process check
    is_frozen = bool(getattr(sys, "frozen", False))
    items.append(
        _green("Backend process is running (frozen=%s)" % is_frozen)
        if True
        else _red("Backend process not running")
    )

    # Database
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        items.append(_green("Database is reachable"))
    except Exception as e:
        items.append(_red("Database error: %s" % e))
        overall = "red"

    # Storage path
    storage = settings.data_dir
    if storage.exists():
        items.append(_green("Storage path exists: %s" % storage))
    else:
        items.append(_yellow("Storage path missing: %s" % storage))
        if overall == "green":
            overall = "yellow"

    # Disk space
    try:
        total, used, free = shutil.disk_usage(storage)
        free_gb = free / (1024**3)
        items.append(_green("Disk: %.1f GB free" % free_gb))
        if free_gb < 1.0:
            items.append(_red("Low disk space: %.1f GB free" % free_gb))
            overall = "red"
    except Exception:
        items.append(_yellow("Could not check disk space"))
        if overall == "green":
            overall = "yellow"

    # Safety policy
    try:
        policy = get_or_create_safety_policy(db)
        risky = []
        if policy.browser_automation_enabled:
            risky.append("browser")
        if policy.screen_control_enabled:
            risky.append("screen control")
        if policy.workflow_recording_enabled:
            risky.append("workflow recording")
        if policy.accounting_sync_enabled:
            risky.append("accounting sync")
        if risky:
            items.append(_yellow("Risky features enabled: %s" % ", ".join(risky)))
            if overall == "green":
                overall = "yellow"
        else:
            items.append(_green("Safety policy: all risky features disabled"))
    except Exception as e:
        items.append(_yellow("Safety policy check failed: %s" % e))

    # Kill switch
    if is_kill_switch_active():
        items.append(_yellow("Kill switch is ACTIVE"))
        if overall == "green":
            overall = "yellow"
    else:
        items.append(_green("Kill switch is inactive (normal)"))

    # OCR
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        items.append(_green("Tesseract OCR is available"))
    except Exception:
        try:
            import subprocess
            result = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                items.append(_green("Tesseract CLI is available"))
            else:
                items.append(_yellow("Tesseract CLI not available (OCR limited)"))
                if overall == "green":
                    overall = "yellow"
        except Exception:
            items.append(_yellow("Tesseract OCR not installed"))
            if overall == "green":
                overall = "yellow"

    # Playwright/browser
    try:
        import playwright
        items.append(_green("Playwright is available"))
    except ImportError:
        items.append(_yellow("Playwright not installed (browser automation limited)"))
        if overall == "green":
            overall = "yellow"

    # Gmail
    gmail_configured = settings.gmail_configured
    if gmail_configured:
        items.append(_green("Gmail integration is configured"))
    else:
        items.append(_yellow("Gmail not configured"))
        if overall == "green":
            overall = "yellow"

    # QuickBooks / Xero
    qb = bool(settings.quickbooks_client_id)
    xero = bool(settings.xero_client_id)
    if qb or xero:
        parts = []
        if qb:
            parts.append("QuickBooks")
        if xero:
            parts.append("Xero")
        items.append(_green("%s configured" % " + ".join(parts)))
    else:
        items.append(_yellow("No accounting integration configured"))
        if overall == "green":
            overall = "yellow"

    # Last backup check
    last_export = (
        db.query(AuditExport)
        .filter(AuditExport.status == "completed")
        .order_by(AuditExport.id.desc())
        .first()
    )
    if last_export:
        items.append(_green("Last export: %s" % last_export.created_at))
    else:
        items.append(_yellow("No audit exports found"))
        if overall == "green":
            overall = "yellow"

    # Format items with names
    item_names = [
        "Backend Process", "Database", "Storage Path", "Disk Space",
        "Safety Policy", "Kill Switch", "OCR Engine", "Playwright",
        "Gmail", "Accounting", "Audit Exports",
    ]
    for i, item in enumerate(items):
        if i < len(item_names):
            item["name"] = item_names[i]

    return {"overall": overall, "items": items}
