"""Phase 15/16A — screen control action model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


ACTION_STATUSES = {"planned", "approved", "rejected", "running", "completed", "failed", "cancelled", "stopped"}
RISK_LEVELS = {"low", "medium", "high"}
APPROVAL_STATUSES = {"pending", "approved", "rejected", "not_required"}
SOURCE_TYPES = {"voice", "ui", "api", "workflow_replay"}


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
