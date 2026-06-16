"""Phase 10 — file snapshots for the "Undo Automation" feature.

Before any risky file action (Excel export overwrite, folder
move/rename, future Excel formula automation) we copy the
existing file to ``data/snapshots/<file_type>/<YYYY>/<MM>/<DD>/<uuid>.<ext>``
and record a row here. The hash of the file before and after the
action lets the user verify the operation.

Restoring a snapshot copies the file back to ``original_path``
(unless the caller supplied a different target). The row's
``restore_status`` flips to ``"restored"`` and ``restored_at`` is
set; the snapshot file is kept on disk so a user can re-restore
multiple times.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class FileSnapshot(Base):
    __tablename__ = "file_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Coarse file category: "excel_export", "invoice_file",
    # "organized_invoice", ...
    file_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Where the file lived *before* the action (the path we'd
    # overwrite or move away from).
    original_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    # Where we copied the bytes to.
    snapshot_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    # What caused the snapshot, e.g. "excel_export.overwrite",
    # "organizer.move", "excel_formula.write".
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # SHA-256 hex of the file before the action. Nullable because
    # the snapshot might be of a file that was just created (so
    # there is no "before").
    file_hash_before: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # SHA-256 hex of the file after the action (or of the file
    # we copied if no follow-up write happened).
    file_hash_after: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Optional size for sanity / display.
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Who triggered the action.
    created_by: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    # Set when the snapshot has been restored at least once. The
    # file stays on disk so the user can re-restore.
    restored_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Counts how many times this snapshot has been restored.
    restore_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # "active" (default), "restored" (used at least once),
    # "missing" (snapshot file is gone — the user can still see
    # the row, but a restore will fail).
    restore_status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
