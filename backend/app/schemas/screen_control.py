"""Phase 15 — Pydantic schemas for the screen control API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScreenPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    enabled: bool = False
    permission_level: int = 0
    screenshots_enabled: bool = False
    ocr_enabled: bool = False
    click_enabled: bool = False
    type_enabled: bool = False
    clipboard_enabled: bool = True
    allowed_apps: list[str] = Field(default_factory=list)
    blocked_apps: list[str] = Field(default_factory=list)
    allowed_folders: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)
    require_approval_for_click: bool = True
    require_approval_for_type: bool = True
    require_approval_for_submit: bool = True
    require_approval_for_clipboard: bool = True
    emergency_stop_enabled: bool = True
    notes: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ScreenPolicyUpdate(BaseModel):
    enabled: Optional[bool] = None
    permission_level: Optional[int] = None
    screenshots_enabled: Optional[bool] = None
    ocr_enabled: Optional[bool] = None
    click_enabled: Optional[bool] = None
    type_enabled: Optional[bool] = None
    clipboard_enabled: Optional[bool] = None
    allowed_apps: Optional[list[str]] = None
    blocked_apps: Optional[list[str]] = None
    allowed_folders: Optional[list[str]] = None
    blocked_domains: Optional[list[str]] = None
    require_approval_for_click: Optional[bool] = None
    require_approval_for_type: Optional[bool] = None
    require_approval_for_submit: Optional[bool] = None
    require_approval_for_clipboard: Optional[bool] = None
    emergency_stop_enabled: Optional[bool] = None
    notes: Optional[str] = None


class ScreenStatusRead(BaseModel):
    enabled: bool
    permission_level: int
    screenshots_enabled: bool
    ocr_enabled: bool
    click_enabled: bool
    type_enabled: bool
    clipboard_enabled: bool
    session_active: bool = False
    session_id: Optional[int] = None
    active_app: str = ""
    active_window_title: str = ""
    allowed_apps: list[str] = Field(default_factory=list)
    blocked_apps: list[str] = Field(default_factory=list)
    allowed_folders: list[str] = Field(default_factory=list)


class ScreenSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str = "user"
    status: str = "active"
    permission_level: int = 0
    active_app: str = ""
    active_window_title: str = ""
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    stopped_by: str = ""
    stop_reason: str = ""


class ScreenSessionStartResponse(BaseModel):
    session_id: int
    status: str
    permission_level: int


class ScreenReadContextResponse(BaseModel):
    active_app: str
    active_window_title: str
    ocr_text: str = ""
    screenshot_path: str = ""
    summary: str = ""


class ScreenCaptureResponse(BaseModel):
    screenshot_path: str = ""
    stored: bool = False


class ScreenOcrResponse(BaseModel):
    text: str = ""
    lines: list[str] = Field(default_factory=list)


class ScreenSummarizeResponse(BaseModel):
    summary: str
    app: str
    window: str
    text_length: int


class ScreenPlannedStep(BaseModel):
    step_order: int
    step_type: str
    target_description: str = ""
    requires_approval: bool = False


class ScreenRiskAssessment(BaseModel):
    risk_level: str = "low"
    requires_approval: bool = False
    reasons: list[str] = Field(default_factory=list)


class ScreenBlockDecision(BaseModel):
    allowed: bool = True
    reason: str = ""


class ScreenActionPreviewResponse(BaseModel):
    action_id: int
    action_type: str
    app_name: str
    window_title: str
    target_description: str
    risk: ScreenRiskAssessment
    steps: list[ScreenPlannedStep] = Field(default_factory=list)
    blocked: Optional[ScreenBlockDecision] = None
    domain_decision: Optional[ScreenBlockDecision] = None


class ScreenActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    source_type: str = "ui"
    source_id: str = ""
    action_type: str = ""
    app_name: str = ""
    window_title: str = ""
    target_description: str = ""
    risk_level: str = "low"
    approval_status: str = "pending"
    status: str = "planned"
    screenshot_path: str = ""
    ocr_text_excerpt: str = ""
    error_message: str = ""
    browser_action_run_id: Optional[int] = None
    stopped_by: str = ""
    stop_reason: str = ""
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class ScreenActionReadWithPreview(ScreenActionRead):
    planned_action: dict = Field(default_factory=dict)
    executed_action: dict = Field(default_factory=dict)
    result: dict = Field(default_factory=dict)


class ScreenStepLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_id: int
    step_order: int
    step_type: str = ""
    target_description: str = ""
    status: str = "pending"
    screenshot_path: str = ""
    error_message: str = ""
    browser_action_step_id: Optional[int] = None
    stopped_by: str = ""
    stop_reason: str = ""
    created_at: Optional[str] = None


class ScreenActionApproveResponse(BaseModel):
    action_id: int
    status: str
    approval_status: str
    steps: list[ScreenPlannedStep] = Field(default_factory=list)


class ScreenActionRejectResponse(BaseModel):
    action_id: int
    status: str
    approval_status: str


class ScreenStepExecuteResponse(BaseModel):
    step_log_id: int
    step_order: int
    status: str
    result: dict = Field(default_factory=dict)


class ScreenEmergencyStopResponse(BaseModel):
    stopped: bool
    reason: str = ""


class ScreenVoiceIntentRequest(BaseModel):
    intent: str
    source_id: str = ""


class ScreenVoiceIntentResponse(BaseModel):
    intent: str
    parsed_action: str
    preview: ScreenActionPreviewResponse


class ScreenOpenFileRequest(BaseModel):
    file_path: str


class ScreenOpenFolderRequest(BaseModel):
    folder_path: str


class ScreenCopyToClipboardRequest(BaseModel):
    text: str


class ScreenPasteToTargetRequest(BaseModel):
    target_app: str = ""
    target_window: str = ""
    text: str


class ScreenCapabilitiesResponse(BaseModel):
    ocr_engine: str = "tesseract"
    ocr_available: bool = False
    click_enabled: bool = False
    type_enabled: bool = False
    clipboard_enabled: bool = True
    ui_automation_enabled: bool = True
    pyautogui_fallback: bool = False
    block_unknown_apps: bool = True
    pyautogui_available: bool = False
    tesseract_installed: bool = False


class ScreenOcrStatusResponse(BaseModel):
    engine: str = ""
    available: bool = False
    message: str = ""


class ScreenExecuteAllResponse(BaseModel):
    action_id: int
    results: list[ScreenStepExecuteResponse] = Field(default_factory=list)
