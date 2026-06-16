"""Phase 10 — file snapshot service.

The "Undo Automation" feature needs to roll back risky file
operations: Excel export overwrites, folder organizer moves, and
the upcoming Excel formula automation. We do this by:

1. Copying the about-to-be-overwritten-or-moved file to
   ``data/snapshots/<file_type>/<YYYY>/<MM>/<DD>/<uuid>.<ext>``.
2. Recording a row in :class:`app.models.file_snapshot.FileSnapshot`
   with hashes, sizes, the action that triggered it, and the
   original path.

On restore we copy the bytes back to the original path (or a
target the caller supplies). The row's ``restore_status`` flips
to ``"restored"`` so the UI can show "Used 2 times" badges.

The service is intentionally filesystem-only: the caller is
responsible for opening the DB session and creating the row.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SnapshotResult:
    snapshot_path: Path
    file_hash: str
    size_bytes: int


def sha256_of_file(path: Path) -> str:
    """Return the SHA-256 hex digest of ``path``. Streams in 1 MB
    chunks so a 100 MB Excel export does not balloon memory."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot_path_for(
    snapshots_root: Path,
    file_type: str,
    original_path: Path,
) -> Path:
    """Return the on-disk path where a snapshot copy of
    ``original_path`` should live. Layout:

        <root>/<file_type>/<YYYY>/<MM>/<DD>/<uuid>.<ext>
    """
    today = datetime.utcnow()
    ext = original_path.suffix or ""
    folder = snapshots_root / file_type / f"{today.year:04d}" / f"{today.month:02d}" / f"{today.day:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{uuid.uuid4().hex}{ext}"


def create_snapshot(
    source: Path,
    *,
    snapshots_root: Path,
    file_type: str,
) -> Optional[SnapshotResult]:
    """Copy ``source`` into the snapshots tree. Returns ``None`` if
    the source does not exist or is not a file (we treat those as
    no-ops — the caller decides whether that is an error)."""
    if not source.exists() or not source.is_file():
        return None
    target = snapshot_path_for(snapshots_root, file_type, source)
    shutil.copy2(str(source), str(target))
    digest = sha256_of_file(target)
    return SnapshotResult(
        snapshot_path=target,
        file_hash=digest,
        size_bytes=target.stat().st_size,
    )


def restore_snapshot(
    snapshot: Path,
    *,
    target: Path,
) -> SnapshotResult:
    """Copy the bytes at ``snapshot`` back to ``target``. Creates
    parent directories as needed. Overwrites ``target`` if it
    exists. Returns the new hash + size of the restored file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(snapshot), str(target))
    digest = sha256_of_file(target)
    return SnapshotResult(
        snapshot_path=snapshot,
        file_hash=digest,
        size_bytes=target.stat().st_size,
    )
