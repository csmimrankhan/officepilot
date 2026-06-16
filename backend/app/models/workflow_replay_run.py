"""Phase 14 — workflow replay run model.

Each row represents one execution (replay) of a
:class:`RecordedWorkflow`. Step-level logs live in
:class:`WorkflowReplayStepLog`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


REPLAY_MODES = {"dry_run", "step_by_step"}
REPLAY_STATUSES = {
    "pending",
    "running",
    "paused",
    "completed",
    "failed",
    "stopped",
    "cancelled",
}


class WorkflowReplayRun(Base):
    __tablename__ = "workflow_replay_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stopped_by: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
