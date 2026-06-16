"""Phase 16B/17 — Local backup and restore endpoints (authenticated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..schemas.safety import BackupRunResponse, BackupStatusRead, RestoreTestResponse
from ..services.backup import get_backup_status, run_local_backup, test_restore
from ..services.permissions import check_permission

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/status", response_model=BackupStatusRead)
def backup_status(
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    status = get_backup_status()
    return BackupStatusRead(**status)


@router.post("/run-local", response_model=BackupRunResponse)
def run_backup(
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    result = run_local_backup()
    return BackupRunResponse(**result)


@router.post("/test-restore", response_model=RestoreTestResponse)
def test_backup_restore(
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    result = test_restore()
    return RestoreTestResponse(**result)
