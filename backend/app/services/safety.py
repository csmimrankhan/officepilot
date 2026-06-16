"""Phase 16B/17 — Safety policy management + persistent kill switch."""

from __future__ import annotations

import logging
import threading
from datetime import datetime

from sqlalchemy.orm import Session

from ..models.automation_safety_state import AutomationSafetyState
from ..models.safety_policy import SafetyPolicy

logger = logging.getLogger("officepilot.safety")

# ── Persistent kill switch ──

# In-memory event for fast checking; synced to DB on write and at startup.
_kill_switch = threading.Event()


def _sync_from_db(db: Session) -> None:
    state = db.query(AutomationSafetyState).first()
    if state and state.kill_switch_active:
        _kill_switch.set()
    else:
        _kill_switch.clear()


def init_kill_switch(db: Session) -> None:
    _sync_from_db(db)


def is_kill_switch_active() -> bool:
    return _kill_switch.is_set()


def activate_kill_switch(db: Session, activated_by: str = "", reason: str = "") -> list[str]:
    now = datetime.utcnow()
    state = db.query(AutomationSafetyState).first()
    if state is None:
        state = AutomationSafetyState()
        db.add(state)

    state.kill_switch_active = True
    state.reason = reason
    state.activated_by = activated_by
    state.activated_at = now
    state.updated_at = now
    db.flush()

    _kill_switch.set()
    logger.warning("KILL SWITCH ACTIVATED by %s: %s", activated_by, reason)
    return _disabled_services_list()


def deactivate_kill_switch(db: Session, resumed_by: str = "") -> list[str]:
    now = datetime.utcnow()
    state = db.query(AutomationSafetyState).first()
    if state:
        state.kill_switch_active = False
        state.resumed_by = resumed_by
        state.resumed_at = now
        state.updated_at = now
        db.flush()

    _kill_switch.clear()
    logger.info("Kill switch deactivated by %s", resumed_by)
    return _disabled_services_list()


def get_kill_switch_state(db: Session) -> dict:
    state = db.query(AutomationSafetyState).first()
    if state is None:
        return {
            "kill_switch_active": False,
            "reason": "",
            "activated_by": "",
            "activated_at": None,
            "resumed_by": "",
            "resumed_at": None,
        }
    return {
        "kill_switch_active": state.kill_switch_active,
        "reason": state.reason,
        "activated_by": state.activated_by,
        "activated_at": state.activated_at.isoformat() if state.activated_at else None,
        "resumed_by": state.resumed_by,
        "resumed_at": state.resumed_at.isoformat() if state.resumed_at else None,
    }


def _disabled_services_list() -> list[str]:
    return [
        "browser_automation",
        "screen_control",
        "workflow_recording",
        "accounting_sync",
    ]


def check_kill_switch_blocked(service: str) -> bool:
    return is_kill_switch_active() and service in _disabled_services_list()


# ── Safety policy CRUD ──


def get_or_create_safety_policy(db: Session) -> SafetyPolicy:
    policy = db.query(SafetyPolicy).first()
    if policy is None:
        policy = SafetyPolicy()
        db.add(policy)
        db.flush()
    return policy


def update_safety_policy(db: Session, updates: dict) -> SafetyPolicy:
    policy = get_or_create_safety_policy(db)
    allowed_fields = {
        "cloud_ai_allowed", "browser_automation_enabled", "screen_control_enabled",
        "workflow_recording_enabled", "accounting_sync_enabled", "voice_enabled",
        "screenshots_enabled", "ocr_enabled", "require_approval_for_write",
        "require_snapshot_for_file_changes", "block_unknown_apps", "block_unknown_domains",
    }
    for key, value in updates.items():
        if key in allowed_fields and value is not None:
            setattr(policy, key, value)
    policy.updated_at = datetime.utcnow()
    db.flush()
    return policy
