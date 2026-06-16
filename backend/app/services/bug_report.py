"""Phase 19 — Bug report service with safe diagnostics collection."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.bug_report import BugReport
from ..services.diagnostics import run_diagnostics

logger = logging.getLogger("officepilot.bug_report")

SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(secret|api_key|api_secret|token|auth_token)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(2fa|otp|cvv|ssn|pin)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(jwt)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(access_token|refresh_token)\s*[=:]\s*\S+"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),  # email addresses
]

REDACTED_LABEL = "[REDACTED]"

EVENT_LOG_CAPTURE_LINES = 200


def redact_text(text: str) -> str:
    if not text:
        return text
    result = text
    for pattern in SENSITIVE_PATTERNS:
        result = pattern.sub(lambda m: re.sub(r"\S+", REDACTED_LABEL, m.group(0)), result)
    return result


def create_bug_report(
    db: Session,
    user_id: int,
    title: str,
    description: str,
    severity: str = "medium",
    include_logs: bool = False,
    include_screenshot: bool = False,
    include_readiness: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    bug_dir = settings.data_dir / "bug_reports"
    bug_dir.mkdir(parents=True, exist_ok=True)

    report_id = str(uuid.uuid4())[:8]
    package_dir = bug_dir / f"bug_report_{report_id}"
    package_dir.mkdir(parents=True, exist_ok=True)

    br = BugReport(
        user_id=user_id,
        title=title,
        description=description,
        severity=severity,
        include_logs=include_logs,
        include_screenshot=include_screenshot,
        include_readiness=include_readiness,
        package_path=str(package_dir),
        status="open",
    )
    db.add(br)
    db.flush()

    _write_package_metadata(package_dir, br, user_id, settings)
    _capture_diagnostics(db, package_dir, include_logs, include_readiness, settings)

    db.commit()
    return _bug_report_to_dict(br)


def _write_package_metadata(package_dir: Path, br: BugReport, user_id: int, settings) -> None:
    meta = {
        "report_id": br.id,
        "title": br.title,
        "description": redact_text(br.description),
        "severity": br.severity,
        "app_version": "0.36.1",
        "backend_phase": 19,
        "demo_mode": settings.demo_mode,
        "created_at": datetime.utcnow().isoformat(),
        "included_logs": br.include_logs,
        "included_screenshot": br.include_screenshot,
        "included_readiness": br.include_readiness,
        "redaction_note": "All sensitive values (passwords, tokens, secrets, emails) have been redacted.",
    }
    (package_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _capture_diagnostics(db: Session, package_dir: Path, include_logs: bool, include_readiness: bool, settings) -> None:
    if include_readiness:
        try:
            diag = run_diagnostics(db)
            diag_redacted = redact_text(json.dumps(diag, indent=2))
            (package_dir / "readiness.json").write_text(diag_redacted, encoding="utf-8")
        except Exception as e:
            (package_dir / "readiness_error.txt").write_text(str(e), encoding="utf-8")

    if include_logs:
        _capture_logs(package_dir, settings)


def _capture_logs(package_dir: Path, settings) -> None:
    logs_dir = settings.logs_dir
    if not logs_dir or not Path(logs_dir).exists():
        (package_dir / "logs_note.txt").write_text("Logs directory not available.", encoding="utf-8")
        return
    log_files = sorted(Path(logs_dir).glob("*.log"), key=os.path.getmtime, reverse=True)
    if not log_files:
        log_files = sorted(Path(logs_dir).glob("*"), key=os.path.getmtime, reverse=True)
    if log_files:
        latest = log_files[0]
        try:
            lines = latest.read_text(encoding="utf-8", errors="replace").splitlines()
            tail = lines[-EVENT_LOG_CAPTURE_LINES:]
            redacted = [redact_text(line) for line in tail]
            (package_dir / "recent_logs.txt").write_text(
                f"Source: {latest.name}\nLines: {len(redacted)}\n\n" + "\n".join(redacted),
                encoding="utf-8",
            )
        except Exception as e:
            (package_dir / "logs_error.txt").write_text(f"Failed to read logs: {e}", encoding="utf-8")
    else:
        (package_dir / "logs_note.txt").write_text("No log files found.", encoding="utf-8")


def get_bug_report(db: Session, report_id: int) -> dict[str, Any] | None:
    br = db.query(BugReport).filter(BugReport.id == report_id).first()
    if br is None:
        return None
    return _bug_report_to_dict(br)


def list_bug_reports(db: Session, user_id: int | None = None, limit: int = 100, skip: int = 0) -> list[dict[str, Any]]:
    q = db.query(BugReport)
    if user_id is not None:
        q = q.filter(BugReport.user_id == user_id)
    q = q.order_by(BugReport.created_at.desc()).offset(skip).limit(limit)
    return [_bug_report_to_dict(br) for br in q.all()]


def get_package_path(db: Session, report_id: int) -> str | None:
    br = db.query(BugReport).filter(BugReport.id == report_id).first()
    if br is None or not br.package_path:
        return None
    return br.package_path


def _bug_report_to_dict(br: BugReport) -> dict[str, Any]:
    return {
        "id": br.id,
        "user_id": br.user_id,
        "title": br.title,
        "description": br.description,
        "severity": br.severity,
        "include_logs": br.include_logs,
        "include_screenshot": br.include_screenshot,
        "include_readiness": br.include_readiness,
        "package_path": br.package_path,
        "status": br.status,
        "created_at": br.created_at.isoformat(),
        "updated_at": br.updated_at.isoformat(),
    }
