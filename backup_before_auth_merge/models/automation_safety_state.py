"""Phase 17 — Persistent automation safety state (kill switch)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class AutomationSafetyState(Base):
    __tablename__ = "automation_safety_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kill_switch_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    activated_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resumed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resumed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
