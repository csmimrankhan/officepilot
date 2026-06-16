"""Phase 12 — per-step log for a browser action run.

Each :class:`BrowserActionRun` decomposes into one or more
:class:`BrowserActionStep` rows (navigate, fill field, click button,
validate). Storing the steps as separate rows means the UI can
render an inspectable timeline even after the run is done, and
postmortems (why did the form submit fail?) don't have to dig
through a free-form JSON blob.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


STEP_STATUSES = {"pending", "running", "completed", "failed", "skipped"}


class BrowserActionStep(Base):
    __tablename__ = "browser_action_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    browser_action_run_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    step_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # E.g. "navigate", "fill", "click", "validate", "screenshot".
    step_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # Human-readable description (e.g. "Fill vendor_name with 'Acme'").
    target_description: Mapped[str] = mapped_column(
        String(512), default="", nullable=False
    )
    # CSS / XPath / aria-label the adapter will resolve at run time.
    selector: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    # Redacted value (see services/browser_automation.redact_value).
    input_value_redacted: Mapped[str] = mapped_column(
        String(1024), default="", nullable=False
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False
    )
    screenshot_path: Mapped[str] = mapped_column(
        String(1024), default="", nullable=False
    )
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
