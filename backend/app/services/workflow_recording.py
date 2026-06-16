"""Phase 14 — workflow recording and replay service.

Handles the complete workflow recording lifecycle: starting/stopping
recording sessions, capturing and redacting events, converting raw
events into workflow steps, saving recordings as replayable workflows,
and managing replay runs (dry-run and step-by-step) with approval
workflow.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.recorded_workflow import RecordedWorkflow
from ..models.recorded_workflow_step import RecordedWorkflowStep
from ..models.workflow_recording_policy import WorkflowRecordingPolicy, DEFAULT_ALLOWED_DOMAINS, DEFAULT_BLOCKED_DOMAINS
from ..models.workflow_recording_session import WorkflowRecordingSession
from ..models.workflow_replay_run import WorkflowReplayRun
from ..models.workflow_replay_step_log import WorkflowReplayStepLog
from ..services.audit import log_action

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SENSITIVE_PATTERNS = ["password", "token", "secret", "api_key", "card", "cvv", "bank", "otp", "2fa", "ssn", "pin"]
SENSITIVE_INPUT_TYPES = ["password", "token", "secret", "api_key", "cvv", "ssn", "pin", "bank_account"]
RISK_LEVELS = {"low", "medium", "high"}
REQUIRE_APPROVAL_STEP_TYPES = {
    "fill_form_field", "click_button", "run_business_action",
    "run_browser_action", "run_accounting_preview",
    "paste_text", "hotkey",
}
WRITE_STEP_TYPES = {"fill_form_field", "click_button", "type_text", "paste_text", "hotkey"}


# ---------------------------------------------------------------------------
# Recording session lifecycle
# ---------------------------------------------------------------------------


def start_recording(db: Session, created_by: str = "user") -> dict:
    """Create a new recording session."""
    session = WorkflowRecordingSession(
        status="recording",
        started_at=datetime.utcnow(),
        created_by=created_by,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "session_id": session.id,
        "status": session.status,
    }


def stop_recording(db: Session, session_id: int) -> dict:
    """Stop a recording session."""
    session = db.get(WorkflowRecordingSession, session_id)
    if session is None:
        raise ValueError("Recording session not found")
    session.status = "stopped"
    session.stopped_at = datetime.utcnow()
    db.commit()
    return {
        "session_id": session.id,
        "status": session.status,
        "event_count": session.event_count,
    }


# ---------------------------------------------------------------------------
# Event capture and redaction
# ---------------------------------------------------------------------------


def capture_event(db: Session, session_id: int, event: dict) -> dict:
    """Capture a raw event into the recording session."""
    session = db.get(WorkflowRecordingSession, session_id)
    if session is None:
        raise ValueError("Recording session not found")
    if session.status != "recording":
        raise ValueError(f"Recording session is not recording (status={session.status})")

    raw_value = event.get("input_value", "")
    redacted_value = _redact_sensitive(raw_value)
    was_redacted = redacted_value != raw_value

    session.event_count = (session.event_count or 0) + 1
    if was_redacted:
        session.contains_sensitive_redactions = True

    # Accumulate raw events as JSON array
    import json
    current = json.loads(session.raw_events_json or "[]")
    current.append(event)
    session.raw_events_json = json.dumps(current, default=str)

    db.commit()

    return {
        "captured": True,
        "redacted": was_redacted,
        "event_index": session.event_count,
    }


def _redact_sensitive(value: str) -> str:
    """Redact sensitive input values.

    Currently returns ``[REDACTED]`` for any non-empty value.
    Future versions may inspect the value against
    :data:`SENSITIVE_PATTERNS` more selectively.
    """
    if not value:
        return value
    return "[REDACTED]"


# ---------------------------------------------------------------------------
# Event-to-step conversion
# ---------------------------------------------------------------------------


_EVENT_TYPE_TO_STEP_TYPE: dict[str, str] = {
    "window_focus": "wait_for_window",
    "open_url": "open_url",
    "open_file": "open_file",
    "open_folder": "open_folder",
    "click": "click_element",
    "type_text": "type_text",
    "hotkey": "hotkey",
    "copy": "copy_text",
    "paste": "paste_text",
    "wait": "wait_for_window",
    "browser_fill_field": "fill_form_field",
    "browser_click_button": "click_button",
    "invoicepilot_action": "run_business_action",
    "approval_checkpoint": "approval_checkpoint",
    "screenshot_checkpoint": "validation_checkpoint",
}


def _convert_event_to_step(event: dict, order: int) -> dict:
    """Convert a raw event dict into a workflow step dict.

    Returns a dictionary whose keys match the columns of
    :class:`RecordedWorkflowStep` (excluding ``id``,
    ``workflow_id`` and ``created_at``).
    """
    event_type = event.get("event_type", "")
    step_type = _EVENT_TYPE_TO_STEP_TYPE.get(event_type, event_type)

    input_value = event.get("input_value", "")
    redacted = _redact_sensitive(input_value)

    risk_level, requires_approval = classify_step_risk(step_type, event)

    return {
        "step_order": order,
        "step_type": step_type,
        "app_name": event.get("app_name", ""),
        "window_title": event.get("window_title", ""),
        "target_description": event.get("target_description", "") or event.get("target", ""),
        "selector_json": event.get("selector_json", {}) or {},
        "ui_automation_json": event.get("ui_automation_json", {}) or {},
        "fallback_coordinates_json": event.get("fallback_coordinates_json", {}) or {},
        "input_value_redacted": redacted,
        "expected_result_json": event.get("expected_result_json", {}) or {},
        "requires_approval": requires_approval,
        "risk_level": risk_level,
        "enabled": True,
    }


def convert_raw_events_to_steps(db: Session, session_id: int) -> list[dict]:
    """Convert all raw events in a session to workflow step dicts."""
    session = db.get(WorkflowRecordingSession, session_id)
    if session is None:
        raise ValueError("Recording session not found")

    import json
    raw_events = json.loads(session.raw_events_json or "[]")

    steps = []
    for idx, event in enumerate(raw_events):
        step = _convert_event_to_step(event, idx + 1)
        steps.append(step)

    return steps


# ---------------------------------------------------------------------------
# Save recording as workflow
# ---------------------------------------------------------------------------


def save_recording_as_workflow(db: Session, session_id: int, name: str, description: str = "") -> dict:
    """Save a recording session as a replayable workflow."""
    session = db.get(WorkflowRecordingSession, session_id)
    if session is None:
        raise ValueError("Recording session not found")

    workflow = RecordedWorkflow(
        name=name,
        description=description,
        source_type="recording",
        created_by=session.created_by,
    )
    db.add(workflow)
    db.flush()

    steps = convert_raw_events_to_steps(db, session_id)
    for step_data in steps:
        step = RecordedWorkflowStep(
            workflow_id=workflow.id,
            **step_data,
        )
        db.add(step)

    db.flush()

    total = len(steps)
    workflow.total_steps = total

    session.workflow_id = workflow.id
    session.status = "saved"

    log_action(
        db,
        actor=session.created_by,
        action="workflow_recording.save",
        entity_type="recorded_workflow",
        entity_id=workflow.id,
        details=f"Saved recording session #{session_id} as workflow '{name}' with {total} steps",
        after_data={"session_id": session_id, "total_steps": total},
    )

    db.commit()
    db.refresh(workflow)

    return {
        "workflow_id": workflow.id,
        "name": workflow.name,
        "total_steps": total,
    }


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------


def classify_step_risk(step_type: str, step_data: dict) -> tuple[str, bool]:
    """Classify a step's risk level and whether it requires approval.

    Returns ``(risk_level, requires_approval)``.

    * "high" — write/submit steps that modify external state.
    * "medium" — form-filling and text-input steps.
    * "low" — navigation and read-only steps.
    """
    target = (step_data.get("target_description") or step_data.get("target") or "").lower()

    if step_type in ("click_button", "run_business_action", "run_browser_action", "run_accounting_preview"):
        return ("high", True)

    if "submit" in target or "save" in target:
        return ("high", True)

    if step_type in ("fill_form_field", "paste_text", "hotkey", "type_text"):
        return ("medium", True)

    return ("low", False)


# ---------------------------------------------------------------------------
# Blocklist helpers
# ---------------------------------------------------------------------------


def blocked_app_check(app_name: str, blocked_apps: list[str]) -> bool:
    """Check whether *app_name* matches any entry in *blocked_apps*.

    Matching is case-insensitive substring containment with
    underscore/space normalization so ``password_manager``
    matches ``Password Manager Pro``.
    """
    app_lower = app_name.lower().replace(" ", "_")
    return any(pattern.lower() in app_lower for pattern in blocked_apps)


def blocked_domain_check(url: str, blocked_domains: list[str]) -> bool:
    """Check whether the hostname of *url* matches any blocked domain.

    Matching is case-insensitive substring containment.
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
    except Exception:
        hostname = url

    hostname_lower = hostname.lower()
    return any(domain.lower() in hostname_lower for domain in blocked_domains)


