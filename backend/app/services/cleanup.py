"""Phase 21 — Local data cleanup with safety rules.

Only removes:
- old demo data
- old temporary files
- old bug report packages
- old audit export packages if over limit
- old screenshots if configured

Never deletes:
- real invoices
- real audit logs
- real accounting sync logs
- backups
- version history
"""

from __future__ import annotations

import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.audit_log import AuditLog
from ..models.audit_export import AuditExport
from ..models.bug_report import BugReport
from ..models.demo_walkthrough import DemoWalkthrough
from ..models.invoice import Invoice
from ..models.pilot_feedback import PilotFeedback
from ..models.usage_event import UsageEvent


def _is_real_invoice(db: Session, invoice_id: int) -> bool:
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if inv and inv.email_source == "demo":
        return False
    return True


def get_storage_usage(db: Session) -> dict[str, Any]:
    settings = get_settings()
    bug_reports_dir = settings.data_dir / "bug_reports"
    exports_dir = settings.data_dir / "audit_exports"
    screenshots_dir = settings.browser_snapshots_dir

    def _dir_size(p: Path) -> int:
        if not p.exists():
            return 0
        total = 0
        for entry in p.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
        return total

    def _file_count(p: Path) -> int:
        if not p.exists():
            return 0
        return sum(1 for _ in p.rglob("*") if _.is_file())

    return {
        "bug_reports": {
            "path": str(bug_reports_dir),
            "size_bytes": _dir_size(bug_reports_dir),
            "file_count": _file_count(bug_reports_dir),
        },
        "audit_exports": {
            "path": str(exports_dir),
            "size_bytes": _dir_size(exports_dir),
            "file_count": _file_count(exports_dir),
        },
        "browser_screenshots": {
            "path": str(screenshots_dir),
            "size_bytes": _dir_size(screenshots_dir),
            "file_count": _file_count(screenshots_dir),
        },
        "cache_dir": {
            "path": str(settings.cache_dir),
            "size_bytes": _dir_size(settings.cache_dir),
            "file_count": _file_count(settings.cache_dir),
        },
        "demo_invoices": {
            "count": db.query(Invoice).filter(Invoice.email_source == "demo").count(),
        },
    }


def build_cleanup_preview(db: Session) -> dict[str, Any]:
    settings = get_settings()
    now = datetime.utcnow()
    preview: dict[str, Any] = {"items": [], "total_bytes_estimate": 0}

    # Old bug report packages
    max_packages = getattr(settings, "max_bug_report_packages", 50)
    bug_dir = settings.data_dir / "bug_reports"
    if bug_dir.exists():
        packages = sorted(bug_dir.iterdir(), key=lambda p: p.stat().st_mtime if p.is_file() else 0)
        if len(packages) > max_packages:
            for p in packages[: len(packages) - max_packages]:
                size = p.stat().st_size if p.is_file() else 0
                preview["items"].append({
                    "type": "bug_report_package",
                    "path": str(p),
                    "size_bytes": size,
                    "reason": f"Over {max_packages} package limit",
                })
                preview["total_bytes_estimate"] += size

    # Old audit export packages
    max_exports = getattr(settings, "max_audit_exports", 50)
    exports_dir = settings.data_dir / "audit_exports"
    if exports_dir.exists():
        exports = sorted(exports_dir.iterdir(), key=lambda p: p.stat().st_mtime if p.is_file() else 0)
        if len(exports) > max_exports:
            for p in exports[: len(exports) - max_exports]:
                size = p.stat().st_size if p.is_file() else 0
                preview["items"].append({
                    "type": "audit_export_package",
                    "path": str(p),
                    "size_bytes": size,
                    "reason": f"Over {max_exports} export limit",
                })
                preview["total_bytes_estimate"] += size

    # Old demo walkthrough data in DB
    demo_retention = getattr(settings, "demo_data_retention_days", 30)
    cutoff = now - timedelta(days=demo_retention)
    old_demos = db.query(DemoWalkthrough).filter(
        DemoWalkthrough.created_at < cutoff,
        DemoWalkthrough.completed_at.isnot(None),
    ).all()
    for d in old_demos:
        preview["items"].append({
            "type": "demo_walkthrough",
            "id": d.id,
            "created_at": str(d.created_at),
            "reason": f"Older than {demo_retention} days",
        })

    # Old bug report records in DB
    bug_retention = getattr(settings, "log_retention_days", 90)
    bug_cutoff = now - timedelta(days=bug_retention)
    old_bugs = db.query(BugReport).filter(BugReport.created_at < bug_cutoff).all()
    for b in old_bugs:
        preview["items"].append({
            "type": "bug_report_record",
            "id": b.id,
            "created_at": str(b.created_at),
            "reason": f"Older than {bug_retention} days",
        })

    # Old usage events
    max_events = 10000
    total_events = db.query(UsageEvent).count()
    if total_events > max_events:
        excess = total_events - max_events
        old_events = (
            db.query(UsageEvent)
            .order_by(UsageEvent.created_at.asc())
            .limit(excess)
            .all()
        )
        for evt in old_events:
            preview["items"].append({
                "type": "usage_event",
                "id": evt.id,
                "created_at": str(evt.created_at),
                "reason": f"Over {max_events} event limit",
            })

    return preview


