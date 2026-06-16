"""Phase 14 — recorded workflow model.

Each row represents a recorded (or manually defined) desktop
workflow that can be replayed. Steps live in
:class:`RecordedWorkflowStep`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


WORKFLOW_STATUSES = {"draft", "ready", "archived"}
SOURCE_TYPES = {"recording", "manual", "imported"}
RISK_LEVELS = {"low", "medium", "high"}
REPLAY_MODES = {"dry_run", "step_by_step"}


class RecordedWorkflow(Base):
    __tablename__ = "recorded_workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="draft", nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(
        String(32), default="recording", nullable=False
    )
    risk_level: Mapped[str] = mapped_column(
        String(16), default="medium", nullable=False
    )
    replay_mode_default: Mapped[str] = mapped_column(
        String(16), default="dry_run", nullable=False
    )
    total_steps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
