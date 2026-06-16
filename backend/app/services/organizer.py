"""File organizer (Phase 3).

When an invoice is approved we rename and move the original file to a
structured folder using a user-configurable pattern. Default:

    Invoices/{year}/{month}/{vendor}_{invoice_number}_{total}_{currency}.{ext}

Tokens supported:
- ``{year}``     4-digit year from invoice_date (else current year)
- ``{month}``    2-digit month from invoice_date (else current month)
- ``{day}``      2-digit day
- ``{vendor}``   vendor name, sanitized for filenames
- ``{invoice_number}``
- ``{total}``    total amount, with 2 decimals, dot as decimal separator
- ``{currency}`` ISO code or symbol
- ``{date}``     YYYY-MM-DD
- ``{source}``   "upload" or "email"
- ``{id}``       invoice id
- ``{ext}``      file extension (no dot)

Any token that is missing/empty is replaced by ``"unknown"`` so the file
name never becomes blank.

Conflict strategies:
- ``"suffix"``    append ``_1``, ``_2`` etc. if the target exists
- ``"skip"``      return the original path unchanged
- ``"overwrite"`` replace the existing file
"""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models.invoice import Invoice
from ..services import settings as settings_service

logger = logging.getLogger(__name__)


_INVALID_FN = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')
_WHITESPACE = re.compile(r"\s+")


@dataclass
class OrganizeResult:
    source_path: str
    target_path: str
    moved: bool
    skipped_reason: Optional[str] = None


def _sanitize(value: str, *, max_len: int = 80) -> str:
    if not value:
        return "unknown"
    v = _INVALID_FN.sub("_", str(value))
    v = _WHITESPACE.sub(" ", v).strip(" .")
    v = v.strip()
    if not v:
        return "unknown"
    return v[:max_len]


def _money(value) -> str:
    if value is None:
        return "0.00"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _date_parts(invoice_date: Optional[str]) -> tuple[str, str, str]:
    if invoice_date:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(invoice_date, fmt)
                return f"{dt.year:04d}", f"{dt.month:02d}", f"{dt.day:02d}"
            except ValueError:
                continue
    now = datetime.utcnow()
    return f"{now.year:04d}", f"{now.month:02d}", f"{now.day:02d}"


def build_target_path(
    storage_root: Path,
    invoice: Invoice,
    *,
    pattern: str,
    source_path: str,
) -> Path:
    year, month, day = _date_parts(invoice.invoice_date)
    src = Path(source_path)
    ext = src.suffix.lstrip(".").lower() or "pdf"
    tokens = {
        "year": year,
        "month": month,
        "day": day,
        "vendor": _sanitize(invoice.vendor_name or ""),
        "invoice_number": _sanitize(invoice.invoice_number or ""),
        "total": _money(invoice.total_amount),
        "currency": _sanitize((invoice.currency or "USD"), max_len=8),
        "date": f"{year}-{month}-{day}",
        "source": invoice.file.source if invoice.file else "upload",
        "id": str(invoice.id),
        "ext": ext,
    }
    # Tokenize
    rel = re.sub(r"\{(\w+)\}", lambda m: tokens.get(m.group(1), "unknown"), pattern)
    # Collapse repeated separators that can result from empty tokens
    rel = re.sub(r"(?<!^)/+", "/", rel)
    rel = rel.replace("\\", "/")
    if not rel.lower().endswith("." + ext):
        rel = f"{rel}.{ext}"
    target = storage_root / rel
    return target


def _resolve_conflict(target: Path, strategy: str) -> tuple[Path, bool]:
    """Return ``(final_path, moved_ok)`` per the conflict strategy."""
    if not target.exists():
        return target, True
    if strategy == "overwrite":
        return target, True
    if strategy == "skip":
        return target, False
    # default: suffix
    stem = target.stem
    parent = target.parent
    suffix = target.suffix
    for n in range(1, 1000):
        candidate = parent / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate, True
    return target, False


def organize(
    storage_root: Path,
    invoice: Invoice,
    *,
    source_path: str,
    pattern: str,
    conflict_strategy: str = "suffix",
) -> OrganizeResult:
    """Move the file at ``source_path`` to its target location.

    Returns an :class:`OrganizeResult` describing what happened. The file
    is renamed/moved on disk using :func:`shutil.move`.
    """
    src = Path(source_path)
    if not src.exists():
        return OrganizeResult(
            source_path=source_path,
            target_path=source_path,
            moved=False,
            skipped_reason="source file missing",
        )

    target = build_target_path(storage_root, invoice, pattern=pattern, source_path=source_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    final_target, ok = _resolve_conflict(target, conflict_strategy)
    if not ok:
        return OrganizeResult(
            source_path=source_path,
            target_path=str(target),
            moved=False,
            skipped_reason="target exists (skip strategy)",
        )
    shutil.move(str(src), str(final_target))
    return OrganizeResult(
        source_path=source_path,
        target_path=str(final_target),
        moved=True,
    )


def get_effective_rules(db, settings_service_module=None) -> dict:
    """Return the folder rules, falling back to defaults."""
    svc = settings_service_module or settings_service
    return svc.get_setting(db, "folder_rules", default=svc.DEFAULT_FOLDER_RULES) or svc.DEFAULT_FOLDER_RULES
