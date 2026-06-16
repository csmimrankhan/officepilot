"""Invoice HTTP API (Phases 1-3)."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from ..config import Settings, get_settings
from ..db import get_db
from ..models.audit_log import AuditLog
from ..models.invoice import Invoice, InvoiceStatus
from ..models.invoice_file import InvoiceFile
from ..models.invoice_line_item import InvoiceLineItem
from ..schemas.invoice import (
    AuditLogRead,
    InvoiceFileRead,
    InvoiceLineItemRead,
    InvoiceRead,
    InvoiceUpdate,
    ReviewQueueItem,
    ReviewQueueRead,
)
from ..services import excel_export, extraction, organizer, settings as settings_svc, storage
from ..services import versioning as versioning_svc
from ..services.audit import log_action
from ..services.snapshots import create_snapshot
from ..services.storage import UnsupportedFileType
from ..models.file_snapshot import FileSnapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


# --------------------------------------------------------------------- helpers


def _load_invoice(db: Session, invoice_id: int) -> Invoice:
    inv = (
        db.query(Invoice)
        .options(selectinload(Invoice.file), selectinload(Invoice.line_items))
        .filter(Invoice.id == invoice_id)
        .first()
    )
    if inv is None:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    return inv


def _serialize(inv: Invoice) -> InvoiceRead:
    return InvoiceRead.model_validate(inv)


def _diff_invoice_fields(before: Invoice, payload: InvoiceUpdate) -> dict:
    diff: dict = {}
    for field in (
        "vendor_name",
        "invoice_number",
        "invoice_date",
        "due_date",
        "currency",
        "subtotal",
        "tax",
        "total_amount",
        "notes",
    ):
        new = getattr(payload, field, None)
        if new is None:
            continue
        old = getattr(before, field)
        if old != new:
            diff[field] = {"from": old, "to": new}
    return diff


def _capture_invoice_version(
    db: Session,
    *,
    inv: Invoice,
    source_action: str,
    actor: str,
    change_summary: Optional[str] = None,
) -> None:
    """Phase 10: append a new entity_versions row for this invoice
    AFTER the mutation has been applied. Caller is expected to
    ``db.commit()`` afterward. The snapshot is the full serialized
    invoice (header fields + line items) so the UI can render
    before/after diffs and a restore is fully self-contained."""
    snapshot = {
        "vendor_name": inv.vendor_name,
        "invoice_number": inv.invoice_number,
        "invoice_date": inv.invoice_date if isinstance(inv.invoice_date, str) else (
            inv.invoice_date.isoformat() if inv.invoice_date else None
        ),
        "due_date": inv.due_date if isinstance(inv.due_date, str) else (
            inv.due_date.isoformat() if inv.due_date else None
        ),
        "currency": inv.currency,
        "subtotal": inv.subtotal,
        "tax": inv.tax,
        "total_amount": inv.total_amount,
        "notes": inv.notes,
        "status": inv.status.value if inv.status else None,
        "line_items": [
            {
                "description": li.description,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "line_total": li.line_total,
                "position": li.position,
            }
            for li in inv.line_items
        ],
    }
    versioning_svc.capture_version(
        db,
        entity_type="invoice",
        entity_id=str(inv.id),
        snapshot=snapshot,
        source_action=source_action,
        created_by=actor,
        change_summary=change_summary,
    )


def _auto_organize(
    db: Session,
    settings_app: Settings,
    inv: Invoice,
    *,
    actor: str,
) -> Optional[organizer.OrganizeResult]:
    """Run the configured folder rule on this invoice (if enabled and
    a file is attached). Returns the result or None when no-op."""
    if inv.file is None:
        return None
    rules = settings_svc.get_setting(db, "folder_rules", default=settings_svc.DEFAULT_FOLDER_RULES)
    if not rules.get("enabled", True) or not rules.get("move_on_approve", True):
        return None
    source = inv.file.current_path or inv.file.stored_path
    if not source:
        return None
    before_path = source
    # Phase 10: snapshot the source file bytes BEFORE the
    # move/rename. Restoring this snapshot puts the bytes back at
    # `before_path`; the file path itself is also captured in the
    # entity_version on the invoice.
    try:
        from datetime import datetime as _dt
        snap = create_snapshot(
            source=Path(before_path),
            snapshots_root=settings.snapshots_dir,
            file_type="invoice_file",
        )
        if snap is not None:
            db.add(
                FileSnapshot(
                    file_type="invoice_file",
                    original_path=before_path,
                    snapshot_path=str(snap.snapshot_path),
                    action_type="organizer.move",
                    created_by=actor,
                    restore_status="active",
                    file_hash_before=snap.file_hash,
                    size_bytes=snap.size_bytes,
                    notes=(
                        f"Pre-move snapshot for invoice #{inv.id}"
                    ),
                )
            )
            db.flush()
    except Exception as _exc:  # pragma: no cover — best-effort
        logger.warning("Failed to snapshot pre-move file: %s", _exc)
    result = organizer.organize(
        settings_app.storage_root,
        inv,
        source_path=source,
        pattern=rules.get("pattern") or settings_svc.DEFAULT_FOLDER_RULES["pattern"],
        conflict_strategy=rules.get("conflict_strategy", "suffix"),
    )
    if result.moved:
        inv.file.organized_path = result.target_path
        inv.file.current_path = result.target_path
        log_action(
            db,
            actor=actor,
            action="organize_file",
            entity_type="invoice",
            entity_id=inv.id,
            details=f"Moved {Path(before_path).name} → {Path(result.target_path).name}",
            before_data={"current_path": before_path},
            after_data={"current_path": result.target_path, "organized_path": result.target_path},
        )
    else:
        log_action(
            db,
            actor=actor,
            action="organize_file.skipped",
            entity_type="invoice",
            entity_id=inv.id,
            details=f"Organize skipped: {result.skipped_reason}",
            extra={"source": before_path, "target": result.target_path},
        )
    return result


# --------------------------------------------------------------------- routes


@router.post("/upload", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def upload_invoice(
    file: UploadFile = File(...),
    actor: str = Query("user", description="Who is performing the action (audit actor)"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Accept a single PDF / PNG / JPG / JPEG and run the extraction pipeline."""
    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    size_mb = len(raw) / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB > limit {settings.max_upload_mb} MB)",
        )

    try:
        stored = storage.store_upload(
            settings, data=raw, original_filename=file.filename or "upload"
        )
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    inv = extraction.extract_and_persist(
        db,
        settings,
        stored_path=stored.stored_path,
        original_filename=stored.original_filename,
        file_hash=stored.file_hash,
        mime_type=stored.mime_type,
        size=stored.size,
        actor=actor,
    )
    # Phase 10: capture v1 of this invoice so the Version History
    # tab has a baseline (the parser result is itself a version).
    db.refresh(inv)
    _capture_invoice_version(
        db,
        inv=inv,
        source_action="parser.extract",
        actor=actor,
        change_summary="Initial extraction",
    )
    db.commit()
    db.refresh(inv)
    return _serialize(inv)


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    status_filter: Optional[InvoiceStatus] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Invoice).options(
        selectinload(Invoice.file), selectinload(Invoice.line_items)
    )
    if status_filter is not None:
        q = q.filter(Invoice.status == status_filter)
    q = q.order_by(Invoice.id.desc()).offset(offset).limit(limit)
    return [_serialize(i) for i in q.all()]


