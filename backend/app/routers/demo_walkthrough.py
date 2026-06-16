"""Phase 19 — Guided demo walkthrough endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.demo_walkthrough import (
    WALKTHROUGH_STEPS,
    complete_step,
    dismiss_walkthrough,
    get_walkthrough_status,
    reset_walkthrough,
    skip_step,
    start_walkthrough,
)

logger = logging.getLogger("officepilot.demo_walkthrough_router")

router = APIRouter(prefix="/api/demo/walkthrough", tags=["demo-walkthrough"])


class CompleteStepBody(BaseModel):
    step: str


class SkipStepBody(BaseModel):
    step: str


@router.get("")
def walkthrough_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_walkthrough_status(db, current_user.id)


@router.post("/start")
def walkthrough_start(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return start_walkthrough(db, current_user.id)


@router.post("/complete-step")
def walkthrough_complete_step(
    body: CompleteStepBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return complete_step(db, current_user.id, body.step)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/skip-step")
def walkthrough_skip_step(
    body: SkipStepBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return skip_step(db, current_user.id, body.step)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset")
def walkthrough_reset(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return reset_walkthrough(db, current_user.id)


@router.post("/dismiss")
def walkthrough_dismiss(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return dismiss_walkthrough(db, current_user.id)
