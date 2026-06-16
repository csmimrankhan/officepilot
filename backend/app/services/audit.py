"""Append-only audit log writer (Phase 1 + Phase 3)."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models.audit_log import AuditLog


def log_action(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: Optional[int],
    details: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
    before_data: Optional[dict[str, Any]] = None,
    after_data: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """Write an audit log entry.

    ``before_data`` / ``after_data`` are optional structured diffs (Phase 3).
    Callers may pass either or both, or neither.
    """
    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        extra_json=extra or {},
        before_data_json=before_data,
        after_data_json=after_data,
    )
    db.add(entry)
    db.commit()
    return entry


def diff_dicts(before: Optional[dict], after: Optional[dict]) -> dict:
    """Return a small ``{field: {from, to}}`` map for any keys whose value
    changed between ``before`` and ``after``. Useful for edit-audit entries.
    """
    out: dict = {}
    keys = set((before or {}).keys()) | set((after or {}).keys())
    for k in keys:
        b = (before or {}).get(k)
        a = (after or {}).get(k)
        if b != a:
            out[k] = {"from": b, "to": a}
    return out
