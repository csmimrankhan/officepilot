"""Phase 33 — Workflow Recorder MVP Service.

Builds on Phase 14 recording infrastructure with:
- User-scoped recording sessions
- Proper event persistence (WorkflowRecordedEvent rows)
- Sensitive-input redaction
- Convert events to skill draft
- Approve / reject / save skill drafts
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models.accounting_skill import AccountingSkill, AccountingSkillRun
from ..models.accounting_skill_version import AccountingSkillVersion
from ..models.workflow_recorded_event import WorkflowRecordedEvent, EVENT_TYPES
from ..models.workflow_recording_session import WorkflowRecordingSession, SESSION_STATUSES, SESSION_SOURCES
from ..models.workflow_skill_draft import WorkflowSkillDraft, DRAFT_STATUSES
from ..services.audit import log_action

logger = logging.getLogger(__name__)

# Patterns for sensitive field detection
SENSITIVE_FIELD_PATTERNS = re.compile(
    r"(password|passwd|pwd|otp|2fa|token|secret|api[_-]?key|card[_-]?number"
    r"|cvv|cvc|ssn|pin|bank[_-]?account|routing[_-]?number)",
    re.IGNORECASE,
)
SENSITIVE_VALUE_PATTERNS = re.compile(
    r"^[\s]*("
    r"[A-Za-z0-9+/]{40,}(?:[=]{0,2})?"  # potential token/key
    r"|\d{16}"                            # 16-digit card number
    r"|\d{3,4}"                           # CVV
    r"|\d{9}"                             # SSN / routing
    r")[\s]*$",
)
REDACTED_PLACEHOLDER = "[REDACTED]"

SAFE_EVENT_TYPES = frozenset({
    "app_focus", "window_title_change", "browser_url_open",
    "browser_url_change", "click", "type_text", "hotkey",
    "file_open", "file_select", "folder_open", "download_detected",
    "wait", "manual_login_checkpoint", "guided_export_checkpoint",
    "screenshot", "copy", "paste", "approval_checkpoint",
    "manual_event",
})

EVENT_TYPE_TO_SKILL_TOOL: dict[str, str] = {
    "browser_url_open": "browser_open_url",
    "browser_url_change": "browser_open_url",
    "manual_login_checkpoint": "browser_wait_for_user_login",
    "guided_export_checkpoint": "browser_export_report",
    "download_detected": "file_find_latest_download",
    "file_open": "file_open",
    "file_select": "file_open",
    "folder_open": "file_open_folder",
    "type_text": "desktop_type",
    "click": "desktop_click",
    "hotkey": "desktop_hotkey",
    "copy": "desktop_copy",
    "paste": "desktop_paste",
    "wait": "desktop_wait",
    "app_focus": "desktop_open_app",
    "screenshot": "screen_capture",
    "approval_checkpoint": "approval_request",
    "manual_event": "validate_result",
}

STEP_TYPE_TO_EVENT_TYPE: dict[str, str] = {v: k for k, v in EVENT_TYPE_TO_SKILL_TOOL.items()}


def _redact_value(label: str, value: str) -> str:
    if not value:
        return value
    if SENSITIVE_FIELD_PATTERNS.search(label or ""):
        return REDACTED_PLACEHOLDER
    if SENSITIVE_VALUE_PATTERNS.match(value.strip()):
        return REDACTED_PLACEHOLDER
    return value


def _compute_risk(event_type: str, label: str) -> tuple[str, bool]:
    if event_type in ("manual_login_checkpoint", "guided_export_checkpoint", "approval_checkpoint"):
        return ("low", False)
    if event_type in ("click", "type_text", "hotkey", "copy", "paste"):
        return ("medium", True)
    if event_type in ("file_open", "file_select", "download_detected"):
        return ("medium", True)
    return ("low", False)


def _event_to_skill_step(event: WorkflowRecordedEvent, order: int) -> dict:
    tool = EVENT_TYPE_TO_SKILL_TOOL.get(event.event_type, "validate_result")
    risk, needs_approval = _compute_risk(event.event_type, event.label)
    params: dict[str, Any] = {}
    if event.browser_url:
        params["url"] = event.browser_url
    if event.file_path:
        params["file_path"] = event.file_path
    if event.text_value_redacted and event.text_value_redacted != REDACTED_PLACEHOLDER:
        params["text"] = event.text_value_redacted
    if event.app_name:
        params["app_name"] = event.app_name

    return {
        "step_order": order,
        "step_type": tool,
        "tool": tool,
        "target": event.label or event.app_name or event.event_type,
        "instruction": f"Execute {tool} on {event.label or event.app_name or event.event_type}",
        "expected_result": f"{tool} completed",
        "requires_approval": needs_approval,
        "risk_level": risk,
        "parameters": params,
    }


def _generate_trigger_phrases(events: list[WorkflowRecordedEvent], session_title: str) -> list[str]:
    phrases = []
    if session_title:
        phrases.append(session_title.strip().lower())
    app_names = list({e.app_name for e in events if e.app_name})
    if app_names:
        phrases.append(f"run {app_names[0].lower()} workflow")
        phrases.append(f"start {app_names[0].lower()} workflow")
    phrases.append("run recorded workflow")
    phrases.append("start recorded workflow")
    return phrases


def _generate_skill_name(events: list[WorkflowRecordedEvent], session_title: str) -> str:
    """Generate a descriptive skill name from recorded events.
    
    Uses the LLM provider (mock/cloud/local) if available, otherwise
    falls back to heuristic-based naming.
    """
    if session_title:
        return session_title.strip()

    # Heuristic-based name from event patterns
    app_names = [e.app_name for e in events if e.app_name]
    event_types = set(e.event_type for e in events)
    browser_events = {t for t in event_types if t.startswith("browser_")}
    excel_events = {t for t in event_types if "excel" in t.lower() or "file" in t.lower()}

    parts = []
    if excel_events:
        parts.append("Excel")
    if browser_events:
        parts.append("Browser")
    if app_names:
        parts.append(app_names[0])

    if parts:
        return f"Recorded {' '.join(parts)} Workflow"

    return "Recorded Workflow"


def _generate_skill_name_llm(events: list[WorkflowRecordedEvent], session_title: str, user_language: str = "en") -> str:
    """Use the LLM provider to generate a descriptive skill name.
    
    Falls back to heuristic naming if LLM is unavailable.
    """
    try:
        from .accountant_agent import _call_local_provider, _mock_agent_response
        provider = os.environ.get("AGENT_PROVIDER", "mock")
        app_names = [e.app_name for e in events if e.app_name]
        event_types = list({e.event_type for e in events})

        prompt = (
            f"Generate a short, descriptive skill name (max 5 words) for a recorded workflow. "
            f"The recording has these action types: {', '.join(event_types[:10])}. "
            f"The applications used were: {', '.join(app_names[:5])}. "
            f"Respond with ONLY the name, no quotes, no explanation."
        )

        if provider == "local":
            response = _call_local_provider(prompt)
            name = response.strip().strip('"\'').strip()
            if name and len(name) < 60:
                return name
        elif provider in ("openai_compatible", "deepseek"):
            from .accountant_agent import _call_cloud_provider
            response = _call_cloud_provider(prompt, None, provider)
            name = response.strip().strip('"\'').strip()
            if name and len(name) < 60:
                return name

        return _generate_skill_name(events, session_title)
    except Exception:
        return _generate_skill_name(events, session_title)


def _extract_safety_rules(events: list[WorkflowRecordedEvent]) -> dict:
    has_high = any(_compute_risk(e.event_type, e.label)[0] == "high" for e in events)
    has_medium = any(_compute_risk(e.event_type, e.label)[0] == "medium" for e in events)
    approval_required = has_high or has_medium
    return {
        "requires_dry_run": True,
        "approval_required": approval_required,
        "max_risk_level": "high" if has_high else ("medium" if has_medium else "low"),
    }


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


def start_recording_session(
    db: Session,
    user_id: int,
    title: str = "",
    source: str = "manual",
) -> dict:
    session = WorkflowRecordingSession(
        user_id=user_id,
        status="recording",
        title=title or f"Recording {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        source=source if source in SESSION_SOURCES else "manual",
        started_at=datetime.utcnow(),
        created_by=str(user_id),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    log_action(db, actor=str(user_id), action="workflow_recorder.start",
               entity_type="workflow_recording_session", entity_id=session.id,
               details=f"Started recording session #{session.id}")
    return {"session_id": session.id, "status": session.status, "title": session.title}


def stop_recording_session(db: Session, session_id: int, user_id: int) -> dict:
    session = db.query(WorkflowRecordingSession).filter(
        WorkflowRecordingSession.id == session_id,
        WorkflowRecordingSession.user_id == user_id,
    ).first()
    if not session:
        raise ValueError("Recording session not found")
    if session.status != "recording":
        raise ValueError(f"Session is not recording (status={session.status})")
    session.status = "stopped"
    session.stopped_at = datetime.utcnow()
    db.commit()
    log_action(db, actor=str(user_id), action="workflow_recorder.stop",
               entity_type="workflow_recording_session", entity_id=session_id,
               details=f"Stopped recording session #{session_id}")
    return {"session_id": session.id, "status": session.status, "event_count": session.event_count}


def cancel_recording_session(db: Session, session_id: int, user_id: int) -> dict:
    session = db.query(WorkflowRecordingSession).filter(
        WorkflowRecordingSession.id == session_id,
        WorkflowRecordingSession.user_id == user_id,
    ).first()
    if not session:
        raise ValueError("Recording session not found")
    session.status = "cancelled"
    session.stopped_at = datetime.utcnow()
    db.commit()
    log_action(db, actor=str(user_id), action="workflow_recorder.cancel",
               entity_type="workflow_recording_session", entity_id=session_id,
               details=f"Cancelled recording session #{session_id}")
    return {"session_id": session.id, "status": session.status}


def get_current_session(db: Session, user_id: int) -> dict | None:
    session = db.query(WorkflowRecordingSession).filter(
        WorkflowRecordingSession.user_id == user_id,
        WorkflowRecordingSession.status == "recording",
    ).order_by(WorkflowRecordingSession.id.desc()).first()
    if not session:
        return None
    event_count = db.query(WorkflowRecordedEvent).filter(
        WorkflowRecordedEvent.session_id == session.id,
    ).count()
    return {
        "session_id": session.id,
        "status": session.status,
        "title": session.title,
        "source": session.source,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "event_count": event_count,
    }


# ---------------------------------------------------------------------------
# Event recording
# ---------------------------------------------------------------------------


def record_event(
    db: Session,
    session_id: int,
    user_id: int,
    event: dict,
) -> dict:
    session = db.query(WorkflowRecordingSession).filter(
        WorkflowRecordingSession.id == session_id,
        WorkflowRecordingSession.user_id == user_id,
    ).first()
    if not session:
        raise ValueError("Recording session not found")
    if session.status != "recording":
        raise ValueError(f"Session is not recording (status={session.status})")

    event_type = event.get("event_type", "manual_event")
    label = event.get("label", event.get("selector", ""))
    raw_value = event.get("text_value", "")
    redacted_value = _redact_value(label, raw_value)
    was_redacted = redacted_value != raw_value

    if was_redacted:
        session.contains_sensitive_redactions = True

    next_order = (db.query(WorkflowRecordedEvent.event_order).filter(
        WorkflowRecordedEvent.session_id == session_id,
    ).order_by(WorkflowRecordedEvent.event_order.desc()).first() or [0])[0] + 1

    recorded = WorkflowRecordedEvent(
        session_id=session_id,
        user_id=user_id,
        event_type=event_type,
        app_name=event.get("app_name", ""),
        window_title=event.get("window_title", ""),
        browser_url=event.get("browser_url", event.get("url", "")),
        selector=event.get("selector", ""),
        label=label,
        coordinates_json=json.dumps(event.get("coordinates", {})),
        text_value_redacted=redacted_value,
        was_redacted=was_redacted,
        file_path=event.get("file_path", ""),
        screenshot_path=event.get("screenshot_path", ""),
        risk_level=event.get("risk_level", "low"),
        raw_event_json=json.dumps(event, default=str),
        timestamp=datetime.utcnow(),
        event_order=next_order,
    )
    db.add(recorded)

    session.event_count = (session.event_count or 0) + 1
    db.commit()
    db.refresh(recorded)

    return {
        "captured": True,
        "redacted": was_redacted,
        "event_id": recorded.id,
        "event_order": recorded.event_order,
    }


def list_session_events(
    db: Session,
    session_id: int,
    user_id: int,
) -> list[dict]:
    session = db.query(WorkflowRecordingSession).filter(
        WorkflowRecordingSession.id == session_id,
        WorkflowRecordingSession.user_id == user_id,
    ).first()
    if not session:
        raise ValueError("Recording session not found")
    events = db.query(WorkflowRecordedEvent).filter(
        WorkflowRecordedEvent.session_id == session_id,
    ).order_by(WorkflowRecordedEvent.event_order).all()
    return [
        {
            "id": e.id,
            "event_order": e.event_order,
            "event_type": e.event_type,
            "app_name": e.app_name,
            "window_title": e.window_title,
            "browser_url": e.browser_url,
            "label": e.label,
            "selector": e.selector,
            "coordinates_json": json.loads(e.coordinates_json) if e.coordinates_json else {},
            "text_value_redacted": e.text_value_redacted,
            "was_redacted": e.was_redacted,
            "file_path": e.file_path,
            "risk_level": e.risk_level,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in events
    ]


# ---------------------------------------------------------------------------
# Convert recording to skill draft
# ---------------------------------------------------------------------------


def convert_recording_to_skill_draft(
    db: Session,
    session_id: int,
    user_id: int,
    name: str = "",
    description: str = "",
) -> dict:
    session = db.query(WorkflowRecordingSession).filter(
        WorkflowRecordingSession.id == session_id,
        WorkflowRecordingSession.user_id == user_id,
    ).first()
    if not session:
        raise ValueError("Recording session not found")
    if session.status not in ("stopped", "saved"):
        raise ValueError(f"Cannot convert session with status={session.status}. Must be 'stopped'.")

    events = db.query(WorkflowRecordedEvent).filter(
        WorkflowRecordedEvent.session_id == session_id,
    ).order_by(WorkflowRecordedEvent.event_order).all()

    if not events:
        raise ValueError("No events recorded in this session")

    skill_name = name or _generate_skill_name_llm(events, session.title) or _generate_skill_name(events, session.title)
    skill_desc = description or f"Recorded workflow from session #{session_id}"
    trigger_phrases = _generate_trigger_phrases(events, session.title)

    steps = [_event_to_skill_step(e, i + 1) for i, e in enumerate(events)]
    safety_rules = _extract_safety_rules(events)

    draft = WorkflowSkillDraft(
        session_id=session_id,
        user_id=user_id,
        name=skill_name,
        description=skill_desc,
        trigger_phrases_json=json.dumps(trigger_phrases),
        steps_json=json.dumps(steps),
        safety_rules_json=json.dumps(safety_rules),
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    session.status = "saved"
    db.commit()

    log_action(db, actor=str(user_id), action="workflow_recorder.convert_to_draft",
               entity_type="workflow_skill_draft", entity_id=draft.id,
               details=f"Converted session #{session_id} to skill draft #{draft.id} ({len(steps)} steps)")

    return {
        "draft_id": draft.id,
        "name": draft.name,
        "description": draft.description,
        "trigger_phrases": trigger_phrases,
        "steps": steps,
        "safety_rules": safety_rules,
        "status": draft.status,
    }


def approve_skill_draft(db: Session, draft_id: int, user_id: int) -> dict:
    draft = db.query(WorkflowSkillDraft).filter(
        WorkflowSkillDraft.id == draft_id,
        WorkflowSkillDraft.user_id == user_id,
    ).first()
    if not draft:
        raise ValueError("Skill draft not found")
    if draft.status != "draft":
        raise ValueError(f"Cannot approve draft with status={draft.status}")
    draft.status = "approved"
    db.commit()
    log_action(db, actor=str(user_id), action="workflow_recorder.approve_draft",
               entity_type="workflow_skill_draft", entity_id=draft_id,
               details=f"Approved skill draft #{draft_id}")
    return {"draft_id": draft.id, "name": draft.name, "status": draft.status}


def reject_skill_draft(db: Session, draft_id: int, user_id: int) -> dict:
    draft = db.query(WorkflowSkillDraft).filter(
        WorkflowSkillDraft.id == draft_id,
        WorkflowSkillDraft.user_id == user_id,
    ).first()
    if not draft:
        raise ValueError("Skill draft not found")
    draft.status = "rejected"
    db.commit()
    log_action(db, actor=str(user_id), action="workflow_recorder.reject_draft",
               entity_type="workflow_skill_draft", entity_id=draft_id,
               details=f"Rejected skill draft #{draft_id}")
    return {"draft_id": draft.id, "status": draft.status}


def save_skill_draft_as_skill(db: Session, draft_id: int, user_id: int) -> dict:
    draft = db.query(WorkflowSkillDraft).filter(
        WorkflowSkillDraft.id == draft_id,
        WorkflowSkillDraft.user_id == user_id,
    ).first()
    if not draft:
        raise ValueError("Skill draft not found")
    if draft.status not in ("approved", "draft"):
        raise ValueError(f"Cannot save draft with status={draft.status}. Must be 'approved' or 'draft'.")

    trigger_phrases = json.loads(draft.trigger_phrases_json or "[]")
    steps = json.loads(draft.steps_json or "[]")
    safety_rules = json.loads(draft.safety_rules_json or "{}")

    skill = AccountingSkill(
        user_id=user_id,
        name=draft.name,
        description=draft.description,
        trigger_phrases_json=json.dumps(trigger_phrases),
        workflow_steps_json=json.dumps(steps),
        safety_rules_json=json.dumps(safety_rules),
        approval_required=safety_rules.get("approval_required", True),
        status="active",
    )
    db.add(skill)
    db.flush()

    version = AccountingSkillVersion(
        skill_id=skill.id,
        user_id=user_id,
        version=1,
        name=skill.name,
        description=skill.description,
        trigger_phrases_json=skill.trigger_phrases_json,
        workflow_steps_json=skill.workflow_steps_json,
        safety_rules_json=skill.safety_rules_json,
        approval_required=skill.approval_required,
    )
    db.add(version)

    draft.status = "saved"
    db.commit()
    db.refresh(skill)

    log_action(db, actor=str(user_id), action="workflow_recorder.save_as_skill",
               entity_type="accounting_skill", entity_id=skill.id,
               details=f"Saved draft #{draft_id} as skill '{skill.name}' (v1)")

    return {
        "skill_id": skill.id,
        "name": skill.name,
        "version": 1,
        "requires_dry_run": safety_rules.get("requires_dry_run", True),
    }
