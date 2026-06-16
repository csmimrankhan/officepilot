"""Phase 18 — Onboarding checklist endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.onboarding import complete_step, dismiss_onboarding, get_onboarding_status

logger = logging.getLogger("officepilot.onboarding_router")

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class CompleteStepBody(BaseModel):
    step: str


@router.get("/status")
def onboarding_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_onboarding_status(db, current_user.id)


@router.post("/complete-step")
def complete_onboarding_step(body: CompleteStepBody, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return complete_step(db, current_user.id, body.step)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dismiss")
def dismiss(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return dismiss_onboarding(db, current_user.id)


@router.get("/check-setup")
def check_setup(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from ..services.accountant_agent import get_agent_status
    from ..services.demo import is_demo_mode

    whisper_model_ready = False
    whisper_cli_found = False
    try:
        from ..services.windows_voice_layer import detect_whisper_status
        ws = detect_whisper_status()
        whisper_model_ready = ws.get("model_found", False)
        whisper_cli_found = ws.get("cli_found", False)
    except Exception:
        pass

    agent_status = get_agent_status()
    demo_status = is_demo_mode()

    return {
        "whisper_model_ready": whisper_model_ready,
        "whisper_cli_found": whisper_cli_found,
        "local_llm_reachable": agent_status.get("status") == "connected",
        "agent_provider": agent_status.get("provider", "mock"),
        "demo_data_seeded": demo_status,
        "onboarding_completed": current_user.onboarding_completed,
    }


class CompleteOnboardingBody(BaseModel):
    demo_data: bool = False


@router.post("/complete")
def complete_onboarding(body: CompleteOnboardingBody, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.onboarding_completed = True
    db.flush()
    db.commit()
    return {"ok": True, "onboarding_completed": True}
