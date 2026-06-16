"""Phase 12 — Pydantic schemas for the browser automation API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class BrowserPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    allowed_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)
    require_approval_for_submit: bool = True
    require_approval_for_write: bool = True
    screenshots_enabled: bool = True
    enabled: bool = False
    headless: bool = False
    notes: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class BrowserPolicyUpdate(BaseModel):
    allowed_domains: Optional[list[str]] = None
    blocked_domains: Optional[list[str]] = None
    require_approval_for_submit: Optional[bool] = None
    require_approval_for_write: Optional[bool] = None
    screenshots_enabled: Optional[bool] = None
    enabled: Optional[bool] = None
    headless: Optional[bool] = None
    notes: Optional[str] = None


class BrowserStatusRead(BaseModel):
    enabled: bool
    headless: bool
    screenshots_enabled: bool
    adapter_mode: str
    live: bool
    allowed_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)
    last_url: str = ""
    last_title: str = ""


class BrowserStepPreview(BaseModel):
    step_order: int
    step_type: str
    target_description: str
    selector: str
    input_value_redacted: str
    requires_approval: bool


class BrowserRiskAssessment(BaseModel):
    risk_level: str
    requires_approval: bool
    reasons: list[str] = Field(default_factory=list)


class BrowserDomainDecision(BaseModel):
    allowed: bool
    host: str
    reason: str


class BrowserActionPreview(BaseModel):
    action_type: str
    target_url: Optional[str] = None
    target_domain: str
    risk: BrowserRiskAssessment
    steps: list[BrowserStepPreview] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    domain_decision: Optional[BrowserDomainDecision] = None


class BrowserPreviewRequest(BaseModel):
    action_type: str = "open_url"
    target_url: str
    field_values: dict[str, Any] = Field(default_factory=dict)
    submit: bool = False
    invoice_id: Optional[int] = None
    source_type: str = "ui"
    source_id: Optional[int] = None
    workflow_run_id: Optional[int] = None
    voice_command_id: Optional[int] = None
    actor: str = "user"


class BrowserPreviewResponse(BaseModel):
    run_id: Optional[int] = None
    preview: BrowserActionPreview
    requires_approval: bool
    domain_allowed: bool
    message: str = ""


class BrowserActionRequest(BaseModel):
    run_id: int
    action_type: Optional[str] = None
    actor: str = "user"


class BrowserActionResponse(BaseModel):
    run_id: int
    status: str
    approval_status: str
    risk_level: str
    target_url: Optional[str] = None
    target_domain: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: dict = Field(default_factory=dict)


class BrowserActionStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    browser_action_run_id: int
    step_order: int
    step_type: str
    target_description: str
    selector: str
    input_value_redacted: str
    requires_approval: bool
    status: str
    screenshot_path: str
    error_message: str
    created_at: datetime


class BrowserActionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    source_id: Optional[int] = None
    workflow_run_id: Optional[int] = None
    voice_command_id: Optional[int] = None
    action_type: str
    target_url: Optional[str] = None
    target_domain: Optional[str] = None
    risk_level: str
    approval_status: str
    status: str
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    preview_json: dict = Field(default_factory=dict)
    result_json: dict = Field(default_factory=dict)


class BrowserActionRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    action_type: str
    target_url: Optional[str] = None
    target_domain: Optional[str] = None
    risk_level: str
    approval_status: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime


class BrowserPageSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    browser_action_run_id: int
    url: str
    title: str
    visible_text_excerpt: str
    screenshot_path: str
    created_at: datetime


class BrowserApprovalRequest(BaseModel):
    actor: str = "user"
    reason: str = "User approved the browser action."


class BrowserRejectRequest(BaseModel):
    actor: str = "user"
    reason: str = "User rejected the browser action."


class BrowserCancelRequest(BaseModel):
    actor: str = "user"
    reason: str = "User cancelled the browser action."


class BrowserVoiceIntentRequest(BaseModel):
    intent: str
    target_url: Optional[str] = None
    invoice_id: Optional[int] = None
    actor: str = "voice"


class BrowserVoiceIntentResponse(BaseModel):
    intent: str
    blocked: bool
    preview: Optional[BrowserActionPreview] = None
    message: str = ""


class BrowserTestFormFillRequest(BaseModel):
    invoice_id: int
    actor: str = "user"
    submit: bool = False
