"""Phase 10 — restore audit log.

Every restore action (entity version, file snapshot, or workflow
version) creates one row here *and* one row in
:class:`app.models.audit_log.AuditLog`. The general audit log
records the event in the global timeline; this table provides a
focused "who restored what and when" view the Version History
page can query directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class RestoreLog(Base):
    __tablename__ = "restore_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # "entity_version" | "file_snapshot" | "workflow_version"
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # The integer PK of the entity_versions / file_snapshots /
    # workflow_versions row that was restored.
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # The user-facing identifier of the underlying object
    # (invoice_id, workflow_run_id, file_path, ...). Stored as a
    # string so non-integer cases work.
    target_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # For entity_versions: the version_number we restored from.
    # For file_snapshots: the source snapshot id (== entity_id).
    # For workflow_versions: the version_number we restored from.
    restored_from_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # The new version_number / version that exists *after* the
    # restore (the new history row we appended).
    restored_to_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Free-text reason the user typed in the restore modal.
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    restored_by: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    restored_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
