"""Phase 16B/17 — Enterprise audit export endpoints (authenticated)."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.audit_export import AuditExport
from ..models.user import User
from ..routers.auth import get_current_user
from ..schemas.safety import (
    AuditExportRead,
    AuditExportRequest,
)
from ..services.audit_exports import build_export, list_exports
from ..services.permissions import check_permission

logger = logging.getLogger("officepilot.audit_export_router")

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.post("/export", response_model=AuditExportRead)
def create_audit_export(
    body: AuditExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_permission(db, current_user.role, "export_audit"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    export = build_export(
        db=db,
        export_type=body.export_type,
        date_from=body.date_from,
        date_to=body.date_to,
        log_types=body.log_types,
        created_by=current_user.email,
    )
    db.commit()
    return AuditExportRead(
        id=export.id,
        export_type=export.export_type,
        date_from=export.date_from,
        date_to=export.date_to,
        log_types_json=export.log_types_json,
        status=export.status,
        file_path=export.file_path,
        created_by=export.created_by,
        created_at=export.created_at.isoformat() if export.created_at else None,
        completed_at=export.completed_at.isoformat() if export.completed_at else None,
        error_message=export.error_message,
    )


@router.get("/exports", response_model=list[AuditExportRead])
def list_audit_exports(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_permission(db, current_user.role, "view_audit_logs"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    exports = list_exports(db, limit=limit)
    return [
        AuditExportRead(
            id=e.id,
            export_type=e.export_type,
            date_from=e.date_from,
            date_to=e.date_to,
            log_types_json=e.log_types_json,
            status=e.status,
            file_path=e.file_path,
            created_by=e.created_by,
            created_at=e.created_at.isoformat() if e.created_at else None,
            completed_at=e.completed_at.isoformat() if e.completed_at else None,
            error_message=e.error_message,
        )
        for e in exports
    ]


@router.get("/exports/{export_id}", response_model=AuditExportRead)
def get_audit_export(
    export_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_permission(db, current_user.role, "view_audit_logs"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    export = db.get(AuditExport, export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Export not found")
    return AuditExportRead(
        id=export.id,
        export_type=export.export_type,
        date_from=export.date_from,
        date_to=export.date_to,
        log_types_json=export.log_types_json,
        status=export.status,
        file_path=export.file_path,
        created_by=export.created_by,
        created_at=export.created_at.isoformat() if export.created_at else None,
        completed_at=export.completed_at.isoformat() if export.completed_at else None,
        error_message=export.error_message,
    )


@router.get("/exports/{export_id}/download")
def download_audit_export(
    export_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_permission(db, current_user.role, "view_audit_logs"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    export = db.get(AuditExport, export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Export not found")
    if export.status != "completed":
        raise HTTPException(status_code=400, detail="Export is not yet completed (status=%s)" % export.status)

    fpath = Path(export.file_path)
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="Export file not found on disk")

    media_type = "application/json"
    if export.export_type == "csv":
        media_type = "text/csv"
    elif export.export_type == "zip":
        media_type = "application/zip"

    return FileResponse(
        path=str(fpath),
        filename=fpath.name,
        media_type=media_type,
    )
