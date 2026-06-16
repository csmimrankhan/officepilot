"""Phase 7 — local storage manager.

Reports the size + status of every OfficePilot data directory and
exposes a safe :func:`clear_cache` that only touches the transient
``cache/`` subdirectory. Invoices, exports, audit logs, Gmail state,
and workflow recordings are *never* deleted by this module.

The manager never resolves a path that escapes the configured
``data_dir`` or ``storage_root``; this is enforced by
:func:`_is_within`.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from ..config import Settings


# Subdirs that hold real, user-owned data. These are listed on the
# privacy dashboard but cannot be deleted from the UI.
PROTECTED_SUBDIRS = ("invoices", "exports", "audit", "recordings", "gmail")
# Subdirs that are safe to wipe at any time.
CACHE_SUBDIRS = ("cache", "tmp")


@dataclass
class DirInfo:
    name: str
    path: str
    exists: bool
    file_count: int
    total_bytes: int
    protected: bool

    def as_dict(self) -> dict:
        return asdict(self)


def _is_within(child: Path, parent: Path) -> bool:
    """True if ``child`` is the same as or inside ``parent``."""
    try:
        child = child.resolve(strict=False)
        parent = parent.resolve(strict=False)
    except OSError:
        return False
    if child == parent:
        return True
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _scan(path: Path) -> tuple[int, int]:
    """Return ``(file_count, total_bytes)`` for *path*.

    Follows symlinks but not into other drives; counts the path
    itself if it is a regular file.
    """
    if not path.exists():
        return (0, 0)
    if path.is_file():
        return (1, path.stat().st_size)
    count = 0
    total = 0
    for root, _dirs, files in os.walk(path, followlinks=False):
        for f in files:
            fp = Path(root) / f
            try:
                total += fp.stat().st_size
                count += 1
            except OSError:
                # A file may vanish between the walk and the stat
                # (e.g. a temp file). Skip it rather than fail.
                continue
    return (count, total)


def _format_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    for u in units:
        if f < 1024 or u == units[-1]:
            return f"{f:.1f} {u}" if u != "B" else f"{int(f)} {u}"
        f /= 1024
    return f"{n} B"


def _build_dirs(settings: Settings) -> list[DirInfo]:
    data_dir = settings.data_dir
    storage_root = settings.storage_root
    out: list[DirInfo] = []

    # Top-level data directory itself.
    count, total = _scan(data_dir)
    out.append(DirInfo(
        name="data",
        path=str(data_dir),
        exists=data_dir.exists(),
        file_count=count,
        total_bytes=total,
        protected=True,
    ))

    # Storage subdirs (Phase 1-3 artefacts).
    for sub in PROTECTED_SUBDIRS:
        p = storage_root / sub
        count, total = _scan(p)
        out.append(DirInfo(
            name=sub,
            path=str(p),
            exists=p.exists(),
            file_count=count,
            total_bytes=total,
            protected=True,
        ))

    # Cache subdirs (safe to clear).
    for sub in CACHE_SUBDIRS:
        p = data_dir / sub
        count, total = _scan(p)
        out.append(DirInfo(
            name=sub,
            path=str(p),
            exists=p.exists(),
            file_count=count,
            total_bytes=total,
            protected=False,
        ))

    # Gmail state dir is configured separately.
    p = settings.gmail_state_dir
    count, total = _scan(p)
    out.append(DirInfo(
        name="gmail_state",
        path=str(p),
        exists=p.exists(),
        file_count=count,
        total_bytes=total,
        protected=True,
    ))

    # Phase 8: log directory (agent + supervisor logs). Logged as
    # protected so the user can see the size on the privacy
    # dashboard; the clear-cache action never touches it.
    p = settings.logs_dir
    count, total = _scan(p)
    out.append(DirInfo(
        name="logs",
        path=str(p),
        exists=p.exists(),
        file_count=count,
        total_bytes=total,
        protected=True,
    ))

    return out


def summarize(settings: Settings) -> dict:
    """Return the privacy-dashboard-friendly storage summary."""
    dirs = _build_dirs(settings)
    protected_total = sum(d.total_bytes for d in dirs if d.protected)
    cache_total = sum(d.total_bytes for d in dirs if not d.protected)
    return {
        "data_dir": str(settings.data_dir),
        "storage_root": str(settings.storage_root),
        "protected_total_bytes": protected_total,
        "protected_total_human": _format_bytes(protected_total),
        "cache_total_bytes": cache_total,
        "cache_total_human": _format_bytes(cache_total),
        "dirs": [d.as_dict() for d in dirs],
    }


def clear_cache(settings: Settings) -> dict:
    """Wipe every cache subdir under ``data_dir``.

    Returns a dict describing what was deleted. We never touch any
    path outside ``data_dir`` and we never delete a file from a
    *protected* subdir.
    """
    data_dir = settings.data_dir
    removed_files = 0
    removed_bytes = 0
    removed_dirs: list[str] = []
    skipped: list[str] = []

    for sub in CACHE_SUBDIRS:
        p = data_dir / sub
        if not p.exists():
            continue
        if not _is_within(p, data_dir):
            # Defence in depth: refuse to delete a path that is
            # not inside the configured data dir.
            skipped.append(str(p))
            continue
        if p.is_file():
            try:
                removed_bytes += p.stat().st_size
                removed_files += 1
                p.unlink()
                removed_dirs.append(str(p))
            except OSError:
                skipped.append(str(p))
            continue
        for root, dirs, files in os.walk(p):
            for f in files:
                fp = Path(root) / f
                try:
                    removed_bytes += fp.stat().st_size
                    removed_files += 1
                    fp.unlink()
                except OSError:
                    skipped.append(str(fp))
            for d in dirs:
                dp = Path(root) / d
                try:
                    dp.rmdir()  # only removes empty dirs
                except OSError:
                    pass
        removed_dirs.append(str(p))

    return {
        "removed_files": removed_files,
        "removed_bytes": removed_bytes,
        "removed_bytes_human": _format_bytes(removed_bytes),
        "removed_dirs": removed_dirs,
        "skipped": skipped,
    }


def export_audit_csv(settings: Settings, db_rows: Iterable[dict]) -> tuple[str, int]:
    """Write the given audit-log rows to a CSV in the audit dir.

    ``db_rows`` should be the dicts from
    :func:`app.services.audit.list_logs`.

    Returns ``(path, row_count)``. The file name is timestamped so
    successive exports do not clobber each other.
    """
    import csv
    from datetime import datetime as _dt

    audit_dir = settings.audit_dir
    audit_dir.mkdir(parents=True, exist_ok=True)
    ts = _dt.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = audit_dir / f"audit_export_{ts}.csv"
    rows = list(db_rows)
    fieldnames = [
        "id", "timestamp", "actor", "action", "entity_type", "entity_id",
        "details", "before_data_json", "after_data_json",
    ]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return (str(out_path), len(rows))
