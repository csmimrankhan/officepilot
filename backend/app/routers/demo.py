"""Phase 18 — Demo mode endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.demo import get_demo_status, get_sample_files, is_demo_mode, reset_demo_data, seed_demo_data
from ..services.permissions import check_permission

logger = logging.getLogger("officepilot.demo_router")

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/status")
def demo_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_demo_status(db)


@router.post("/seed")
def demo_seed(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_permission(db, current_user.role, "manage_safety_policies"):
        raise HTTPException(status_code=403, detail="Only owners can seed demo data")
    counts = seed_demo_data(db)
    logger.info("Demo data seeded: %s", counts)
    return {"ok": True, "counts": counts}


@router.post("/reset")
def demo_reset(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_permission(db, current_user.role, "manage_safety_policies"):
        raise HTTPException(status_code=403, detail="Only owners can reset demo data")
    counts = reset_demo_data(db)
    logger.info("Demo data reset: %s", counts)
    return {"ok": True, "counts": counts}


@router.get("/sample-files")
def sample_files(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"files": get_sample_files()}
