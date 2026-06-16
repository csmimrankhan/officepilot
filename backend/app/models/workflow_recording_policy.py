"""Phase 14 — workflow recording policy.

A single-row configuration table for the workflow recording
feature. The same row is upserted whenever the user toggles a
setting, manages the app / domain allowlist or blocklist, or
enables / disables screenshots or sensitive-input redaction.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


DEFAULT_ALLOWED_DOMAINS: list[str] = [
    "localhost",
    "127.0.0.1",
]

DEFAULT_BLOCKED_DOMAINS: list[str] = [
    "chase.com",
    "bankofamerica.com",
    "paypal.com",
    "coinbase.com",
    "irs.gov",
]


class WorkflowRecordingPolicy(Base):
    __tablename__ = "workflow_recording_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recording_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    screenshots_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    redact_sensitive_inputs: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    allowed_apps_json: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    blocked_apps_json: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    allowed_domains_json: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    blocked_domains_json: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    require_approval_for_replay: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    require_approval_for_submit: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    require_approval_for_write: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    notes: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