# ---------------------------------------------------------------------------
# Replay lifecycle
# ---------------------------------------------------------------------------


def start_dry_run(db: Session, workflow_id: int) -> dict:
    """Start a dry-run replay of *workflow_id*.

    All steps are logged with ``status="pending"`` and no actual
    execution occurs — the run exists purely for preview.
    """
    workflow = db.get(RecordedWorkflow, workflow_id)
    if workflow is None:
        raise ValueError("Workflow not found")

    steps = (
        db.query(RecordedWorkflowStep)
        .filter(
            RecordedWorkflowStep.workflow_id == workflow_id,
            RecordedWorkflowStep.enabled == True,
        )
        .order_by(RecordedWorkflowStep.step_order)
        .all()
    )

    run = WorkflowReplayRun(
        workflow_id=workflow_id,
        mode="dry_run",
        status="running",
    )
    db.add(run)
    db.flush()

    for step in steps:
        preview = build_action_preview(step)
        step_log = WorkflowReplayStepLog(
            replay_run_id=run.id,
            step_id=step.id,
            step_order=step.step_order,
            step_type=step.step_type,
            status="pending",
            action_preview_json=preview,
        )
        db.add(step_log)

    log_action(
        db,
        actor="system",
        action="workflow_replay.start_dry_run",
        entity_type="recorded_workflow",
        entity_id=workflow_id,
        details=f"Started dry-run replay of workflow '{workflow.name}' ({len(steps)} steps)",
    )

    db.commit()
    db.refresh(run)

    return {
        "run_id": run.id,
        "mode": run.mode,
        "total_steps": len(steps),
    }


