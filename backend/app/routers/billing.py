"""Phase 35 — License status, plans, billing checkout placeholders."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.app_update import get_license_status, get_plans

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str = "pro"
    success_url: str | None = None
    cancel_url: str | None = None


@router.get("/license")
def license_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_license_status(db, current_user.id)


@router.get("/plans")
def list_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"plans": get_plans()}


@router.post("/start-checkout")
def start_checkout(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info("Checkout started: user=%s plan=%s", current_user.email, body.plan)
    return {
        "checkout_url": None,
        "message": "Billing checkout is not yet configured. Contact officepilot.ai for subscription management.",
        "plan": body.plan,
    }


@router.post("/manage")
def manage_billing(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "portal_url": None,
        "message": "Billing management is not yet configured. Contact officepilot.ai for subscription management.",
    }
