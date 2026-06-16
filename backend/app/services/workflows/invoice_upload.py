"""Phase 6 — Graph 1: invoice_upload_processing_graph.

Mirrors the existing :func:`app.services.extraction.extract_and_persist`
pipeline as a LangGraph ``StateGraph`` so it can be paused, retried,
and audited. This is the workflow version of the upload endpoint —
the existing ``POST /api/invoices/upload`` keeps working unchanged.

Nodes (in order):

1. ``store_file``           — copy the uploaded file into the
                              configured storage dir and compute
                              its hash.
2. ``detect_duplicate``     — check by file_hash; if duplicate,
                              set the run's final status to
                              ``DUPLICATE`` and the rest of the
                              graph becomes a no-op.
3. ``parse_invoice``        — run the selected parser engine.
4. ``validate_fields``      — apply the cross-field validator.
5. ``route_by_confidence``  — branching: high-confidence invoices
                              go to ``create_review_item`` with
                              status READY_FOR_APPROVAL, low go
                              with NEEDS_REVIEW.
6. ``create_review_item``   — persist the Invoice + line items.
7. ``audit_log``            — write the workflow-level audit row.

Handlers take ``(state, runner)`` and return a partial state
update; the runner handles persistence, logging, and approval
side effects.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ..engines import EngineResult
from ..engines.registry import get_engine
from ..extraction import _is_duplicate
from ..parser import parse_invoice_text
from ..text_extraction import extract_text
from ..validator import validate_parsed

logger = logging.getLogger(__name__)


class InvoiceUploadState(TypedDict, total=False):
    """State carried by the invoice-upload graph.

    All fields are optional (``total=False``) because every node
    may add to or transform the state. Keys prefixed with ``_`` are
    private to the runner.
    """

    # ---- input (set by the API router) ----
    actor: str
    file_path: str
    original_filename: str
    file_hash: str
    mime_type: str
    size: int

    # ---- intermediate ----
    stored_path: str
    duplicate_of_id: int
    is_duplicate: bool

    parsed_json: dict
    raw_text: str
    text_source: str
    used_ocr: bool
    confidence_per_field: dict
    engine_runtime_ms: float
    engine_name: str

    confidence_score: float
    status: str                 # READY_FOR_APPROVAL / NEEDS_REVIEW / DUPLICATE
    warnings: list[str]

    invoice_id: int
    error: str


INVOICE_UPLOAD_NODES = [
    "store_file",
    "detect_duplicate",
    "parse_invoice",
    "validate_fields",
    "route_by_confidence",
    "create_review_item",
    "audit_log",
]


# ---------------------------------------------------------------- node handlers


def _node_store_file(state, runner):
    """Copy the file to the storage dir (idempotent). The router
    already saved it; we just confirm and emit a log entry."""
    if state.get("error"):
        return {}
    src = Path(state["file_path"])
    dst = Path(state["file_path"])
    try:
        if src != dst:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return {"stored_path": str(dst)}
    except Exception as exc:  # pragma: no cover
        return {"error": f"store_file failed: {exc}"}


def _node_detect_duplicate(state, runner):
    """Look up a prior invoice with the same file_hash. If
    duplicate, set a flag so the rest of the graph becomes a
    no-op."""
    if state.get("error"):
        return {}
    file_hash = state.get("file_hash")
    if not file_hash:
        return {"is_duplicate": False, "duplicate_of_id": None}
    existing = _is_duplicate(runner.db, file_hash)
    if existing is None:
        return {"is_duplicate": False, "duplicate_of_id": None}
    return {
        "is_duplicate": True,
        "duplicate_of_id": existing.id,
        "status": "duplicate",
    }


def _node_parse_invoice(state, runner):
    """Run the configured parser engine. Falls back to the
    regex pipeline if the engine raises."""
    if state.get("error") or state.get("is_duplicate"):
        return {}
    settings = runner.settings
    mime = state.get("mime_type", "application/pdf")
    path = Path(state["stored_path"])
    engine_name = (getattr(settings, "parser_engine", "existing") or "existing")
    try:
        engine = get_engine(engine_name, settings)
        er: EngineResult = engine.extract_structure(path, mime)
    except Exception as exc:
        logger.warning("engine %s failed (%s); falling back", engine_name, exc)
        try:
            ext = extract_text(path, mime, settings)
            parsed = parse_invoice_text(ext.text)
            er = EngineResult(
                parsed=parsed,
                runtime_ms=0.0,
                used_ocr=ext.used_ocr,
                text_source=ext.source,
                raw_text=ext.text,
                notes=[f"engine_fallback: {exc}"] + ext.notes,
            )
        except Exception as exc2:
            return {"error": f"parse_invoice failed: {exc2}"}
    return {
        "parsed_json": {
            "vendor_name": er.parsed.vendor_name,
            "invoice_number": er.parsed.invoice_number,
            "invoice_date": er.parsed.invoice_date,
            "due_date": er.parsed.due_date,
            "currency": er.parsed.currency,
            "subtotal": er.parsed.subtotal,
            "tax": er.parsed.tax,
            "total_amount": er.parsed.total_amount,
            "line_items": [li.__dict__ for li in er.parsed.line_items],
        },
        "raw_text": er.raw_text or "",
        "text_source": er.text_source,
        "used_ocr": er.used_ocr,
        "confidence_per_field": er.confidence.as_dict() if hasattr(er.confidence, "as_dict") else {},
        "engine_runtime_ms": er.runtime_ms,
        "engine_name": engine_name,
        "warnings": list(er.warnings),
    }


def _node_validate_fields(state, runner):
    """Run the cross-field validator. We rebuild a ``ParsedInvoice``
    from the JSON the parse node produced and feed the validator."""
    if state.get("error") or state.get("is_duplicate"):
        return {}
    settings = runner.settings
    from ..parser import ParsedInvoice, ParsedLineItem
    pj = state.get("parsed_json", {}) or {}
    parsed = ParsedInvoice(
        vendor_name=pj.get("vendor_name"),
        invoice_number=pj.get("invoice_number"),
        invoice_date=pj.get("invoice_date"),
        due_date=pj.get("due_date"),
        currency=pj.get("currency"),
        subtotal=pj.get("subtotal"),
        tax=pj.get("tax"),
        total_amount=pj.get("total_amount"),
        line_items=[ParsedLineItem(**li) for li in pj.get("line_items", [])],
        confidence=(state.get("confidence_per_field", {}) or {}).get("total_amount", 0.0) or 0.0,
        warnings=list(state.get("warnings", []) or []),
    )
    res = validate_parsed(parsed, settings)
    return {
        "confidence_score": res.confidence_score,
        "status": res.status.value,
        "warnings": list(res.warnings),
    }


def _node_route_by_confidence(state, runner):
    """Branching. The validator already produced a status, so this
    node just enforces a safe default if no status is set."""
    if state.get("error") or state.get("is_duplicate"):
        return {}
    if not state.get("status"):
        return {"status": "needs_review"}
    return {}


def _node_create_review_item(state, runner):
    """Persist the Invoice + line items. We do the DB write here
    so the runner can mark this node ok/failed correctly.

    This mirrors the body of :func:`app.services.extraction.extract_and_persist`
    but operates on the workflow's session.
    """
    if state.get("error"):
        return {}
    if state.get("is_duplicate"):
        # Duplicate path: a stub invoice with status DUPLICATE.
        from ...models.invoice import Invoice, InvoiceStatus
        from ...models.invoice_file import InvoiceFile
        from ...models.invoice_line_item import InvoiceLineItem

        db = runner.db
        # Find the original invoice to mirror its fields.
        from ...models.invoice import Invoice as Inv
        orig = (
            db.query(Inv)
            .filter(Inv.id == state.get("duplicate_of_id"))
            .first()
        )
        file_row = InvoiceFile(
            original_filename=state.get("original_filename") or "duplicate",
            stored_path=state.get("stored_path"),
            original_path=state.get("stored_path"),
            current_path=state.get("stored_path"),
            file_hash=state.get("file_hash"),
            mime_type=state.get("mime_type"),
            size=state.get("size", 0),
        )
        db.add(file_row)
        db.flush()
        inv = Invoice(
            vendor_name=(orig.vendor_name if orig else None),
            invoice_number=(orig.invoice_number if orig else None),
            invoice_date=(orig.invoice_date if orig else None),
            due_date=(orig.due_date if orig else None),
            currency=(orig.currency if orig else None),
            subtotal=(orig.subtotal if orig else None),
            tax=(orig.tax if orig else None),
            total_amount=(orig.total_amount if orig else None),
            confidence_score=(orig.confidence_score if orig else 0.0),
            warnings_json=[f"Duplicate of invoice #{state.get('duplicate_of_id')}"] + (list(orig.warnings_json) if orig else []),
            status=InvoiceStatus.DUPLICATE,
            notes=f"Blocked by duplicate of invoice #{state.get('duplicate_of_id')}",
            duplicate_of_invoice_id=state.get("duplicate_of_id"),
            file_id=file_row.id,
        )
        db.add(inv)
        db.commit()
        db.refresh(inv)
        return {"invoice_id": inv.id, "status": "duplicate"}

    if not state.get("parsed_json"):
        return {"error": "no parsed_json; cannot persist"}

    from ...models.invoice import Invoice, InvoiceStatus, Invoice as Inv
    from ...models.invoice_file import InvoiceFile
    from ...models.invoice_line_item import InvoiceLineItem

    db = runner.db
    pj = state.get("parsed_json", {})
    status_str = state.get("status", "needs_review")
    try:
        inv_status = InvoiceStatus(status_str)
    except ValueError:
        inv_status = InvoiceStatus.NEEDS_REVIEW

    file_row = InvoiceFile(
        original_filename=state.get("original_filename") or Path(state.get("stored_path", "")).name,
        stored_path=state.get("stored_path"),
        original_path=state.get("stored_path"),
        current_path=state.get("stored_path"),
        file_hash=state.get("file_hash"),
        mime_type=state.get("mime_type"),
        size=state.get("size", 0),
    )
    db.add(file_row)
    db.flush()
    inv = Invoice(
        vendor_name=pj.get("vendor_name"),
        invoice_number=pj.get("invoice_number"),
        invoice_date=pj.get("invoice_date"),
        due_date=pj.get("due_date"),
        currency=pj.get("currency"),
        subtotal=pj.get("subtotal"),
        tax=pj.get("tax"),
        total_amount=pj.get("total_amount"),
        confidence_score=state.get("confidence_score", 0.0) or 0.0,
        warnings_json=list(state.get("warnings") or []),
        status=inv_status,
        raw_text=(state.get("raw_text") or "")[:20000],
        raw_text_source=state.get("text_source"),
        file_id=file_row.id,
    )
    db.add(inv)
    db.flush()
    for idx, li in enumerate(pj.get("line_items") or []):
        db.add(InvoiceLineItem(
            invoice_id=inv.id,
            description=li.get("description"),
            quantity=li.get("quantity"),
            unit_price=li.get("unit_price"),
            line_total=li.get("line_total"),
            position=idx,
        ))
    db.commit()
    db.refresh(inv)
    return {"invoice_id": inv.id, "status": inv_status.value}


def _node_audit_log(state, runner):
    """Write the workflow-level audit row. Mirrors the
    ``upload`` + ``extraction`` audit entries that the existing
    pipeline writes."""
    if state.get("error"):
        return {}
    from ...services.audit import log_action
    if state.get("invoice_id"):
        log_action(
            runner.db,
            actor=state.get("actor", "user"),
            action="workflow.upload",
            entity_type="invoice",
            entity_id=state["invoice_id"],
            details=(
                f"Processed by workflow=invoice_upload_processing, "
                f"engine={state.get('engine_name', 'existing')}, "
                f"status={state.get('status')}"
            ),
            extra={
                "workflow_run_id": runner.run.id,
                "engine": state.get("engine_name"),
                "confidence": state.get("confidence_score"),
                "is_duplicate": state.get("is_duplicate", False),
            },
        )
    return {}


NODES = {
    "store_file": _node_store_file,
    "detect_duplicate": _node_detect_duplicate,
    "parse_invoice": _node_parse_invoice,
    "validate_fields": _node_validate_fields,
    "route_by_confidence": _node_route_by_confidence,
    "create_review_item": _node_create_review_item,
    "audit_log": _node_audit_log,
}


def build_invoice_upload_graph():
    """Build the LangGraph ``StateGraph`` for the invoice upload
    workflow. Returns ``(compiled_graph, node_handlers)``."""
    g = StateGraph(InvoiceUploadState)
    for name, fn in NODES.items():
        g.add_node(name, fn)
    g.add_edge(START, "store_file")
    for a, b in zip(INVOICE_UPLOAD_NODES, INVOICE_UPLOAD_NODES[1:]):
        g.add_edge(a, b)
    g.add_edge(INVOICE_UPLOAD_NODES[-1], END)
    return g.compile(), NODES
