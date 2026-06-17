"""Phase 10 — version history, file snapshots, and restore endpoints.

Routes (all under ``/api``):

- ``GET  /versions/{entity_type}/{entity_id}``             list versions
- ``GET  /versions/{entity_type}/{entity_id}/{version}``   fetch one version
- ``POST /versions/{entity_type}/{entity_id}/restore``     restore a version
- ``GET  /change-timeline/{entity_type}/{entity_id}``      merge version
                                                            history +
                                                            audit log
- ``GET  /file-snapshots``                                 list snapshots
                                                            (filterable by
                                                            file_type /
                                                            path)
- ``GET  /file-snapshots/{id}``                            fetch one
- ``POST /file-snapshots/{id}/restore``                    restore a snapshot
- ``GET  /file-snapshots/{id}/download``                   download the
                                                            snapshot bytes
- ``GET  /workflows/{id}/versions``                        workflow versions
- ``GET  /workflows/{id}/versions/{v}``                    fetch one
- ``POST /workflows/{id}/versions/{v}/restore``            restore a workflow
                                                            version
- ``GET  /restore-logs``                                   recent restore log
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..models.audit_log import AuditLog
from ..models.file_snapshot import FileSnapshot
from ..models.restore_log import RestoreLog
from ..models.workflow_run import WorkflowRun
from ..services import snapshots as snapshot_svc
from ..services import versioning as versioning_svc
from ..services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["versions"])


# --------------------------------------------------------------------- schemas


class VersionRead(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    version_number: int
    snapshot: dict
    change_summary: Optional[str]
    source_action: str
    created_by: str
    restored_from_version: Optional[int]
    created_at: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class VersionDiff(BaseModel):
    field: str
    before: Any
    after: Any


class VersionDiffRead(BaseModel):
    entity_type: str
    entity_id: str
    from_version: int
    to_version: int
    diffs: list[VersionDiff]


class RestoreRequest(BaseModel):
    actor: str = "user"
    reason: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Free-text reason for the restore. Recorded in the audit log.",
    )


class FileSnapshotRead(BaseModel):
    id: int
    file_type: str
    original_path: str
    snapshot_path: str
    action_type: str
    file_hash_before: Optional[str]
    file_hash_after: Optional[str]
    size_bytes: Optional[int]
    created_by: str
    created_at: Optional[str]
    restored_at: Optional[str]
    restore_count: int
    restore_status: str
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class RestoreLogRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    target_id: Optional[str]
    restored_from_version: Optional[int]
    restored_to_version: Optional[int]
    reason: Optional[str]
    restored_by: str
    restored_at: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class WorkflowVersionRead(BaseModel):
    id: int
    workflow_id: int
    workflow_name: str
    version_number: int
    workflow: dict
    change_summary: Optional[str]
    source_action: str
    created_by: str
    restored_from_version: Optional[int]
    created_at: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------- helpers


def _serialize_version(v) -> VersionRead:
    return VersionRead(
        id=v.id,
        entity_type=v.entity_type,
        entity_id=v.entity_id,
        version_number=v.version_number,
        snapshot=v.snapshot_json or {},
        change_summary=v.change_summary,
        source_action=v.source_action,
        created_by=v.created_by,
        restored_from_version=v.restored_from_version,
        created_at=v.created_at.isoformat() if v.created_at else None,
    )


def _serialize_snapshot(s: FileSnapshot) -> FileSnapshotRead:
    return FileSnapshotRead(
        id=s.id,
        file_type=s.file_type,
        original_path=s.original_path,
        snapshot_path=s.snapshot_path,
        action_type=s.action_type,
        file_hash_before=s.file_hash_before,
        file_hash_after=s.file_hash_after,
        size_bytes=s.size_bytes,
        created_by=s.created_by,
        created_at=s.created_at.isoformat() if s.created_at else None,
        restored_at=s.restored_at.isoformat() if s.restored_at else None,
        restore_count=s.restore_count,
        restore_status=s.restore_status,
        notes=s.notes,
    )


def _serialize_workflow_version(v) -> WorkflowVersionRead:
    return WorkflowVersionRead(
        id=v.id,
        workflow_id=v.workflow_id,
        workflow_name=v.workflow_name,
        version_number=v.version_number,
        workflow=v.workflow_json or {},
        change_summary=v.change_summary,
        source_action=v.source_action,
        created_by=v.created_by,
        restored_from_version=v.restored_from_version,
        created_at=v.created_at.isoformat() if v.created_at else None,
    )


def _serialize_restore_log(r: RestoreLog) -> RestoreLogRead:
    return RestoreLogRead(
        id=r.id,
        entity_type=r.entity_type,
        entity_id=r.entity_id,
        target_id=r.target_id,
        restored_from_version=r.restored_from_version,
        restored_to_version=r.restored_to_version,
        reason=r.reason,
        restored_by=r.restored_by,
        restored_at=r.restored_at.isoformat() if r.restored_at else None,
    )


# --------------------------------------------------------------------- restore dispatch


def _apply_entity_restore(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    snapshot: dict,
) -> None:
    """Apply a restored snapshot to the live entity. Each entity
    type knows its own schema. Unknown types raise 501 so the
    caller can surface "restore is not yet wired for X" instead of
    silently no-oping."""
    if entity_type == "invoice":
        from ..models.invoice import Invoice
        from ..models.invoice_line_item import InvoiceLineItem

        try:
            inv_id = int(entity_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid invoice id") from exc
        inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
        if inv is None:
            raise HTTPException(status_code=404, detail=f"invoice {inv_id} not found")
        # Mutate the editable fields from the snapshot.
        for f in (
            "vendor_name",
            "invoice_number",
            "invoice_date",
            "due_date",
            "currency",
            "subtotal",
            "tax",
            "total_amount",
            "notes",
            "status",
        ):
            if f in snapshot:
                setattr(inv, f, snapshot.get(f))
        # Replace line items if present in snapshot.
        if "line_items" in snapshot:
            for li in list(inv.line_items):
                db.delete(li)
            db.flush()
            for idx, item in enumerate(snapshot.get("line_items") or []):
                db.add(
                    InvoiceLineItem(
                        invoice_id=inv.id,
                        description=item.get("description"),
                        quantity=item.get("quantity"),
                        unit_price=item.get("unit_price"),
                        line_total=item.get("line_total"),
                        position=idx,
                    )
                )
        return
    if entity_type == "settings":
        from ..services import settings as settings_svc

        # For entity_id like "folder_rules" the snapshot *is* the
        # value stored under that single settings key. Writing each
        # sub-key as its own setting row would create rows like
        # key="pattern" / value="A/..." which ``get_setting("folder_rules")``
        # never reads. So prefer writing the whole snapshot under
        # the entity_id. If the snapshot is empty or doesn't look
        # like a single settings payload, fall back to per-key
        # writes (future settings namespaces may need that).
        if entity_id and entity_id.strip():
            settings_svc.set_setting(db, entity_id, snapshot)
            return
        for key, value in snapshot.items():
            settings_svc.set_setting(db, key, value)
        return
    if entity_type == "extraction":
        # Extraction snapshots are informational only — they
        # describe what the parser produced. Restoring an
        # extraction is equivalent to "show me what the parser
        # saw at v3"; the live invoice keeps its own data. The
        # caller (UI) is expected to treat this as read-only.
        return
    raise HTTPException(
        status_code=501,
        detail=(
            f"restore is not yet wired for entity_type={entity_type!r}. "
            "Add a branch in _apply_entity_restore."
        ),
    )


def _apply_workflow_restore(
    db: Session,
    *,
    workflow_id: int,
    snapshot: dict,
) -> None:
    run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"workflow run {workflow_id} not found")
    for f in (
        "status",
        "current_node",
        "error_message",
        "state_json",
        "input_json",
        "completed_at",
    ):
        if f in snapshot:
            setattr(run, f, snapshot.get(f))


# --------------------------------------------------------------------- entity versions


@router.get(
    "/versions/{entity_type}/{entity_id}",
    response_model=list[VersionRead],
    summary="List version history for an entity",
)
def list_entity_versions(
    entity_type: str,
    entity_id: str,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    rows = versioning_svc.list_versions(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    return [_serialize_version(r) for r in rows]


@router.get(
    "/versions/{entity_type}/{entity_id}/{version_number}",
    response_model=VersionRead,
    summary="Fetch a single version (with its full JSON snapshot)",
)
def get_entity_version(
    entity_type: str,
    entity_id: str,
    version_number: int,
    db: Session = Depends(get_db),
):
    v = versioning_svc.get_version(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        version_number=version_number,
    )
    if v is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"version v{version_number} of {entity_type}/{entity_id} not found"
            ),
        )
    return _serialize_version(v)


@router.get(
    "/versions/{entity_type}/{entity_id}/diff",
    response_model=VersionDiffRead,
    summary="Compare two versions (or version -> current)",
)
def diff_entity_versions(
    entity_type: str,
    entity_id: str,
    from_version: int = Query(..., alias="from"),
    to_version: Optional[int] = Query(
        None,
        alias="to",
        description="If omitted, diff against the latest version.",
    ),
    db: Session = Depends(get_db),
):
    a = versioning_svc.get_version(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        version_number=from_version,
    )
    if a is None:
        raise HTTPException(
            status_code=404,
            detail=f"version v{from_version} not found",
        )
    if to_version is None:
        # Default: latest.
        latest = versioning_svc.list_versions(
            db, entity_type=entity_type, entity_id=entity_id, limit=1
        )
        if not latest:
            raise HTTPException(status_code=404, detail="no versions to diff against")
        b = latest[0]
    else:
        b = versioning_svc.get_version(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            version_number=to_version,
        )
        if b is None:
            raise HTTPException(
                status_code=404,
                detail=f"version v{to_version} not found",
            )
    diffs_map = versioning_svc.diff_snapshots(a.snapshot_json, b.snapshot_json)
    diffs = [VersionDiff(field=k, before=v["from"], after=v["to"]) for k, v in diffs_map.items()]
    return VersionDiffRead(
        entity_type=entity_type,
        entity_id=entity_id,
        from_version=from_version,
        to_version=b.version_number,
        diffs=diffs,
    )


@router.post(
    "/versions/{entity_type}/{entity_id}/restore",
    response_model=VersionRead,
    summary="Restore an entity to a previous version",
)
def restore_entity_version(
    entity_type: str,
    entity_id: str,
    payload: RestoreRequest,
    version_number: int = Query(..., alias="version"),
    db: Session = Depends(get_db),
):
    try:
        src, new_row = versioning_svc.restore_version(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            version_number=version_number,
            actor=payload.actor,
            reason=payload.reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Apply the snapshot to the live entity. If the entity type
    # has no restore handler, _apply_entity_restore raises 501 and
    # the history row we just appended stays — restoring an
    # unknown type is a configuration error, not a silent no-op.
    _apply_entity_restore(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        snapshot=src.snapshot_json,
    )

    # Audit log entry — every restore writes one (Phase 10
    # safety rule: "every restore action creates audit log").
    log_action(
        db,
        actor=payload.actor,
        action="version.restore",
        entity_type=entity_type,
        entity_id=(
            int(entity_id) if entity_id.isdigit() else None
        ),
        details=(
            f"Restored {entity_type}/{entity_id} to v{src.version_number} "
            f"(new v{new_row.version_number})"
        ),
        extra={
            "source_version_id": src.id,
            "source_version_number": src.version_number,
            "new_version_id": new_row.id,
            "new_version_number": new_row.version_number,
            "reason": payload.reason,
        },
    )
    db.commit()
    db.refresh(new_row)
    return _serialize_version(new_row)


# --------------------------------------------------------------------- change timeline


@router.get(
    "/change-timeline/{entity_type}/{entity_id}",
    summary="Merge version history + audit log for an entity",
)
def change_timeline(
    entity_type: str,
    entity_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return a single chronological list of every change for the
    given entity, mixing entity_versions rows and audit_logs rows.
    The UI uses this to render a single "Change Timeline" tab."""

    # Map "invoice" -> audit_log.entity_type "invoice" for the
    # merge; for workflow we use the run id; for settings we
    # query by entity_type and entity_id is None.
    audit_entity_id: Optional[int] = None
    if entity_id.isdigit():
        audit_entity_id = int(entity_id)

    versions = versioning_svc.list_versions(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    audit_q = db.query(AuditLog).filter(AuditLog.entity_type == entity_type)
    if audit_entity_id is not None:
        audit_q = audit_q.filter(AuditLog.entity_id == audit_entity_id)
    audits = audit_q.order_by(AuditLog.id.desc()).limit(limit).all()

    merged: list[dict] = []
    for v in versions:
        merged.append(
            {
                "kind": "version",
                "id": v.id,
                "version_number": v.version_number,
                "change_summary": v.change_summary,
                "source_action": v.source_action,
                "actor": v.created_by,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "restored_from_version": v.restored_from_version,
                "snapshot": v.snapshot_json or {},
            }
        )
    for a in audits:
        merged.append(
            {
                "kind": "audit",
                "id": a.id,
                "action": a.action,
                "details": a.details,
                "actor": a.actor,
                "created_at": a.timestamp.isoformat() if a.timestamp else None,
                "before": a.before_data_json,
                "after": a.after_data_json,
            }
        )
    # Newest first.
    merged.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return merged[:limit]


# --------------------------------------------------------------------- file snapshots


@router.get(
    "/file-snapshots",
    response_model=list[FileSnapshotRead],
    summary="List file snapshots",
)
def list_file_snapshots(
    file_type: Optional[str] = Query(None),
    original_path: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(FileSnapshot).order_by(FileSnapshot.id.desc())
    if file_type:
        q = q.filter(FileSnapshot.file_type == file_type)
    if original_path:
        q = q.filter(FileSnapshot.original_path == original_path)
    rows = q.limit(limit).all()
    return [_serialize_snapshot(r) for r in rows]


@router.get(
    "/file-snapshots/{snapshot_id}",
    response_model=FileSnapshotRead,
    summary="Fetch a single file snapshot metadata",
)
def get_file_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    s = db.query(FileSnapshot).filter(FileSnapshot.id == snapshot_id).first()
    if s is None:
        raise HTTPException(status_code=404, detail=f"snapshot {snapshot_id} not found")
    return _serialize_snapshot(s)


@router.get(
    "/file-snapshots/{snapshot_id}/download",
    summary="Download the snapshot bytes",
)
def download_file_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    s = db.query(FileSnapshot).filter(FileSnapshot.id == snapshot_id).first()
    if s is None:
        raise HTTPException(status_code=404, detail=f"snapshot {snapshot_id} not found")
    p = Path(s.snapshot_path)
    if not p.exists():
        raise HTTPException(
            status_code=410,
            detail="snapshot file is missing on disk",
        )
    return FileResponse(
        path=str(p),
        filename=p.name,
        media_type="application/octet-stream",
    )


@router.post(
    "/file-snapshots/{snapshot_id}/restore",
    response_model=FileSnapshotRead,
    summary="Restore a file snapshot to its original path",
)
def restore_file_snapshot(
    snapshot_id: int,
    payload: RestoreRequest,
    target_path: Optional[str] = Query(
        None,
        description=(
            "Optional override path; if absent, the snapshot is "
            "restored to its ``original_path``."
        ),
    ),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    s = db.query(FileSnapshot).filter(FileSnapshot.id == snapshot_id).first()
    if s is None:
        raise HTTPException(status_code=404, detail=f"snapshot {snapshot_id} not found")
    src = Path(s.snapshot_path)
    if not src.exists():
        s.restore_status = "missing"
        db.commit()
        raise HTTPException(
            status_code=410,
            detail="snapshot file is missing on disk; cannot restore",
        )
    target = Path(target_path) if target_path else Path(s.original_path)
    snapshot_svc.restore_snapshot(src, target=target)

    from datetime import datetime as _dt
    s.restored_at = _dt.utcnow()
    s.restore_count = (s.restore_count or 0) + 1
    s.restore_status = "restored"
    # Audit log + restore_logs row.
    log_action(
        db,
        actor=payload.actor,
        action="file_snapshot.restore",
        entity_type="file_snapshot",
        entity_id=s.id,
        details=(
            f"Restored snapshot #{s.id} ({s.file_type}) → {target}"
            + (f" — {payload.reason}" if payload.reason else "")
        ),
        extra={
            "file_type": s.file_type,
            "original_path": s.original_path,
            "target_path": str(target),
            "snapshot_id": s.id,
            "reason": payload.reason,
        },
    )
    db.add(
        RestoreLog(
            entity_type="file_snapshot",
            entity_id=s.id,
            target_id=s.original_path,
            restored_from_version=None,
            restored_to_version=None,
            reason=payload.reason,
            restored_by=payload.actor,
            restored_at=_dt.utcnow(),
        )
    )
    db.commit()
    db.refresh(s)
    return _serialize_snapshot(s)


# --------------------------------------------------------------------- workflow versions


@router.get(
    "/workflows/{workflow_id}/versions",
    response_model=list[WorkflowVersionRead],
    summary="List version history for a workflow run",
)
def list_workflow_versions(
    workflow_id: int,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    if db.query(WorkflowRun).filter(WorkflowRun.id == workflow_id).first() is None:
        raise HTTPException(status_code=404, detail=f"workflow run {workflow_id} not found")
    rows = versioning_svc.list_workflow_versions(
        db, workflow_id=workflow_id, limit=limit
    )
    return [_serialize_workflow_version(r) for r in rows]


@router.get(
    "/workflows/{workflow_id}/versions/{version_number}",
    response_model=WorkflowVersionRead,
)
def get_workflow_version(
    workflow_id: int,
    version_number: int,
    db: Session = Depends(get_db),
):
    v = versioning_svc.get_workflow_version(
        db, workflow_id=workflow_id, version_number=version_number
    )
    if v is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"workflow version v{version_number} of run {workflow_id} not found"
            ),
        )
    return _serialize_workflow_version(v)


@router.post(
    "/workflows/{workflow_id}/versions/{version_number}/restore",
    response_model=WorkflowVersionRead,
    summary="Restore a workflow run to a previous version",
)
def restore_workflow_version(
    workflow_id: int,
    version_number: int,
    payload: RestoreRequest,
    db: Session = Depends(get_db),
):
    try:
        src, new_row = versioning_svc.restore_workflow_version(
            db,
            workflow_id=workflow_id,
            version_number=version_number,
            actor=payload.actor,
            reason=payload.reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _apply_workflow_restore(
        db, workflow_id=workflow_id, snapshot=src.workflow_json
    )
    log_action(
        db,
        actor=payload.actor,
        action="workflow.restore",
        entity_type="workflow_run",
        entity_id=workflow_id,
        details=(
            f"Restored workflow run #{workflow_id} to v{src.version_number} "
            f"(new v{new_row.version_number})"
        ),
        extra={
            "source_version_id": src.id,
            "source_version_number": src.version_number,
            "new_version_id": new_row.id,
            "new_version_number": new_row.version_number,
            "reason": payload.reason,
        },
    )
    db.commit()
    db.refresh(new_row)
    return _serialize_workflow_version(new_row)


# --------------------------------------------------------------------- restore logs


@router.get(
    "/restore-logs",
    response_model=list[RestoreLogRead],
    summary="Recent restore activity (audit-style)",
)
def list_restore_logs(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(RestoreLog)
        .order_by(RestoreLog.id.desc())
        .limit(limit)
        .all()
    )
    return [_serialize_restore_log(r) for r in rows]