def start_step_by_step_replay(db: Session, workflow_id: int) -> dict:
    """Start a step-by-step replay of *workflow_id*.

    Each step must be individually approved before execution.
    """
    workflow = db.get(RecordedWorkflow, workflow_id)
    if workflow is None:
        raise ValueError("Workflow not found")

    steps = (
        db.query(RecordedWorkflowStep)
        .filter(
            RecordedWorkflowStep.workflow_id == workflow_id,
            RecordedWorkflowStep.enabled == True,
        )
        .order_by(RecordedWorkflowStep.step_order)
        .all()
    )

    run = WorkflowReplayRun(
        workflow_id=workflow_id,
        mode="step_by_step",
        status="running",
    )
    db.add(run)
    db.flush()

    first_step_preview = None
    for step in steps:
        preview = build_action_preview(step)
        if first_step_preview is None:
            first_step_preview = preview
        step_log = WorkflowReplayStepLog(
            replay_run_id=run.id,
            step_id=step.id,
            step_order=step.step_order,
            step_type=step.step_type,
            status="pending",
            action_preview_json=preview,
        )
        db.add(step_log)

    log_action(
        db,
        actor="system",
        action="workflow_replay.start_step_by_step",
        entity_type="recorded_workflow",
        entity_id=workflow_id,
        details=f"Started step-by-step replay of workflow '{workflow.name}' ({len(steps)} steps)",
    )

    db.commit()
    db.refresh(run)

    return {
        "run_id": run.id,
        "mode": run.mode,
        "total_steps": len(steps),
        "first_step_preview": first_step_preview,
    }


# ---------------------------------------------------------------------------
# Step-level approval
# ---------------------------------------------------------------------------


def approve_step(db: Session, run_id: int, step_log_id: int) -> dict:
    """Approve a single step in a replay run."""
    step_log = db.get(WorkflowReplayStepLog, step_log_id)
    if step_log is None:
        raise ValueError("Step log not found")
    if step_log.replay_run_id != run_id:
        raise ValueError("Step log does not belong to the specified run")

    step_log.status = "approved"
    db.commit()
    db.refresh(step_log)

    # Look up the associated workflow step for approval/risk info
    workflow_step = db.get(RecordedWorkflowStep, step_log.step_id)

    return {
        "step_log_id": step_log.id,
        "step_order": step_log.step_order,
        "step_type": step_log.step_type,
        "status": step_log.status,
        "action_preview": step_log.action_preview_json or {},
        "requires_approval": workflow_step.requires_approval if workflow_step else True,
        "risk_level": workflow_step.risk_level if workflow_step else "medium",
    }


def reject_step(db: Session, run_id: int, step_log_id: int) -> dict:
    """Reject a single step and stop the replay run."""
    step_log = db.get(WorkflowReplayStepLog, step_log_id)
    if step_log is None:
        raise ValueError("Step log not found")
    if step_log.replay_run_id != run_id:
        raise ValueError("Step log does not belong to the specified run")

    step_log.status = "rejected"

    run = db.get(WorkflowReplayRun, run_id)
    if run is not None:
        run.status = "stopped"

    db.commit()

    return {
        "step_log_id": step_log.id,
        "step_order": step_log.step_order,
        "step_type": step_log.step_type,
        "stopped": True,
        "run_id": run_id,
        "status": step_log.status,
        "run_status": "stopped",
    }


