"""Phase 19 — Usage tracking endpoints."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.usage_tracking import (
    get_usage_summary,
    is_tracking_enabled,
    list_usage_events,
    record_event,
)

logger = logging.getLogger("officepilot.usage_router")

router = APIRouter(prefix="/api/usage", tags=["usage"])


class RecordEventBody(BaseModel):
    event_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None


@router.post("/events")
def record_usage_event(
    body: RecordEventBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = record_event(
        db,
        current_user.id,
        event_type=body.event_type,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        metadata=body.metadata,
    )
    if result is None:
        return {"tracking_enabled": False, "recorded": False}
    return {"tracking_enabled": True, "recorded": True, "event": result}


@router.get("/summary")
def usage_summary(
    days: int = Query(30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_owner_or_admin = current_user.role in ("owner", "admin")
    user_id = None if is_owner_or_admin else current_user.id
    return get_usage_summary(db, user_id=user_id, days=days)


@router.get("/events")
def list_usage(
    event_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_owner_or_admin = current_user.role in ("owner", "admin")
    user_id = None if is_owner_or_admin else current_user.id
    return list_usage_events(db, user_id=user_id, event_type_filter=event_type, skip=skip, limit=limit)
