"""Phase 14 — recorded workflow step model.

One row per step within a :class:`RecordedWorkflow`. The
``step_type`` determines which UI automation action to take
during replay.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


STEP_TYPES = {
    "open_app",
    "open_url",
    "open_file",
    "open_folder",
    "click_element",
    "type_text",
    "hotkey",
    "copy_text",
    "paste_text",
    "wait_for_window",
    "fill_form_field",
    "click_button",
    "run_business_action",
    "run_browser_action",
    "run_accounting_preview",
    "approval_checkpoint",
    "validation_checkpoint",
    "stop",
}


class RecordedWorkflowStep(Base):
    __tablename__ = "recorded_workflow_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(64), nullable=False)
    app_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    window_title: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    target_description: Mapped[str] = mapped_column(
        String(512), default="", nullable=False
    )
    selector_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ui_automation_json: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    fallback_coordinates_json: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    input_value_redacted: Mapped[str] = mapped_column(
        String(512), default="", nullable=False
    )
    expected_result_json: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    risk_level: Mapped[str] = mapped_column(
        String(16), default="low", nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
