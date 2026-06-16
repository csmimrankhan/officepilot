"""Phase 15/16A — screen control step log model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


STEP_LOG_STATUSES = {"pending", "running", "completed", "failed", "skipped"}


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
