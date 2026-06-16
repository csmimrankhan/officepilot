"""Phase 19 — Pilot readiness checklist service."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models.pilot_readiness import PilotReadiness

logger = logging.getLogger("officepilot.pilot_readiness")

READINESS_CHECKLIST = [
    {"step": "owner_account_created", "label": "First owner account created", "optional": False},
    {"step": "demo_data_loaded", "label": "Demo data loaded", "optional": False},
    {"step": "sample_invoice_approved", "label": "Sample invoice approved", "optional": False},
    {"step": "excel_export_tested", "label": "Excel export tested", "optional": False},
    {"step": "audit_log_viewed", "label": "Audit log viewed", "optional": False},
    {"step": "backup_tested", "label": "Backup tested", "optional": False},
    {"step": "kill_switch_tested", "label": "Kill switch tested", "optional": False},
    {"step": "readiness_reviewed", "label": "Readiness dashboard green/yellow reviewed", "optional": False},
    {"step": "feedback_tested", "label": "Feedback button tested", "optional": False},
    {"step": "bug_report_tested", "label": "Bug report tested", "optional": True},
]


def get_or_create_readiness(db: Session, user_id: int) -> PilotReadiness:
    pr = db.query(PilotReadiness).filter(PilotReadiness.user_id == user_id).first()
    if pr is None:
        pr = PilotReadiness(
            user_id=user_id,
            checklist_json=json.dumps(READINESS_CHECKLIST),
            completed_steps_json="[]",
            dismissed=False,
        )
        db.add(pr)
        db.flush()
    return pr


def get_readiness_status(db: Session, user_id: int) -> dict[str, Any]:
    pr = get_or_create_readiness(db, user_id)
    checklist = json.loads(pr.checklist_json)
    completed = json.loads(pr.completed_steps_json)
    total = len(checklist)
    done = len(completed)
    required = [s for s in checklist if not s["optional"]]
    required_done = [s for s in required if s["step"] in completed]
    ready = len(required_done) >= len(required) if required else False
    return {
        "checklist": checklist,
        "completed_steps": completed,
        "progress_pct": round(done / total * 100) if total > 0 else 0,
        "ready_for_pilot": ready,
        "required_total": len(required),
        "required_completed": len(required_done),
    }


def complete_readiness_step(db: Session, user_id: int, step: str) -> dict[str, Any]:
    pr = get_or_create_readiness(db, user_id)
    checklist = json.loads(pr.checklist_json)
    completed = json.loads(pr.completed_steps_json)

    step_names = {s["step"] for s in checklist}
    if step not in step_names:
        raise ValueError(f"Unknown readiness step: {step}")

    if step not in completed:
        completed.append(step)

    pr.completed_steps_json = json.dumps(completed)
    pr.updated_at = datetime.utcnow()
    db.flush()
    db.commit()
    return get_readiness_status(db, user_id)


def reset_readiness(db: Session, user_id: int) -> dict[str, Any]:
    pr = get_or_create_readiness(db, user_id)
    pr.completed_steps_json = "[]"
    pr.updated_at = datetime.utcnow()
    db.flush()
    db.commit()
    return get_readiness_status(db, user_id)
