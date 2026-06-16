"""Phase 10 — workflow-run version history.

Workflows in this codebase are *runtime* state machines
(:class:`app.models.workflow_run.WorkflowRun`), not user-editable
templates. The user-facing "Workflow Versions" feature therefore
versions the *state* of a run: its ``state_json``, the set of
node logs, the approval decisions, and the status.

Every state transition (approve, reject, retry, cancel, custom
node) captures a row here *before* the mutation. Restoring a
previous version rewinds the run to that point — a new version
row is then created with ``restored_from_version`` pointing back
at the one we restored, so the history stays append-only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    workflow_name: Mapped[str] = mapped_column(String(64), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Frozen snapshot of the WorkflowRun row + the per-node logs
    # and approval rows at this point in time. We store everything
    # together so a restore can rebuild the row atomically.
    workflow_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_action: Mapped[str] = mapped_column(String(64), default="user", nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    restored_from_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
