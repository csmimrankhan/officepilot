"""Orchestrates text extraction → parsing → validation → persistence.

Phase 5: this module is unchanged in its persistence and audit-log
behaviour. The only addition is that it now consults the configured
:mod:`app.services.engines` registry to choose which parser engine
to run. The default engine is ``existing``, which reproduces the
Phase 1-3 behaviour exactly, so the production code path is
backward compatible.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..config import Settings
from ..models.invoice import Invoice, InvoiceStatus
from ..models.invoice_file import InvoiceFile
from ..models.invoice_line_item import InvoiceLineItem
from .engines import EngineResult, InvoiceParserEngine
from .engines.registry import get_engine
from .parser import parse_invoice_text
from .validator import validate_parsed

logger = logging.getLogger(__name__)


def _is_duplicate(db: Session, file_hash: str) -> Optional[Invoice]:
    return (
        db.query(Invoice)
        .join(InvoiceFile, Invoice.file_id == InvoiceFile.id)
        .filter(InvoiceFile.file_hash == file_hash)
        .order_by(Invoice.id.desc())
        .first()
    )


def _resolve_engine(settings: Settings) -> InvoiceParserEngine:
    """Pick the engine based on settings.parser_engine. Falls back to
    the existing engine if the configured name is unknown."""
    name = (settings.parser_engine or "existing").lower()
    return get_engine(name, settings)


def extract_and_persist(
    db: Session,
    settings: Settings,
    *,
    stored_path: str,
    original_filename: str,
    file_hash: str,
    mime_type: str,
    size: int,
    actor: str = "system",
    record_audit: bool = True,
) -> Invoice:
    """Run the full pipeline. Creates InvoiceFile + Invoice rows; returns the Invoice.

    Side-effects: writes an audit log entry for upload + extraction.
    """
    # 1) duplicate detection
    existing = _is_duplicate(db, file_hash)
    if existing is not None:
        inv = _make_invoice_for_duplicate(
            db=db,
            settings=settings,
            stored_path=stored_path,
            original_filename=original_filename,
            file_hash=file_hash,
            mime_type=mime_type,
            size=size,
            duplicate_of=existing,
        )
        if record_audit:
            from .audit import log_action
            log_action(
                db,
                actor=actor,
                action="upload.duplicate",
                entity_type="invoice",
                entity_id=inv.id,
                details=f"Duplicate of invoice #{existing.id} (file_hash={file_hash[:12]}…)",
            )
        db.commit()
        db.refresh(inv)
        return inv

    # 2) run the selected parser engine. The engine is responsible
    # for text extraction and field parsing. The default engine
    # ("existing") is a thin wrapper around the Phase 1-3 pipeline,
    # so this is backward compatible.
    engine = _resolve_engine(settings)
    er = engine.extract_structure(Path(stored_path), mime_type)
    parsed = er.parsed

    # 3) validate / decide status (uses the engine's parsed fields;
    # the validator itself is unchanged).
    validation = validate_parsed(parsed, settings)
    warnings = (
        list(validation.warnings)
        + [f"source={er.text_source}"]
        + [n for n in er.notes]
        + [w for w in er.warnings if w not in validation.warnings]
    )

    # 4) persist
    file_row = InvoiceFile(
        original_filename=original_filename,
        stored_path=stored_path,
        original_path=stored_path,
        current_path=stored_path,
        file_hash=file_hash,
        mime_type=mime_type,
        size=size,
    )
    db.add(file_row)
    db.flush()

    inv = Invoice(
        vendor_name=parsed.vendor_name,
        invoice_number=parsed.invoice_number,
        invoice_date=parsed.invoice_date,
        due_date=parsed.due_date,
        currency=parsed.currency,
        subtotal=parsed.subtotal,
        tax=parsed.tax,
        total_amount=parsed.total_amount,
        confidence_score=validation.confidence_score,
        warnings_json=warnings,
        # Phase 3: extracted state is the post-validation terminal state
        status=validation.status,
        raw_text=(er.raw_text or "")[:20000] if er.raw_text else None,
        raw_text_source=er.text_source,
        file_id=file_row.id,
    )
    db.add(inv)
    db.flush()

    for idx, li in enumerate(parsed.line_items):
        db.add(
            InvoiceLineItem(
                invoice_id=inv.id,
                description=li.description,
                quantity=li.quantity,
                unit_price=li.unit_price,
                line_total=li.line_total,
                position=idx,
            )
        )

    if record_audit:
        from .audit import log_action
        log_action(
            db,
            actor=actor,
            action="upload",
            entity_type="invoice",
            entity_id=inv.id,
            details=f"Uploaded {original_filename} ({mime_type}, {size} bytes)",
            extra={
                "file_hash": file_hash,
                "extraction_source": er.text_source,
                "used_ocr": er.used_ocr,
                "parser_engine": engine.name,
            },
        )
        log_action(
            db,
            actor=actor,
            action="extraction",
            entity_type="invoice",
            entity_id=inv.id,
            details=(
                f"Extracted with parser={engine.name}, "
                f"confidence={validation.confidence_score}"
            ),
            extra={
                "parser_engine": engine.name,
                "runtime_ms": er.runtime_ms,
                "status": validation.status.value,
                "warnings": warnings,
                "fields": {
                    "vendor_name": inv.vendor_name,
                    "invoice_number": inv.invoice_number,
                    "invoice_date": inv.invoice_date,
                    "total_amount": inv.total_amount,
                    "currency": inv.currency,
                },
                "confidence_per_field": er.confidence.as_dict() if hasattr(er.confidence, "as_dict") else {},
            },
        )

    db.commit()
    db.refresh(inv)
    return inv


def _make_invoice_for_duplicate(
    *,
    db: Session,
    settings: Settings,
    stored_path: str,
    original_filename: str,
    file_hash: str,
    mime_type: str,
    size: int,
    duplicate_of: Invoice,
) -> Invoice:
    file_row = InvoiceFile(
        original_filename=original_filename,
        stored_path=stored_path,
        original_path=stored_path,
        current_path=stored_path,
        file_hash=file_hash,
        mime_type=mime_type,
        size=size,
    )
    db.add(file_row)
    db.flush()
    inv = Invoice(
        vendor_name=duplicate_of.vendor_name,
        invoice_number=duplicate_of.invoice_number,
        invoice_date=duplicate_of.invoice_date,
        due_date=duplicate_of.due_date,
        currency=duplicate_of.currency,
        subtotal=duplicate_of.subtotal,
        tax=duplicate_of.tax,
        total_amount=duplicate_of.total_amount,
        confidence_score=duplicate_of.confidence_score,
        warnings_json=[f"Duplicate of invoice #{duplicate_of.id}"] + list(duplicate_of.warnings_json),
        status=InvoiceStatus.DUPLICATE,
        notes=f"Blocked by duplicate of invoice #{duplicate_of.id}",
        duplicate_of_invoice_id=duplicate_of.id,
        file_id=file_row.id,
    )
    db.add(inv)
    db.flush()
    return inv