def run_cleanup(db: Session, confirmed: bool = False) -> dict[str, Any]:
    if not confirmed:
        return {"status": "error", "detail": "Confirmation required. Set confirmed=true."}

    settings = get_settings()
    now = datetime.utcnow()
    removed: dict[str, int] = {"bug_report_packages": 0, "audit_exports": 0, "demo_walkthroughs": 0, "bug_report_records": 0, "usage_events": 0}

    # Clean old bug report packages (FS)
    max_packages = getattr(settings, "max_bug_report_packages", 50)
    bug_dir = settings.data_dir / "bug_reports"
    if bug_dir.exists():
        packages = sorted(bug_dir.iterdir(), key=lambda p: p.stat().st_mtime if p.is_file() else 0)
        if len(packages) > max_packages:
            for p in packages[: len(packages) - max_packages]:
                try:
                    if p.is_file():
                        p.unlink()
                    elif p.is_dir():
                        shutil.rmtree(p)
                    removed["bug_report_packages"] += 1
                except OSError:
                    pass

    # Clean old audit exports (FS)
    max_exports = getattr(settings, "max_audit_exports", 50)
    exports_dir = settings.data_dir / "audit_exports"
    if exports_dir.exists():
        exports = sorted(exports_dir.iterdir(), key=lambda p: p.stat().st_mtime if p.is_file() else 0)
        if len(exports) > max_exports:
            for p in exports[: len(exports) - max_exports]:
                try:
                    if p.is_file():
                        p.unlink()
                    elif p.is_dir():
                        shutil.rmtree(p)
                    removed["audit_exports"] += 1
                except OSError:
                    pass

    # Remove old demo walkthroughs (DB)
    demo_retention = getattr(settings, "demo_data_retention_days", 30)
    cutoff = now - timedelta(days=demo_retention)
    old_demos = db.query(DemoWalkthrough).filter(
        DemoWalkthrough.created_at < cutoff,
        DemoWalkthrough.completed_at.isnot(None),
    )
    removed["demo_walkthroughs"] = old_demos.count()
    old_demos.delete(synchronize_session=False)

    # Remove old bug report records (DB)
    bug_retention = getattr(settings, "log_retention_days", 90)
    bug_cutoff = now - timedelta(days=bug_retention)
    old_bugs = db.query(BugReport).filter(BugReport.created_at < bug_cutoff)
    removed["bug_report_records"] = old_bugs.count()
    old_bugs.delete(synchronize_session=False)

    # Trim usage events to max 10000
    max_events = 10000
    total_events = db.query(UsageEvent).count()
    if total_events > max_events:
        excess = total_events - max_events
        old_events = (
            db.query(UsageEvent)
            .order_by(UsageEvent.created_at.asc())
            .limit(excess)
            .all()
        )
        ids = [e.id for e in old_events]
        db.query(UsageEvent).filter(UsageEvent.id.in_(ids)).delete(synchronize_session=False)
        removed["usage_events"] = len(ids)

    db.commit()
    return {"status": "ok", "removed": removed}
