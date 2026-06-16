"""Phase 12 — captured page snapshot (URL + title + visible text).

Stored separately from :class:`BrowserActionStep` so a single page
load can keep its own artifact even when the step log is rotated.
Screenshots are written to ``data/browser_snapshots/<run_id>/...``
and only the relative path lives in the DB.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class BrowserPageSnapshot(Base):
    __tablename__ = "browser_page_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    browser_action_run_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    # Truncated to a reasonable size to keep the DB small.
    visible_text_excerpt: Mapped[str] = mapped_column(
        Text, default="", nullable=False
    )
    screenshot_path: Mapped[str] = mapped_column(
        String(1024), default="", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
