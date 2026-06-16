"""Phase 14 — Pydantic schemas for workflow recording and replay."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, RootModel


# ── Policy ────────────────────────────────────────────────────────────────

class WorkflowRecordingPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recording_enabled: bool
    screenshots_enabled: bool
    redact_sensitive_inputs: bool
    allowed_apps_json: list[str] = Field(default_factory=list)
    blocked_apps_json: list[str] = Field(default_factory=list)
    allowed_domains_json: list[str] = Field(default_factory=list)
    blocked_domains_json: list[str] = Field(default_factory=list)
    require_approval_for_replay: bool
    require_approval_for_submit: bool
    require_approval_for_write: bool
    notes: str
    created_at: datetime
    updated_at: datetime


class WorkflowRecordingPolicyUpdate(BaseModel):
    recording_enabled: Optional[bool] = None
    screenshots_enabled: Optional[bool] = None
    redact_sensitive_inputs: Optional[bool] = None
    allowed_apps_json: Optional[list[str]] = None
    blocked_apps_json: Optional[list[str]] = None
    allowed_domains_json: Optional[list[str]] = None
    blocked_domains_json: Optional[list[str]] = None
    require_approval_for_replay: Optional[bool] = None
    require_approval_for_submit: Optional[bool] = None
    require_approval_for_write: Optional[bool] = None
    notes: Optional[str] = None


# ── Recording Sessions ────────────────────────────────────────────────────

class WorkflowRecordingSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: Optional[int] = None
    status: str
    started_at: datetime
    stopped_at: Optional[datetime] = None
    contains_screenshots: bool
    contains_sensitive_redactions: bool
    raw_events_path: str
    event_count: int
    created_by: str
    created_at: datetime


class WorkflowRecordingSessionList(RootModel):
    model_config = ConfigDict(from_attributes=True)

    root: list[WorkflowRecordingSessionRead]


# ── Events ────────────────────────────────────────────────────────────────

class CaptureEventRequest(BaseModel):
    event_type: str
    app_name: str = ""
    window_title: str = ""
    target_description: str = ""
    selector_json: dict = Field(default_factory=dict)
    input_value: str = ""
    coordinates_json: dict = Field(default_factory=dict)
    screenshot_b64: str = ""


class CaptureEventResponse(BaseModel):
    captured: bool = True
    redacted: bool = False
    event_index: int


# ── Recorded Workflows ────────────────────────────────────────────────────

class RecordedWorkflowCreate(BaseModel):
    name: str
    description: str = ""
    source_type: str = "manual"


class RecordedWorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    risk_level: Optional[str] = None
    replay_mode_default: Optional[str] = None


class RecordedWorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    status: str
    source_type: str
    risk_level: str
    replay_mode_default: str
    total_steps: int
    created_by: str
    created_at: datetime
    updated_at: datetime


# ── Workflow Steps ────────────────────────────────────────────────────────

class RecordedWorkflowStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    step_order: int
    step_type: str
    app_name: str
    window_title: str
    target_description: str
    selector_json: dict = Field(default_factory=dict)
    ui_automation_json: dict = Field(default_factory=dict)
    fallback_coordinates_json: dict = Field(default_factory=dict)
    input_value_redacted: str
    expected_result_json: dict = Field(default_factory=dict)
    requires_approval: bool
    risk_level: str
    enabled: bool
    created_at: datetime


class RecordedWorkflowStepUpdate(BaseModel):
    step_type: Optional[str] = None
    app_name: Optional[str] = None
    window_title: Optional[str] = None
    target_description: Optional[str] = None
    input_value_redacted: Optional[str] = None
    expected_result_json: Optional[dict] = None
    requires_approval: Optional[bool] = None
    risk_level: Optional[str] = None
    enabled: Optional[bool] = None


class RecordedWorkflowStepList(RootModel):
    model_config = ConfigDict(from_attributes=True)

    root: list[RecordedWorkflowStepRead]


# ── Step Reorder ──────────────────────────────────────────────────────────

class StepReorder(BaseModel):
    step_id: int
    new_order: int


# ── Replay Runs ───────────────────────────────────────────────────────────

class WorkflowReplayRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    mode: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    stopped_by: str
    error_message: str
    created_at: datetime


class WorkflowReplayStepLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    replay_run_id: int
    step_id: int
    step_order: int
    step_type: str
    status: str
    action_preview_json: dict = Field(default_factory=dict)
    result_json: dict = Field(default_factory=dict)
    screenshot_path: str
    error_message: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime


class WorkflowReplayStepLogList(RootModel):
    model_config = ConfigDict(from_attributes=True)

    root: list[WorkflowReplayStepLogRead]


# ── Response Schemas ──────────────────────────────────────────────────────

class ReplayStartResponse(BaseModel):
    run_id: int
    mode: str
    total_steps: int
    first_step: Optional[RecordedWorkflowStepRead] = None


class StepActionResponse(BaseModel):
    step_log_id: int
    action_preview: dict = Field(default_factory=dict)
    requires_approval: bool
    risk_level: str


class ReplayStopResponse(BaseModel):
    stopped: bool
    run_id: int
    status: str


class RecordingStartResponse(BaseModel):
    session_id: int
    status: str


class RecordingStopResponse(BaseModel):
    session_id: int
    status: str
    event_count: int
    workflow_id: Optional[int] = None


class WorkflowDuplicateResponse(BaseModel):
    workflow_id: int
    name: str


# ── Action Preview ────────────────────────────────────────────────────────

class PlannedAction(BaseModel):
    step_type: str
    target_description: str
    input_value_redacted: str
    app_name: str
    risk_level: str
    requires_approval: bool
    warning: str = ""
