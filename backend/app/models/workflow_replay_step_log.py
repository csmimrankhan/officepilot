"""Phase 14 — workflow replay step log model.

One row per step executed (or skipped) during a
:class:`WorkflowReplayRun`. Tracks the action preview,
result, screenshot, and any error encountered.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


STEP_LOG_STATUSES = {
    "pending",
    "running",
    "approved",
    "rejected",
    "skipped",
    "completed",
    "failed",
}


class WorkflowReplayStepLog(Base):
    __tablename__ = "workflow_replay_step_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    replay_run_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    step_id: Mapped[int] = mapped_column(Integer, nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )
    action_preview_json: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    result_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    screenshot_path: Mapped[str] = mapped_column(
        String(512), default="", nullable=False
    )
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