# ---------------------------------------------------------------------------
# Run-level controls
# ---------------------------------------------------------------------------


def pause_replay(db: Session, run_id: int):
    """Pause a running replay."""
    run = db.get(WorkflowReplayRun, run_id)
    if run is None:
        raise ValueError("Replay run not found")
    run.status = "paused"
    db.commit()


def resume_replay(db: Session, run_id: int):
    """Resume a paused replay."""
    run = db.get(WorkflowReplayRun, run_id)
    if run is None:
        raise ValueError("Replay run not found")
    run.status = "running"
    db.commit()


def emergency_stop(db: Session, run_id: int, stopped_by: str = "user") -> dict:
    """Immediately stop a replay and skip all pending steps."""
    run = db.get(WorkflowReplayRun, run_id)
    if run is None:
        raise ValueError("Replay run not found")

    run.status = "stopped"
    run.completed_at = datetime.utcnow()
    run.stopped_by = stopped_by

    pending_logs = (
        db.query(WorkflowReplayStepLog)
        .filter(
            WorkflowReplayStepLog.replay_run_id == run_id,
            WorkflowReplayStepLog.status == "pending",
        )
        .all()
    )
    for log_entry in pending_logs:
        log_entry.status = "skipped"

    log_action(
        db,
        actor=stopped_by,
        action="workflow_replay.emergency_stop",
        entity_type="workflow_replay_run",
        entity_id=run_id,
        details=f"Emergency stop by {stopped_by}; {len(pending_logs)} pending steps skipped",
    )

    db.commit()

    return {
        "stopped": True,
        "run_id": run_id,
        "status": run.status,
    }


# ---------------------------------------------------------------------------
# Preview and validation
# ---------------------------------------------------------------------------


def build_action_preview(step) -> dict:
    """Build a safe preview dict for a workflow step.

    *step* can be a :class:`RecordedWorkflowStep` ORM instance or a
    plain dict with matching keys.
    """
    if isinstance(step, dict):
        step_type = step.get("step_type", "")
        target_description = step.get("target_description", "")
        input_value_redacted = step.get("input_value_redacted", "")
        app_name = step.get("app_name", "")
        risk_level = step.get("risk_level", "low")
        requires_approval = step.get("requires_approval", False)
    else:
        step_type = getattr(step, "step_type", "")
        target_description = getattr(step, "target_description", "")
        input_value_redacted = getattr(step, "input_value_redacted", "")
        app_name = getattr(step, "app_name", "")
        risk_level = getattr(step, "risk_level", "low")
        requires_approval = getattr(step, "requires_approval", False)

    warning = ""
    if risk_level == "high":
        warning = "This step has been classified as high-risk and requires manual approval before execution."
    elif risk_level == "medium" and requires_approval:
        warning = "This step modifies data and requires approval before execution."

    return {
        "step_type": step_type,
        "target_description": target_description,
        "input_value_redacted": input_value_redacted,
        "app_name": app_name,
        "risk_level": risk_level,
        "requires_approval": requires_approval,
        "warning": warning,
    }


def validate_step_result(step_log_id: int, result_data: dict) -> bool:
    """Validate a completed step's result.

    .. note:: This is a stub. The real implementation will compare
              *result_data* against the step's
              ``expected_result_json`` and return ``True`` only if
              they match within tolerance.
    """
    return True


# ---------------------------------------------------------------------------
# Policy helpers
# ---------------------------------------------------------------------------


def _default_policy() -> dict:
    """Return a dict of default policy values."""
    return {
        "recording_enabled": False,
        "screenshots_enabled": False,
        "redact_sensitive_inputs": True,
        "allowed_apps_json": [],
        "blocked_apps_json": [],
        "allowed_domains_json": list(DEFAULT_ALLOWED_DOMAINS),
        "blocked_domains_json": list(DEFAULT_BLOCKED_DOMAINS),
        "require_approval_for_replay": True,
        "require_approval_for_submit": True,
        "require_approval_for_write": True,
        "notes": "",
    }


def get_or_create_policy(db: Session) -> WorkflowRecordingPolicy:
    """Return the singleton policy row, creating a default if absent."""
    policy = db.query(WorkflowRecordingPolicy).first()
    if policy is None:
        defaults = _default_policy()
        policy = WorkflowRecordingPolicy(**defaults)
        db.add(policy)
        db.commit()
        db.refresh(policy)
    return policy
