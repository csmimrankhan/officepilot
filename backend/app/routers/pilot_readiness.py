"""Phase 19 — Pilot readiness checklist endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.pilot_readiness import (
    complete_readiness_step,
    get_readiness_status,
    reset_readiness,
)

logger = logging.getLogger("officepilot.pilot_readiness_router")

router = APIRouter(prefix="/api/pilot/readiness", tags=["pilot-readiness"])


class CompleteStepBody(BaseModel):
    step: str


@router.get("")
def readiness_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_readiness_status(db, current_user.id)


@router.post("/complete-step")
def readiness_complete_step(
    body: CompleteStepBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return complete_readiness_step(db, current_user.id, body.step)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset")
def readiness_reset(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return reset_readiness(db, current_user.id)
