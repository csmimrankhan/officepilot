"""Phase 15 — screen control session model."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


SESSION_STATUSES = {"active", "ended", "stopped"}


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