@router.get("/review-queue", response_model=ReviewQueueRead)
def review_queue(
    limit_per_status: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return invoices grouped by status, with counts. Designed for the
    Review Queue UI which renders tabs/sections per status."""
    by_status: dict[str, list[ReviewQueueItem]] = {}
    counts: dict[str, int] = {}

    # All relevant statuses (skip the transient "imported"/"extracting" since
    # they shouldn't sit in the queue — the pipeline moves through them
    # quickly).
    queue_statuses = [
        InvoiceStatus.NEEDS_REVIEW,
        InvoiceStatus.READY_FOR_APPROVAL,
        InvoiceStatus.APPROVED,
        InvoiceStatus.REJECTED,
        InvoiceStatus.DUPLICATE,
        InvoiceStatus.EXPORTED,
    ]

    for st in queue_statuses:
        rows = (
            db.query(Invoice)
            .options(selectinload(Invoice.file))
            .filter(Invoice.status == st)
            .order_by(Invoice.updated_at.desc())
            .limit(limit_per_status)
            .all()
        )
        by_status[st.value] = [
            ReviewQueueItem(
                id=r.id,
                status=r.status,
                vendor_name=r.vendor_name,
                invoice_number=r.invoice_number,
                invoice_date=r.invoice_date,
                total_amount=r.total_amount,
                currency=r.currency,
                confidence_score=r.confidence_score,
                updated_at=r.updated_at,
                source=r.file.source if r.file else None,
                duplicate_of_invoice_id=r.duplicate_of_invoice_id,
                approved_by=r.approved_by,
                approved_at=r.approved_at,
                rejected_reason=r.rejected_reason,
            )
            for r in rows
        ]
        count = (
            db.query(func.count(Invoice.id))
            .filter(Invoice.status == st)
            .scalar()
        )
        counts[st.value] = int(count or 0)

    return ReviewQueueRead(by_status=by_status, counts=counts)


@router.get("/export/excel")
def export_excel(
    actor: str = Query("user"),
    include_rejected: bool = Query(False, description="Admin override to include rejected/duplicate rows. Default: false."),
    include_duplicate: bool = Query(False, description="Admin override to include duplicate rows. Default: false."),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    path = excel_export.build_excel(
        db, settings,
        include_rejected=include_rejected,
        include_duplicate=include_duplicate,
    )
    log_action(
        db,
        actor=actor,
        action="export.excel",
        entity_type="invoice",
        entity_id=None,
        details=f"Exported approved invoices to {path.name}",
        extra={
            "path": str(path),
            "include_rejected": include_rejected,
            "include_duplicate": include_duplicate,
        },
    )
    # Mark the included rows as 'exported' for the audit trail. We do this
    # *after* the file is built so a failed export does not change status.
    exported_ids = excel_export.mark_exported(db, include_rejected=include_rejected, include_duplicate=include_duplicate)
    log_action(
        db,
        actor=actor,
        action="mark_exported",
        entity_type="invoice",
        entity_id=None,
        details=f"Marked {len(exported_ids)} invoice(s) as exported.",
        extra={"invoice_ids": exported_ids},
    )
    db.commit()
    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    return _serialize(_load_invoice(db, invoice_id))


@router.get("/{invoice_id}/file")
def get_invoice_file(
    invoice_id: int,
    inline: bool = Query(True, description="Send with Content-Disposition: inline (for preview)"),
    db: Session = Depends(get_db),
):
    inv = _load_invoice(db, invoice_id)
    if inv.file is None:
        raise HTTPException(status_code=404, detail="No file attached to this invoice")
    # Prefer the current/organized path if present.
    p = Path(inv.file.current_path or inv.file.stored_path)
    if not p.exists():
        raise HTTPException(status_code=410, detail="Stored file is missing on disk")
    disposition = "inline" if inline else "attachment"
    return FileResponse(
        path=str(p),
        media_type=inv.file.mime_type or "application/octet-stream",
        filename=inv.file.original_filename,
        content_disposition_type=disposition,
    )


@router.get("/{invoice_id}/audit", response_model=list[AuditLogRead])
def invoice_audit_timeline(
    invoice_id: int,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Return every audit log entry that references this invoice, newest first."""
    inv = _load_invoice(db, invoice_id)
    q = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type == "invoice")
        .filter(AuditLog.entity_id == inv.id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
    )
    return [AuditLogRead.model_validate(r) for r in q.all()]


