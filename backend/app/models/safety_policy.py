"""Phase 16B — Global Safety Policy (single-row config)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class SafetyPolicy(Base):
    __tablename__ = "safety_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cloud_ai_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    browser_automation_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    screen_control_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    workflow_recording_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accounting_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    voice_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    screenshots_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ocr_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_approval_for_write: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_snapshot_for_file_changes: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    block_unknown_apps: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    block_unknown_domains: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
