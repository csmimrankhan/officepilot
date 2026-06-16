"""Phase 14 — workflow recording session model.

Each row represents one recording session — the act of capturing
desktop interactions before they are saved as a
:class:`RecordedWorkflow`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


SESSION_STATUSES = {"recording", "stopped", "saved", "cancelled"}


class WorkflowRecordingSession(Base):
    __tablename__ = "workflow_recording_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="recording", nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    contains_screenshots: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    contains_sensitive_redactions: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    raw_events_path: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    raw_events_json: Mapped[Optional[str]] = mapped_column(Text, default="[]", nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
