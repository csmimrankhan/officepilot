"""Phase 18 — Onboarding checklist service."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models.onboarding_state import OnboardingState

logger = logging.getLogger("officepilot.onboarding")

DEFAULT_CHECKLIST = [
    {"step": "create_owner", "label": "Create owner account", "optional": False},
    {"step": "confirm_agent", "label": "Confirm local agent is online", "optional": False},
    {"step": "load_demo_data", "label": "Load sample data", "optional": False},
    {"step": "upload_invoice", "label": "Upload your first invoice", "optional": False},
    {"step": "review_invoice", "label": "Review an extracted invoice", "optional": False},
    {"step": "approve_invoice", "label": "Approve an invoice", "optional": False},
    {"step": "export_excel", "label": "Export to Excel", "optional": False},
    {"step": "view_audit_log", "label": "View the audit log", "optional": False},
    {"step": "run_backup", "label": "Run a backup", "optional": False},
    {"step": "check_readiness", "label": "Check readiness dashboard", "optional": False},
    {"step": "connect_gmail", "label": "Connect Gmail (optional)", "optional": True},
    {"step": "connect_accounting", "label": "Connect QuickBooks/Xero sandbox (optional)", "optional": True},
]


def get_or_create_onboarding(db: Session, user_id: int) -> OnboardingState:
    state = db.query(OnboardingState).filter(OnboardingState.user_id == user_id).first()
    if state is None:
        state = OnboardingState(
            user_id=user_id,
            checklist_json=json.dumps(DEFAULT_CHECKLIST),
            completed_steps_json="[]",
            dismissed=False,
        )
        db.add(state)
        db.flush()
    return state


def get_onboarding_status(db: Session, user_id: int) -> dict[str, Any]:
    state = get_or_create_onboarding(db, user_id)
    checklist = json.loads(state.checklist_json)
    completed = json.loads(state.completed_steps_json)
    total = len(checklist)
    done = len(completed)
    return {
        "checklist": checklist,
        "completed_steps": completed,
        "progress_pct": round(done / total * 100) if total > 0 else 0,
        "dismissed": state.dismissed,
    }


def complete_step(db: Session, user_id: int, step: str) -> dict[str, Any]:
    state = get_or_create_onboarding(db, user_id)
    checklist = json.loads(state.checklist_json)
    completed = json.loads(state.completed_steps_json)

    step_names = {s["step"] for s in checklist}
    if step not in step_names:
        raise ValueError(f"Unknown step: {step}")

    if step not in completed:
        completed.append(step)

    state.completed_steps_json = json.dumps(completed)
    state.updated_at = datetime.utcnow()
    db.flush()
    db.commit()

    return get_onboarding_status(db, user_id)


def dismiss_onboarding(db: Session, user_id: int) -> dict[str, Any]:
    state = get_or_create_onboarding(db, user_id)
    state.dismissed = True
    state.updated_at = datetime.utcnow()
    db.flush()
    db.commit()
    return {"dismissed": True}