@router.patch("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    actor: str = Query("user"),
    db: Session = Depends(get_db),
):
    inv = _load_invoice(db, invoice_id)
    # Snapshot relevant fields for the before/after diff.
    before = {
        "vendor_name": inv.vendor_name,
        "invoice_number": inv.invoice_number,
        "invoice_date": inv.invoice_date,
        "due_date": inv.due_date,
        "currency": inv.currency,
        "subtotal": inv.subtotal,
        "tax": inv.tax,
        "total_amount": inv.total_amount,
        "notes": inv.notes,
    }
    diff = _diff_invoice_fields(inv, payload)
    if payload.vendor_name is not None: inv.vendor_name = payload.vendor_name
    if payload.invoice_number is not None: inv.invoice_number = payload.invoice_number
    if payload.invoice_date is not None: inv.invoice_date = payload.invoice_date
    if payload.due_date is not None: inv.due_date = payload.due_date
    if payload.currency is not None: inv.currency = payload.currency
    if payload.subtotal is not None: inv.subtotal = payload.subtotal
    if payload.tax is not None: inv.tax = payload.tax
    if payload.total_amount is not None: inv.total_amount = payload.total_amount
    if payload.notes is not None: inv.notes = payload.notes

    if payload.line_items is not None:
        # Replace the line items list with user-provided values.
        for li in list(inv.line_items):
            db.delete(li)
        db.flush()
        for idx, item in enumerate(payload.line_items):
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

    after = {
        "vendor_name": inv.vendor_name,
        "invoice_number": inv.invoice_number,
        "invoice_date": inv.invoice_date,
        "due_date": inv.due_date,
        "currency": inv.currency,
        "subtotal": inv.subtotal,
        "tax": inv.tax,
        "total_amount": inv.total_amount,
        "notes": inv.notes,
    }

    # After edits, the user takes responsibility → mark as ready_for_approval
    # unless duplicate/rejected/approved.
    prev_status = inv.status
    if inv.status not in (InvoiceStatus.DUPLICATE, InvoiceStatus.REJECTED, InvoiceStatus.APPROVED):
        inv.status = InvoiceStatus.READY_FOR_APPROVAL

    log_action(
        db,
        actor=actor,
        action="edit",
        entity_type="invoice",
        entity_id=inv.id,
        details=f"Edited invoice #{inv.id}",
        extra={"line_items_replaced": payload.line_items is not None},
        before_data={**before, "status": prev_status.value},
        after_data={**after, "status": inv.status.value},
    )
    _capture_invoice_version(
        db,
        inv=inv,
        source_action="user.edit",
        actor=actor,
        change_summary=(
            f"Edited {len(diff)} field(s)"
            if diff
            else "Edit (no field changes detected)"
        ),
    )
    db.commit()
    db.refresh(inv)
    return _serialize(inv)


