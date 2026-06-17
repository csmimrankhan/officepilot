"""Phase 15/16A — Screen control ORM models (policy, session, action, step_log)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

PERMISSION_LEVELS = {0, 1, 2, 3, 4, 5}

DEFAULT_ALLOWED_APPS: list[str] = [
    "officepilot",
    "invoicepilot",
]

DEFAULT_BLOCKED_APPS: list[str] = [
    "password_manager",
    "banking",
    "security_settings",
    "credential_dialog",
]

DEFAULT_ALLOWED_FOLDERS: list[str] = []

DEFAULT_BLOCKED_DOMAINS: list[str] = [
    "chase.com", "bankofamerica.com", "wellsfargo.com", "citi.com",
    "paypal.com", "venmo.com", "coinbase.com", "kraken.com",
    "binance.com", "gemini.com", "1password.com", "lastpass.com",
    "bitwarden.com", "irs.gov", "hmrc.gov.uk",
]

ACTION_STATUSES = {"planned", "approved", "rejected", "running", "completed", "failed", "cancelled", "stopped"}
RISK_LEVELS = {"low", "medium", "high"}
APPROVAL_STATUSES = {"pending", "approved", "rejected", "not_required"}
SOURCE_TYPES = {"voice", "ui", "api", "workflow_replay"}
SESSION_STATUSES = {"active", "ended", "stopped"}
STEP_LOG_STATUSES = {"pending", "running", "completed", "failed", "skipped"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ScreenControlPolicy(Base):
    __tablename__ = "screen_control_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permission_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    screenshots_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ocr_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    click_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    type_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clipboard_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allowed_apps_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    blocked_apps_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    allowed_folders_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    blocked_domains_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    require_approval_for_click: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_approval_for_type: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_approval_for_submit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_approval_for_clipboard: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    emergency_stop_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ScreenControlSession(Base):
    __tablename__ = "screen_control_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), default="user", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    permission_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_app: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    active_window_title: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stopped_by: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    stop_reason: Mapped[str] = mapped_column(String(256), default="", nullable=False)


class ScreenControlAction(Base):
    __tablename__ = "screen_control_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="ui", nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    app_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    window_title: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    target_description: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    planned_action_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    executed_action_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), default="low", nullable=False)
    approval_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    screenshot_path: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    ocr_text_excerpt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    browser_action_run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stopped_by: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    stop_reason: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ScreenControlStepLog(Base):
    __tablename__ = "screen_control_step_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    target_description: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    screenshot_path: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    browser_action_step_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stopped_by: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    stop_reason: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
