"""Application settings service (Phase 3).

A small key/value store with JSON values. Use :func:`get_setting` to read
with a default; :func:`set_setting` to write; :func:`update_setting` to
merge fields into an existing object. Every write is logged to the
audit trail by the caller (the routers do this explicitly so they can
attach before/after diffs).
"""

from __future__ import annotations

import copy
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models.setting import Setting


# Default folder rules. Pattern tokens: {year}, {month}, {vendor},
# {invoice_number}, {total}, {currency}, {date}, {source}.
DEFAULT_FOLDER_RULES: dict = {
    "enabled": True,
    "pattern": "Invoices/{year}/{month}/{vendor}_{invoice_number}_{total}_{currency}.{ext}",
    "conflict_strategy": "suffix",   # "suffix" (file_1.pdf) or "skip" or "overwrite"
    "move_on_approve": True,         # auto-move file on approval
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "folder_rules": DEFAULT_FOLDER_RULES,
}


def get_setting(db: Session, key: str, default: Any = None) -> Any:
    row = db.query(Setting).filter(Setting.key == key).first()
    if row is None:
        return copy.deepcopy(default) if default is not None else None
    return copy.deepcopy(row.value_json)


def get_or_create(db: Session, key: str, default: Any = None) -> Setting:
    """Return the row, creating it with the default value if missing."""
    row = db.query(Setting).filter(Setting.key == key).first()
    if row is not None:
        return row
    if default is None:
        default = DEFAULT_SETTINGS.get(key)
    row = Setting(key=key, value_json=copy.deepcopy(default) if default is not None else {})
    db.add(row)
    db.flush()
    return row


def set_setting(db: Session, key: str, value: Any) -> dict:
    """Set the JSON value for ``key`` and return the new value (deep-copied)."""
    row = db.query(Setting).filter(Setting.key == key).first()
    if row is None:
        row = Setting(key=key, value_json=copy.deepcopy(value))
        db.add(row)
    else:
        row.value_json = copy.deepcopy(value)
    db.flush()
    return copy.deepcopy(row.value_json)


def update_setting(db: Session, key: str, patch: dict) -> tuple[Setting, Any, Any]:
    """Merge ``patch`` into the existing JSON value. Returns
    ``(row, before, after)`` so the caller can log a diff."""
    row = get_or_create(db, key, default=DEFAULT_SETTINGS.get(key, {}))
    before = copy.deepcopy(row.value_json or {})
    after = {**before, **patch}
    row.value_json = after
    db.flush()
    return row, before, after


def diff_dicts(before: Optional[dict], after: Optional[dict]) -> dict:
    """Thin wrapper around :func:`app.services.audit.diff_dicts` so callers
    that already import the settings service don't have to know which module
    owns the helper."""
    from .audit import diff_dicts as _audit_diff

    return _audit_diff(before, after)
