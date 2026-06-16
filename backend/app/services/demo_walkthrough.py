"""Phase 19 — Guided demo walkthrough service."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models.demo_walkthrough import DemoWalkthrough

logger = logging.getLogger("officepilot.demo_walkthrough")

WALKTHROUGH_STEPS = [
    {"step": "load_demo_data", "label": "Load sample data", "description": "Seed fake invoices and demo data"},
    {"step": "open_sample_invoice", "label": "Open sample invoice", "description": "View an extracted demo invoice"},
    {"step": "review_extracted_fields", "label": "Review extracted fields", "description": "Check vendor, amount, and confidence"},
    {"step": "approve_invoice", "label": "Approve invoice", "description": "Approve a sample invoice"},
    {"step": "export_to_excel", "label": "Export to Excel", "description": "Export approved invoices to Excel"},
    {"step": "view_excel_report", "label": "View Excel report", "description": "Review the exported Excel report"},
    {"step": "open_audit_log", "label": "Open audit log", "description": "View the audit trail of actions"},
    {"step": "restore_previous_version", "label": "Restore previous version", "description": "Restore a previous invoice version"},
    {"step": "open_readiness_dashboard", "label": "Open readiness dashboard", "description": "Check production readiness status"},
    {"step": "run_backup", "label": "Run backup", "description": "Create a local backup"},
    {"step": "activate_kill_switch", "label": "Activate and resume kill switch", "description": "Test the global automation kill switch"},
    {"step": "preview_accounting_sync", "label": "Preview QuickBooks/Xero sync", "description": "View accounting sync preview in demo mode"},
    {"step": "view_browser_automation", "label": "View browser automation test form", "description": "See the browser test form in action"},
    {"step": "view_workflow_recording", "label": "View workflow recording demo", "description": "Review a recorded workflow"},
    {"step": "view_screen_assistant", "label": "View screen assistant", "description": "Open the screen assistant in read-only mode"},
]


def get_or_create_walkthrough(db: Session, user_id: int) -> DemoWalkthrough:
    wt = db.query(DemoWalkthrough).filter(DemoWalkthrough.user_id == user_id).first()
    if wt is None:
        wt = DemoWalkthrough(
            user_id=user_id,
            status="not_started",
            current_step=0,
            completed_steps_json="[]",
            dismissed=False,
        )
        db.add(wt)
        db.flush()
    return wt


def get_walkthrough_status(db: Session, user_id: int) -> dict[str, Any]:
    wt = get_or_create_walkthrough(db, user_id)
    completed = json.loads(wt.completed_steps_json)
    total = len(WALKTHROUGH_STEPS)
    done = len(completed)
    return {
        "steps": WALKTHROUGH_STEPS,
        "status": wt.status,
        "current_step": wt.current_step,
        "completed_steps": completed,
        "progress_pct": round(done / total * 100) if total > 0 else 0,
        "started_at": wt.started_at.isoformat() if wt.started_at else None,
        "completed_at": wt.completed_at.isoformat() if wt.completed_at else None,
        "dismissed": wt.dismissed,
    }


def start_walkthrough(db: Session, user_id: int) -> dict[str, Any]:
    wt = get_or_create_walkthrough(db, user_id)
    if wt.status == "completed":
        # Reset first
        wt.status = "not_started"
        wt.current_step = 0
        wt.completed_steps_json = "[]"
        wt.started_at = None
        wt.completed_at = None
        wt.dismissed = False
    wt.status = "in_progress"
    wt.started_at = datetime.utcnow()
    wt.updated_at = datetime.utcnow()
    db.flush()
    db.commit()
    return get_walkthrough_status(db, user_id)


def complete_step(db: Session, user_id: int, step: str) -> dict[str, Any]:
    wt = get_or_create_walkthrough(db, user_id)
    if wt.status != "in_progress":
        raise ValueError("Walkthrough is not in progress")

    step_names = {s["step"] for s in WALKTHROUGH_STEPS}
    if step not in step_names:
        raise ValueError(f"Unknown step: {step}")

    completed = json.loads(wt.completed_steps_json)
    if step not in completed:
        completed.append(step)

    step_index = next(i for i, s in enumerate(WALKTHROUGH_STEPS) if s["step"] == step)
    wt.current_step = min(step_index + 1, len(WALKTHROUGH_STEPS) - 1)
    wt.completed_steps_json = json.dumps(completed)

    if len(completed) >= len(WALKTHROUGH_STEPS):
        wt.status = "completed"
        wt.completed_at = datetime.utcnow()

    wt.updated_at = datetime.utcnow()
    db.flush()
    db.commit()
    return get_walkthrough_status(db, user_id)


def skip_step(db: Session, user_id: int, step: str) -> dict[str, Any]:
    wt = get_or_create_walkthrough(db, user_id)
    if wt.status != "in_progress":
        raise ValueError("Walkthrough is not in progress")

    step_names = {s["step"] for s in WALKTHROUGH_STEPS}
    if step not in step_names:
        raise ValueError(f"Unknown step: {step}")

    step_index = next(i for i, s in enumerate(WALKTHROUGH_STEPS) if s["step"] == step)
    wt.current_step = min(step_index + 1, len(WALKTHROUGH_STEPS) - 1)
    wt.updated_at = datetime.utcnow()
    db.flush()
    db.commit()
    return get_walkthrough_status(db, user_id)


def reset_walkthrough(db: Session, user_id: int) -> dict[str, Any]:
    wt = get_or_create_walkthrough(db, user_id)
    wt.status = "not_started"
    wt.current_step = 0
    wt.completed_steps_json = "[]"
    wt.started_at = None
    wt.completed_at = None
    wt.dismissed = False
    wt.updated_at = datetime.utcnow()
    db.flush()
    db.commit()
    return get_walkthrough_status(db, user_id)


def dismiss_walkthrough(db: Session, user_id: int) -> dict[str, Any]:
    wt = get_or_create_walkthrough(db, user_id)
    wt.dismissed = True
    wt.updated_at = datetime.utcnow()
    db.flush()
    db.commit()
    return {"dismissed": True}
