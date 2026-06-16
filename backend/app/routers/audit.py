"""Audit log HTTP API."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.audit_log import AuditLog
from ..schemas.invoice import AuditLogRead

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if action: q = q.filter(AuditLog.action == action)
    if entity_type: q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None: q = q.filter(AuditLog.entity_id == entity_id)
    q = q.order_by(AuditLog.id.desc()).offset(offset).limit(limit)
    return [AuditLogRead.model_validate(r) for r in q.all()]
