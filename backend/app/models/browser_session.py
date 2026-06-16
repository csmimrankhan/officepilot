"""Phase 32 — browser session model for export automation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


SESSION_STATUSES = {"active", "waiting_login", "logged_in", "navigating", "exporting", "completed", "stopped", "error"}


class BrowserSession(Base):
    __tablename__ = "browser_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), default="user", nullable=False, index=True)
    run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    current_url: Mapped[str] = mapped_column(String(2048), default="", nullable=False)
    current_title: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    screenshot_path: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    download_dir: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    output_dir: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), default="", nullable=False)
    downloaded_file_path: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    guided_mode: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
