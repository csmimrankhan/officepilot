from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


EVENT_TYPES = frozenset({
    "app_focus", "window_title_change", "browser_url_open",
    "browser_url_change", "click", "type_text", "hotkey",
    "file_open", "file_select", "folder_open", "download_detected",
    "wait", "manual_login_checkpoint", "guided_export_checkpoint",
    "screenshot", "copy", "paste", "approval_checkpoint",
    "manual_event",
})


class WorkflowRecordedEvent(Base):
    __tablename__ = "workflow_recorded_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflow_recording_sessions.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    app_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    window_title: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    browser_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    selector: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    label: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    coordinates_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    text_value_redacted: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    was_redacted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    screenshot_path: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), default="low", nullable=False)
    raw_event_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    event_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
