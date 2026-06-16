"""Phase 18 — First-run diagnostics endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.diagnostics import run_diagnostics

logger = logging.getLogger("officepilot.diagnostics_router")

router = APIRouter(prefix="/api/first-run", tags=["diagnostics"])


@router.get("/diagnostics")
def diagnostics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return run_diagnostics(db)
