"""Phase 33 — Workflow Recorder MVP HTTP API.

All endpoints under /api/workflow-recorder.
Every endpoint is user-scoped via JWT auth.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.workflow_recorder_service import (
    start_recording_session,
    stop_recording_session,
    cancel_recording_session,
    get_current_session,
    record_event,
    list_session_events,
    convert_recording_to_skill_draft,
    approve_skill_draft,
    reject_skill_draft,
    save_skill_draft_as_skill,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workflow-recorder", tags=["workflow_recorder_phase33"])


# ── Request / Response models ───────────────────────────────────────────────


class StartRequest(BaseModel):
    title: str = ""
    source: str = "manual"


class StartResponse(BaseModel):
    session_id: int
    status: str
    title: str


class StopResponse(BaseModel):
    session_id: int
    status: str
    event_count: int


class CancelResponse(BaseModel):
    session_id: int
    status: str


class CurrentSessionResponse(BaseModel):
    session_id: int
    status: str
    title: str
    source: str
    started_at: Optional[str] = None
    event_count: int = 0


class EventRequest(BaseModel):
    event_type: str = "manual_event"
    app_name: str = ""
    window_title: str = ""
    browser_url: str = ""
    url: str = ""
    selector: str = ""
    label: str = ""
    coordinates: dict = {}
    text_value: str = ""
    file_path: str = ""
    screenshot_path: str = ""
    risk_level: str = "low"


class EventResponse(BaseModel):
    captured: bool
    redacted: bool
    event_id: int
    event_order: int


class EventRead(BaseModel):
    id: int
    event_order: int
    event_type: str
    app_name: str
    window_title: str
    browser_url: str
    label: str
    selector: str
    coordinates_json: dict = {}
    text_value_redacted: str
    was_redacted: bool
    file_path: str
    risk_level: str
    timestamp: Optional[str] = None


class ConvertRequest(BaseModel):
    name: str = ""
    description: str = ""


class ConvertResponse(BaseModel):
    draft_id: int
    name: str
    description: str
    trigger_phrases: list[str]
    steps: list[dict]
    safety_rules: dict
    status: str


class DraftActionResponse(BaseModel):
    draft_id: int
    name: str = ""
    status: str


class SaveAsSkillResponse(BaseModel):
    skill_id: int
    name: str
    version: int
    requires_dry_run: bool = True


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/start", response_model=StartResponse)
def start_endpoint(
    payload: StartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = start_recording_session(db, current_user.id, payload.title, payload.source)
    return StartResponse(**result)


@router.post("/stop", response_model=StopResponse)
def stop_endpoint(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = stop_recording_session(db, session_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return StopResponse(**result)


@router.post("/cancel", response_model=CancelResponse)
def cancel_endpoint(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = cancel_recording_session(db, session_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return CancelResponse(**result)


@router.get("/current", response_model=CurrentSessionResponse | None)
def current_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_current_session(db, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="No active recording session")
    return CurrentSessionResponse(**session)


@router.post("/event", response_model=EventResponse)
def event_endpoint(
    session_id: int,
    payload: EventRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event_dict = payload.model_dump()
    event_dict["url"] = payload.url or payload.browser_url
    try:
        result = record_event(db, session_id, current_user.id, event_dict)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return EventResponse(**result)


@router.get("/{session_id}/events", response_model=list[EventRead])
def list_events_endpoint(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        events = list_session_events(db, session_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return [EventRead(**e) for e in events]


@router.post("/{session_id}/convert-to-skill", response_model=ConvertResponse)
def convert_endpoint(
    session_id: int,
    payload: ConvertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = convert_recording_to_skill_draft(
            db, session_id, current_user.id,
            name=payload.name, description=payload.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ConvertResponse(**result)


@router.post("/skill-drafts/{draft_id}/approve", response_model=DraftActionResponse)
def approve_draft_endpoint(
    draft_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = approve_skill_draft(db, draft_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DraftActionResponse(**result)


@router.post("/skill-drafts/{draft_id}/reject", response_model=DraftActionResponse)
def reject_draft_endpoint(
    draft_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = reject_skill_draft(db, draft_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DraftActionResponse(**result)


@router.post("/skill-drafts/{draft_id}/save-as-skill", response_model=SaveAsSkillResponse)
def save_as_skill_endpoint(
    draft_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = save_skill_draft_as_skill(db, draft_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SaveAsSkillResponse(**result)
