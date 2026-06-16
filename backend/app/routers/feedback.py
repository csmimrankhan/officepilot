"""Phase 19 — Pilot feedback endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.feedback import (
    FEEDBACK_STATUSES,
    create_feedback,
    get_feedback,
    list_feedback,
    update_feedback,
)

logger = logging.getLogger("officepilot.feedback_router")

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class CreateFeedbackBody(BaseModel):
    feedback_type: str
    title: str
    message: str
    page_url: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    severity: str = "medium"


class UpdateFeedbackBody(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None


@router.post("")
def create_feedback_endpoint(
    body: CreateFeedbackBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return create_feedback(
            db,
            current_user.id,
            feedback_type=body.feedback_type,
            title=body.title,
            message=body.message,
            page_url=body.page_url,
            related_entity_type=body.related_entity_type,
            related_entity_id=body.related_entity_id,
            severity=body.severity,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_feedback_endpoint(
    status: Optional[str] = Query(None),
    feedback_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_owner_or_admin = current_user.role in ("owner", "admin")
    user_id = None if is_owner_or_admin else current_user.id
    return list_feedback(db, user_id=user_id, status_filter=status, feedback_type_filter=feedback_type, skip=skip, limit=limit)


@router.get("/{feedback_id}")
def get_feedback_endpoint(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_owner_or_admin = current_user.role in ("owner", "admin")
    user_id = None if is_owner_or_admin else current_user.id
    fb = get_feedback(db, feedback_id, user_id=user_id)
    if fb is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return fb


@router.patch("/{feedback_id}")
def update_feedback_endpoint(
    feedback_id: int,
    body: UpdateFeedbackBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_owner_or_admin = current_user.role in ("owner", "admin")
    user_id = None if is_owner_or_admin else current_user.id
    try:
        fb = update_feedback(db, feedback_id, user_id=user_id, status=body.status, severity=body.severity)
        if fb is None:
            raise HTTPException(status_code=404, detail="Feedback not found")
        return fb
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