@router.post("/{invoice_id}/approve", response_model=InvoiceRead)
def approve_invoice(
    invoice_id: int,
    actor: str = Query("user"),
    auto_organize: bool = Query(True, description="Move file to the organized folder using the configured pattern."),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    inv = _load_invoice(db, invoice_id)
    if inv.status == InvoiceStatus.DUPLICATE:
        raise HTTPException(status_code=409, detail="Cannot approve a duplicate invoice")
    before_status = inv.status
    inv.status = InvoiceStatus.APPROVED
    inv.approved_by = actor
    inv.approved_at = datetime.utcnow()
    log_action(
        db,
        actor=actor,
        action="approve",
        entity_type="invoice",
        entity_id=inv.id,
        details=f"Approved invoice #{inv.id}",
        before_data={"status": before_status.value},
        after_data={"status": inv.status.value, "approved_by": actor, "approved_at": inv.approved_at.isoformat()},
    )
    if auto_organize:
        _auto_organize(db, settings, inv, actor=actor)
    _capture_invoice_version(
        db,
        inv=inv,
        source_action="user.approve",
        actor=actor,
        change_summary=f"Status: {before_status.value} → APPROVED",
    )
    db.commit()
    db.refresh(inv)
    return _serialize(inv)


@router.post("/{invoice_id}/reject", response_model=InvoiceRead)
def reject_invoice(
    invoice_id: int,
    actor: str = Query("user"),
    reason: Optional[str] = Query(None, description="Required reason for rejection (recorded on the invoice + audit log)."),
    db: Session = Depends(get_db),
):
    inv = _load_invoice(db, invoice_id)
    if not reason or not reason.strip():
        raise HTTPException(
            status_code=400,
            detail="A reason is required to reject an invoice.",
        )
    before_status = inv.status
    inv.status = InvoiceStatus.REJECTED
    inv.rejected_reason = reason.strip()
    log_action(
        db,
        actor=actor,
        action="reject",
        entity_type="invoice",
        entity_id=inv.id,
        details=f"Rejected invoice #{inv.id}",
        before_data={"status": before_status.value},
        after_data={"status": inv.status.value, "rejected_reason": inv.rejected_reason},
    )
    _capture_invoice_version(
        db,
        inv=inv,
        source_action="user.reject",
        actor=actor,
        change_summary=f"Status: {before_status.value} → REJECTED — {inv.rejected_reason}",
    )
    db.commit()
    db.refresh(inv)
    return _serialize(inv)


@router.post("/{invoice_id}/mark-duplicate", response_model=InvoiceRead)
def mark_invoice_duplicate(
    invoice_id: int,
    duplicate_of: int = Query(..., description="ID of the original invoice this is a duplicate of."),
    actor: str = Query("user"),
    db: Session = Depends(get_db),
):
    inv = _load_invoice(db, invoice_id)
    if inv.id == duplicate_of:
        raise HTTPException(
            status_code=400,
            detail="An invoice cannot be a duplicate of itself.",
        )
    original = _load_invoice(db, duplicate_of)
    if original.status == InvoiceStatus.DUPLICATE:
        raise HTTPException(
            status_code=400,
            detail="The target invoice is itself a duplicate. Mark against the original instead.",
        )
    before_status = inv.status
    inv.status = InvoiceStatus.DUPLICATE
    inv.duplicate_of_invoice_id = original.id
    log_action(
        db,
        actor=actor,
        action="mark_duplicate",
        entity_type="invoice",
        entity_id=inv.id,
        details=f"Marked invoice #{inv.id} as duplicate of #{original.id}",
        before_data={"status": before_status.value},
        after_data={"status": inv.status.value, "duplicate_of_invoice_id": original.id},
    )
    _capture_invoice_version(
        db,
        inv=inv,
        source_action="user.mark_duplicate",
        actor=actor,
        change_summary=(
            f"Status: {before_status.value} → DUPLICATE (of #{original.id})"
        ),
    )
    db.commit()
    db.refresh(inv)
    return _serialize(inv)


@router.post("/{invoice_id}/organize-file", response_model=InvoiceRead)
def organize_invoice_file(
    invoice_id: int,
    actor: str = Query("user"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Manually trigger the folder-rule organizer for an invoice. Idempotent:
    if the file is already at the organized path, this is a no-op (but still
    logged)."""
    inv = _load_invoice(db, invoice_id)
    result = _auto_organize(db, settings, inv, actor=actor)
    if result is None:
        raise HTTPException(
            status_code=409,
            detail="No file to organize, or folder rules are disabled.",
        )
    db.commit()
    db.refresh(inv)
    return _serialize(inv)
