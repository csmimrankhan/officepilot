"""Phase 6 — workflow run model.

Each row represents one execution of a LangGraph workflow. The
``state_json`` column holds the per-node state at the time of the
last successful transition; ``current_node`` is the node that will
run on the next resume.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"            # created, not started yet
    RUNNING = "running"            # graph is executing
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"          # user explicitly rejected an approval
    CANCELLED = "cancelled"


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default=WorkflowStatus.PENDING.value, nullable=False, index=True)
    current_node: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    state_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(128), default="user", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
