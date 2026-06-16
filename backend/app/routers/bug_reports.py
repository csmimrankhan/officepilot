"""Phase 19 — Bug report endpoints."""

from __future__ import annotations

import json
import logging
import os
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.bug_report import create_bug_report, get_bug_report, get_package_path, list_bug_reports

logger = logging.getLogger("officepilot.bug_report_router")

router = APIRouter(prefix="/api/bug-reports", tags=["bug-reports"])


class CreateBugReportBody(BaseModel):
    title: str
    description: str
    severity: str = "medium"
    include_logs: bool = False
    include_screenshot: bool = False
    include_readiness: bool = False


@router.post("")
def create_bug_report_endpoint(
    body: CreateBugReportBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_bug_report(
        db,
        current_user.id,
        title=body.title,
        description=body.description,
        severity=body.severity,
        include_logs=body.include_logs,
        include_screenshot=body.include_screenshot,
        include_readiness=body.include_readiness,
    )


@router.get("")
def list_bug_reports_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_owner_or_admin = current_user.role in ("owner", "admin")
    user_id = None if is_owner_or_admin else current_user.id
    return list_bug_reports(db, user_id=user_id, skip=skip, limit=limit)


@router.get("/{report_id}")
def get_bug_report_endpoint(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    br = get_bug_report(db, report_id)
    if br is None:
        raise HTTPException(status_code=404, detail="Bug report not found")
    return br


@router.get("/{report_id}/download")
def download_bug_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    br = get_bug_report(db, report_id)
    if br is None:
        raise HTTPException(status_code=404, detail="Bug report not found")

    pkg_path = get_package_path(db, report_id)
    if not pkg_path or not Path(pkg_path).exists():
        raise HTTPException(status_code=410, detail="Bug report package files no longer available on disk")

    buf = BytesIO()
    pkg_dir = Path(pkg_path)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in pkg_dir.rglob("*"):
            if file_path.is_file():
                arcname = str(file_path.relative_to(pkg_dir))
                zf.write(file_path, arcname)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=bug_report_{report_id}.zip"},
    )
