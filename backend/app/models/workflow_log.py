"""Phase 6 — per-node log entries.

One row per node transition. Captures status (ok/awaiting_approval/
failed/skipped), an optional message, and a JSON blob with whatever
the node wants to surface.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class NodeLogStatus(str, enum.Enum):
    OK = "ok"
    AWAITING_APPROVAL = "awaiting_approval"
    SKIPPED = "skipped"
    FAILED = "failed"


class WorkflowLog(Base):
    __tablename__ = "workflow_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=NodeLogStatus.OK.value, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
