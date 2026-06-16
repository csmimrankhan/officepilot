"""Email import history HTTP API (Phase 2)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models.email_import import EmailImport, EmailImportStatus
from ..schemas.email import EmailImportRead

router = APIRouter(prefix="/api/email-imports", tags=["email-imports"])


@router.get("", response_model=list[EmailImportRead])
def list_email_imports(
    account_id: Optional[int] = None,
    status_filter: Optional[EmailImportStatus] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(EmailImport).options(selectinload(EmailImport.attachments))
    if account_id is not None:
        q = q.filter(EmailImport.account_id == account_id)
    if status_filter is not None:
        q = q.filter(EmailImport.status == status_filter)
    q = q.order_by(EmailImport.id.desc()).offset(offset).limit(limit)
    return [EmailImportRead.model_validate(r) for r in q.all()]


@router.get("/{import_id}", response_model=EmailImportRead)
def get_email_import(import_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(EmailImport)
        .options(selectinload(EmailImport.attachments))
        .filter(EmailImport.id == import_id)
        .first()
    )
    if row is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Email import {import_id} not found")
    return EmailImportRead.model_validate(row)
