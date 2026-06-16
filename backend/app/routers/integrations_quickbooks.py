"""Phase 38.6 Task 2 — QuickBooks sync endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.accounting_connection import AccountingConnection
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.quickbooks_sync import get_sync_status, run_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quickbooks", tags=["quickbooks"])


@router.get("/status")
def quickbooks_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_sync_status(db)


@router.post("/sync")
def quickbooks_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conn = (
        db.query(AccountingConnection)
        .filter(
            AccountingConnection.provider == "quickbooks",
            AccountingConnection.status == "active",
        )
        .order_by(AccountingConnection.id.desc())
        .first()
    )
    if conn is None:
        raise HTTPException(status_code=409, detail="QuickBooks is not connected")
    result = run_sync(db, conn.id)
    if result["status"] == "failed":
        raise HTTPException(status_code=502, detail=result.get("error", "Sync failed"))
    return result
