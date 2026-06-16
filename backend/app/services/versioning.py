"""Phase 10 — entity version + restore service.

Tracks and restores versions of arbitrary entities (invoices,
workflow runs, settings, extraction payloads). Every time a
caller is about to mutate an entity, they call
:meth:`capture_version` *before* the change. After the change
they call :meth:`record_version` to lock the new state into the
history.

The key invariant — "restoring does not delete history" — is
enforced by :meth:`restore_version`: it appends a new
:class:`EntityVersion` row whose ``snapshot_json`` is the old
content and whose ``restored_from_version`` points back at the
source. The caller is expected to apply the restored payload
to the live entity after the call returns.

``workflow_versions`` is a separate table because the snapshot
includes node logs and approvals; we want them queryable
without rebuilding the JSON shape on every read.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models.entity_version import EntityVersion
from ..models.restore_log import RestoreLog
from ..models.workflow_version import WorkflowVersion

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------- capture


def _next_version_number(db: Session, entity_type: str, entity_id: str) -> int:
    """Return the next 1-based version number for this entity."""
    last = (
        db.query(EntityVersion)
        .filter(
            EntityVersion.entity_type == entity_type,
            EntityVersion.entity_id == str(entity_id),
        )
        .order_by(EntityVersion.version_number.desc())
        .first()
    )
    return (last.version_number + 1) if last else 1


def capture_version(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    snapshot: dict[str, Any],
    change_summary: str,
    source_action: str,
    created_by: str,
) -> EntityVersion:
    """Append a new version row. Use this *after* a successful
    mutation so the new state is recorded. We keep the function
    name "capture" because every successful edit produces a
    capture; ``restore_version`` is the only path that mutates an
    existing entity's state from history.
    """
    v_num = _next_version_number(db, entity_type, entity_id)
    row = EntityVersion(
        entity_type=entity_type,
        entity_id=str(entity_id),
        version_number=v_num,
        snapshot_json=snapshot or {},
        change_summary=change_summary,
        source_action=source_action,
        created_by=created_by,
    )
    db.add(row)
    db.flush()
    return row


def list_versions(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    limit: int = 200,
) -> list[EntityVersion]:
    return (
        db.query(EntityVersion)
        .filter(
            EntityVersion.entity_type == entity_type,
            EntityVersion.entity_id == str(entity_id),
        )
        .order_by(EntityVersion.version_number.desc())
        .limit(limit)
        .all()
    )


def get_version(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    version_number: int,
) -> Optional[EntityVersion]:
    return (
        db.query(EntityVersion)
        .filter(
            EntityVersion.entity_type == entity_type,
            EntityVersion.entity_id == str(entity_id),
            EntityVersion.version_number == version_number,
        )
        .first()
    )


# --------------------------------------------------------------------- diff


def diff_snapshots(before: dict, after: dict) -> dict[str, dict[str, Any]]:
    """Return a ``{field: {from, to}}`` map of any key whose value
    changed. Used by the before/after comparison view. Nested
    dicts are flattened one level deep so the UI can render them
    as a simple table.
    """
    out: dict[str, dict[str, Any]] = {}
    keys = set((before or {}).keys()) | set((after or {}).keys())
    for k in keys:
        b = (before or {}).get(k)
        a = (after or {}).get(k)
        if b != a:
            out[k] = {"from": b, "to": a}
    return out


# --------------------------------------------------------------------- restore


def restore_version(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    version_number: int,
    actor: str,
    reason: Optional[str] = None,
) -> tuple[EntityVersion, EntityVersion]:
    """Mark a previous version as restored.

    Returns a ``(source_version, new_version)`` tuple. The new
    version is appended to the history with
    ``restored_from_version = source_version.id`` so the user can
    see "this version was created by restoring v3".

    The caller is responsible for applying ``source_version.snapshot_json``
    to the live entity (e.g. updating an Invoice row) and then
    calling :meth:`capture_version` so the new state is also in
    the history.
    """
    src = get_version(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        version_number=version_number,
    )
    if src is None:
        raise LookupError(
            f"version v{version_number} of {entity_type}/{entity_id} not found"
        )
    # Append the new history row. The actual entity update is
    # done by the caller; this row documents "someone asked to
    # restore v3" before the change commits.
    new_row = capture_version(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        snapshot=src.snapshot_json,
        change_summary=(
            f"Restored from v{src.version_number}"
            + (f" — {reason}" if reason else "")
        ),
        source_action="restore",
        created_by=actor,
    )
    new_row.restored_from_version = src.id
    db.flush()
    db.add(
        RestoreLog(
            entity_type="entity_version",
            entity_id=src.id,
            target_id=str(entity_id),
            restored_from_version=src.version_number,
            restored_to_version=new_row.version_number,
            reason=reason,
            restored_by=actor,
            restored_at=datetime.utcnow(),
        )
    )
    db.flush()
    return src, new_row


# --------------------------------------------------------------------- workflow


def _next_workflow_version(db: Session, workflow_id: int) -> int:
    last = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version_number.desc())
        .first()
    )
    return (last.version_number + 1) if last else 1


def capture_workflow_version(
    db: Session,
    *,
    workflow_id: int,
    workflow_name: str,
    workflow_json: dict[str, Any],
    change_summary: str,
    source_action: str,
    created_by: str,
) -> WorkflowVersion:
    v_num = _next_workflow_version(db, workflow_id)
    row = WorkflowVersion(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        version_number=v_num,
        workflow_json=workflow_json or {},
        change_summary=change_summary,
        source_action=source_action,
        created_by=created_by,
    )
    db.add(row)
    db.flush()
    return row


def list_workflow_versions(
    db: Session,
    *,
    workflow_id: int,
    limit: int = 200,
) -> list[WorkflowVersion]:
    return (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version_number.desc())
        .limit(limit)
        .all()
    )


def get_workflow_version(
    db: Session,
    *,
    workflow_id: int,
    version_number: int,
) -> Optional[WorkflowVersion]:
    return (
        db.query(WorkflowVersion)
        .filter(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version_number == version_number,
        )
        .first()
    )


def restore_workflow_version(
    db: Session,
    *,
    workflow_id: int,
    version_number: int,
    actor: str,
    reason: Optional[str] = None,
) -> tuple[WorkflowVersion, WorkflowVersion]:
    src = get_workflow_version(
        db, workflow_id=workflow_id, version_number=version_number
    )
    if src is None:
        raise LookupError(
            f"workflow version v{version_number} of run {workflow_id} not found"
        )
    new_row = capture_workflow_version(
        db,
        workflow_id=workflow_id,
        workflow_name=src.workflow_name,
        workflow_json=src.workflow_json,
        change_summary=(
            f"Restored from v{src.version_number}"
            + (f" — {reason}" if reason else "")
        ),
        source_action="restore",
        created_by=actor,
    )
    new_row.restored_from_version = src.id
    db.flush()
    db.add(
        RestoreLog(
            entity_type="workflow_version",
            entity_id=src.id,
            target_id=str(workflow_id),
            restored_from_version=src.version_number,
            restored_to_version=new_row.version_number,
            reason=reason,
            restored_by=actor,
            restored_at=datetime.utcnow(),
        )
    )
    db.flush()
    return src, new_row
