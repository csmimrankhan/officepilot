"""Phase 12 — browser action run (one row per user / voice / workflow
initiated browser automation request).

The "run" is the durable record of the whole flow:

    preview -> approval -> execute -> validate -> log

The steps themselves live in :class:`BrowserActionStep` and the
captured page state lives in :class:`BrowserPageSnapshot`. The
risk level is classified up-front and only the matching risk
profile requires approval (e.g. ``low``-risk navigation can
proceed without a modal, ``medium``-risk forms always need one).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


ACTION_RUN_STATUSES = {
    "preview",        # preview requested, no execution yet
    "awaiting_approval",
    "approved",
    "rejected",
    "running",
    "completed",
    "failed",
    "cancelled",
}


APPROVAL_STATUSES = {"not_required", "pending", "approved", "rejected"}


RISK_LEVELS = {"low", "medium", "high"}


class BrowserActionRun(Base):
    __tablename__ = "browser_action_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # What kicked off this run. Examples: "ui", "voice",
    # "workflow", "invoice_detail", "test_form".
    source_type: Mapped[str] = mapped_column(String(32), default="ui", nullable=False)
    # Optional source row id (e.g. workflow_run_id, voice_command_id,
    # invoice_id). Loose FK only — we keep these as plain ints.
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    workflow_run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    voice_command_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # The high-level action we are about to perform.
    action_type: Mapped[str] = mapped_column(
        String(32), default="open_url", nullable=False
    )
    target_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    target_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    risk_level: Mapped[str] = mapped_column(
        String(16), default="low", nullable=False
    )
    approval_status: Mapped[str] = mapped_column(
        String(16), default="not_required", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), default="preview", nullable=False
    )
    preview_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
