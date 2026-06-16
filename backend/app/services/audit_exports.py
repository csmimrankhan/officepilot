"""Phase 16B — Enterprise audit export builder."""

from __future__ import annotations

import csv
import io
import json
import logging
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.audit_export import AuditExport
from ..models.audit_log import AuditLog
from ..models.browser_action_run import BrowserActionRun
from ..models.browser_action_step import BrowserActionStep
from ..models.accounting_sync_log import AccountingSyncLog
from ..models.screen_control_action import ScreenControlAction
from ..models.screen_control_session import ScreenControlSession
from ..models.workflow_run import WorkflowRun
from ..models.restore_log import RestoreLog

logger = logging.getLogger("officepilot.audit_export")

# Map of log type names to (model_class, query_filter) for generic export.
LOG_TYPE_QUERIES: dict[str, callable] = {}


def _export_table_to_dicts(db: Session, model, date_field: str, date_from: str = "", date_to: str = "") -> list[dict]:
    q = db.query(model)
    try:
        col = getattr(model, date_field)
        if date_from:
            q = q.filter(col >= date_from)
        if date_to:
            q = q.filter(col <= date_to)
    except AttributeError:
        pass
    rows = q.all()
    return [{c.name: getattr(r, c.name) for c in model.__table__.columns} for r in rows]


def build_export(
    db: Session,
    export_type: str,
    date_from: str,
    date_to: str,
    log_types: list[str],
    created_by: str = "user",
) -> AuditExport:
    settings = get_settings()
    export_dir = settings.data_dir / "audit_exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    ext = "json" if export_type == "json" else "csv"
    filename = f"audit_export_{ts}.{ext}"
    file_path = str(export_dir / filename)

    export = AuditExport(
        export_type=export_type,
        date_from=date_from,
        date_to=date_to,
        log_types_json=json.dumps(log_types),
        status="running",
        file_path="",
        created_by=created_by,
        created_at=datetime.utcnow(),
    )
    db.add(export)
    db.flush()

    try:
        data = _collect_export_data(db, log_types, date_from, date_to)

        if export_type == "zip":
            _write_zip(file_path, data)
        elif export_type == "csv":
            _write_csv(file_path, data)
        else:
            _write_json(file_path, data)

        if export_type == "zip":
            zip_path = file_path
        else:
            zip_path = file_path

        export.file_path = zip_path
        export.status = "completed"
        export.completed_at = datetime.utcnow()
    except Exception as e:
        logger.exception("Audit export failed")
        export.status = "failed"
        export.error_message = str(e)

    db.flush()
    return export


def _collect_export_data(
    db: Session, log_types: list[str], date_from: str, date_to: str
) -> dict[str, list[dict]]:
    data: dict[str, list[dict]] = {}

    type_map = {
        "audit_logs": (AuditLog, "timestamp"),
        "browser_actions": (BrowserActionRun, "created_at"),
        "browser_steps": (BrowserActionStep, "created_at"),
        "accounting_sync": (AccountingSyncLog, "created_at"),
        "screen_actions": (ScreenControlAction, "created_at"),
        "screen_sessions": (ScreenControlSession, "started_at"),
        "workflow_runs": (WorkflowRun, "created_at"),
        "restore_logs": (RestoreLog, "created_at"),
    }

    selected = log_types if log_types else list(type_map.keys())
    for key in selected:
        if key in type_map:
            model, date_field = type_map[key]
            data[key] = _export_table_to_dicts(db, model, date_field, date_from, date_to)

    return data


def _write_json(file_path: str, data: dict) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _write_csv(file_path: str, data: dict) -> None:
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["log_type", "field", "value"])
        for log_type, rows in data.items():
            for row in rows:
                for key, value in row.items():
                    writer.writerow([log_type, key, str(value) if value is not None else ""])


def _write_zip(file_path: str, data: dict) -> None:
    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for log_type, rows in data.items():
            content = json.dumps(rows, indent=2, default=str)
            zf.writestr(f"{log_type}.json", content)


def list_exports(db: Session, limit: int = 20) -> list[AuditExport]:
    return (
        db.query(AuditExport)
        .order_by(AuditExport.id.desc())
        .limit(limit)
        .all()
    )
