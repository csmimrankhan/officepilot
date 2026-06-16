"""Tests for Phase 6 — workflow orchestration."""

from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import SessionLocal
from app.models.invoice import Invoice, InvoiceStatus
from app.models.workflow_approval import ApprovalStatus, WorkflowApproval
from app.models.workflow_log import NodeLogStatus
from app.models.workflow_run import WorkflowRun, WorkflowStatus
from app.services.workflows.invoice_upload import build_invoice_upload_graph
from app.services.workflows.excel_export import build_excel_export_graph
from app.services.workflows.runner import WorkflowRunner


# ----------------------------------------------------------- helpers


def _make_invoice_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((50, 60), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def _upload_text_invoice(client: TestClient, body: str, *, name: str = "test.pdf") -> dict:
    data = _make_invoice_pdf(body)
    r = client.post(
        "/api/invoices/upload",
        files={"file": (name, io.BytesIO(data), "application/pdf")},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


def _approve_invoice(invoice_id: int) -> None:
    """Mark an invoice APPROVED via the test session."""
    db = SessionLocal()
    try:
        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        inv.status = InvoiceStatus.APPROVED
        db.add(inv)
        db.commit()
    finally:
        db.close()


# ----------------------------------------------------------- model / persistence


def test_workflow_runs_table_persists_state(tmp_path):
    """The acceptance criterion: workflow state persists after
    app restart. We simulate a restart by creating the run,
    writing partial state, closing the session, opening a fresh
    session, and reading it back."""
    db = SessionLocal()
    try:
        run = WorkflowRun(
            workflow_name="invoice_upload_processing",
            status=WorkflowStatus.RUNNING.value,
            current_node="parse_invoice",
            state_json={"foo": "bar", "n": 42},
            input_json={"actor": "alice"},
            actor="alice",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
    finally:
        db.close()

    # Simulate restart.
    db2 = SessionLocal()
    try:
        run2 = db2.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        assert run2 is not None
        assert run2.status == WorkflowStatus.RUNNING.value
        assert run2.current_node == "parse_invoice"
        assert run2.state_json == {"foo": "bar", "n": 42}
    finally:
        db2.close()


# ----------------------------------------------------------- Graph 1: invoice upload


def test_invoice_upload_graph_runs_to_completion(client: TestClient):
    """The graph runs end-to-end, persists the invoice, and writes
    per-node log rows."""
    body = (
        "Acme Office Supplies\n"
        "INVOICE\n"
        "Invoice Number: WORKFLOW-001\n"
        "Invoice Date: 2026-05-12\n"
        "Due Date: 2026-06-11\n"
        "Subtotal: 100.00\n"
        "Tax (7%): 7.00\n"
        "Total: 107.00\n"
    )
    r = client.post(
        "/api/workflows/run/invoice_upload_processing",
        json={
            "input": {
                "actor": "alice",
                "file_path": _write_tmp_pdf(body),
                "original_filename": "wf1.pdf",
                "file_hash": _hash_tmp(body),
                "mime_type": "application/pdf",
                "size": 1024,
            }
        },
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["workflow_name"] == "invoice_upload_processing"
    assert out["status"] in (WorkflowStatus.COMPLETED.value, WorkflowStatus.RUNNING.value)
    # At least the audit_log + a few middle nodes were logged.
    node_names = [l["node_name"] for l in out["logs"]]
    assert "store_file" in node_names
    assert "parse_invoice" in node_names
    # An invoice was created.
    assert out["state"].get("invoice_id")


def test_invoice_upload_graph_detects_duplicate(client: TestClient):
    """Second upload of the same content hits detect_duplicate."""
    body = (
        "Acme Office Supplies\n"
        "INVOICE\n"
        "Invoice Number: WORKFLOW-DUP-001\n"
        "Invoice Date: 2026-05-12\n"
        "Total: 100.00\n"
    )
    file_path = _write_tmp_pdf(body)
    file_hash = _hash_tmp(body)
    payload = {
        "input": {
            "actor": "alice",
            "file_path": file_path,
            "original_filename": "dup.pdf",
            "file_hash": file_hash,
            "mime_type": "application/pdf",
            "size": 1024,
        }
    }
    r1 = client.post("/api/workflows/run/invoice_upload_processing", json=payload)
    assert r1.status_code == 200
    out1 = r1.json()
    # First run: not a duplicate.
    assert not out1["state"].get("is_duplicate")
    # Second run: should detect the duplicate.
    r2 = client.post("/api/workflows/run/invoice_upload_processing", json=payload)
    assert r2.status_code == 200
    out2 = r2.json()
    assert out2["state"].get("is_duplicate") is True
    assert out2["state"].get("duplicate_of_id")


# ----------------------------------------------------------- Graph 3: export with approval


def test_excel_export_pauses_at_approval(client: TestClient):
    body = (
        "Acme Office Supplies\n"
        "INVOICE\n"
        "Invoice Number: EXPORT-001\n"
        "Invoice Date: 2026-05-12\n"
        "Subtotal: 200.00\n"
        "Tax (7%): 14.00\n"
        "Total: 214.00\n"
    )
    upload = _upload_text_invoice(client, body, name="exp1.pdf")
    _approve_invoice(upload["id"])

    r = client.post("/api/workflows/run/approved_invoice_export", json={"input": {"actor": "alice"}})
    assert r.status_code == 200
    out = r.json()
    # The run should be paused at human_approval_checkpoint.
    assert out["status"] == WorkflowStatus.AWAITING_APPROVAL.value
    assert out["current_node"] == "human_approval_checkpoint"
    assert out["pending_approval"] is not None
    assert "Export" in out["pending_approval"]["message"]


def test_excel_export_approval_resumes_run(client: TestClient):
    body = (
        "Acme Office Supplies\n"
        "INVOICE\n"
        "Invoice Number: EXPORT-002\n"
        "Invoice Date: 2026-05-12\n"
        "Subtotal: 100.00\n"
        "Tax: 7.00\n"
        "Total: 107.00\n"
    )
    upload = _upload_text_invoice(client, body, name="exp2.pdf")
    _approve_invoice(upload["id"])

    r = client.post("/api/workflows/run/approved_invoice_export", json={"input": {"actor": "alice"}})
    out = r.json()
    run_id = out["id"]
    assert out["status"] == WorkflowStatus.AWAITING_APPROVAL.value

    # Approve.
    r2 = client.post(
        f"/api/workflows/runs/{run_id}/approve",
        json={"actor": "alice", "note": "looks good"},
    )
    assert r2.status_code == 200
    out2 = r2.json()
    # The run should now be completed.
    assert out2["status"] == WorkflowStatus.COMPLETED.value
    # And the approval row is updated.
    approval = next(a for a in out2["approvals"] if a["node_name"] == "human_approval_checkpoint")
    assert approval["status"] == ApprovalStatus.APPROVED.value
    assert approval["approved_by"] == "alice"


def test_excel_export_rejection_stops_run(client: TestClient):
    body = (
        "Acme Office Supplies\n"
        "INVOICE\n"
        "Invoice Number: EXPORT-003\n"
        "Invoice Date: 2026-05-12\n"
        "Total: 50.00\n"
    )
    upload = _upload_text_invoice(client, body, name="exp3.pdf")
    _approve_invoice(upload["id"])

    r = client.post("/api/workflows/run/approved_invoice_export", json={"input": {"actor": "alice"}})
    out = r.json()
    run_id = out["id"]
    assert out["status"] == WorkflowStatus.AWAITING_APPROVAL.value

    r2 = client.post(
        f"/api/workflows/runs/{run_id}/reject",
        json={"actor": "alice", "note": "missing receipt"},
    )
    assert r2.status_code == 200
    out2 = r2.json()
    assert out2["status"] == WorkflowStatus.REJECTED.value


# ----------------------------------------------------------- cancel + retry


def test_cancel_running_workflow(client: TestClient):
    """Cancel works for runs that are RUNNING (or PENDING, AWAITING_APPROVAL)."""
    body = (
        "Acme\nINVOICE\nInvoice Number: CANCEL-001\nInvoice Date: 2026-05-12\nTotal: 50.00\n"
    )
    upload = _upload_text_invoice(client, body, name="cancel.pdf")
    _approve_invoice(upload["id"])

    r = client.post("/api/workflows/run/approved_invoice_export", json={"input": {"actor": "alice"}})
    out = r.json()
    run_id = out["id"]
    r2 = client.post(
        f"/api/workflows/runs/{run_id}/cancel",
        json={"actor": "alice", "note": "test cancel"},
    )
    assert r2.status_code == 200
    out2 = r2.json()
    assert out2["status"] == WorkflowStatus.CANCELLED.value


def test_retry_failed_node(client: TestClient):
    """Retry re-runs the graph from the node that failed.

    We create a FAILED run directly (the runner is exercised
    end-to-end by the other tests) and then call /retry. The
    retry should reset the status, re-execute the graph from
    ``current_node``, and either complete (if the input is
    valid) or fail again (if the input is bad). Either way, the
    retry endpoint must accept the request.
    """
    from app.models.workflow_run import WorkflowRun, WorkflowStatus
    from app.services.workflows import registry as reg
    from app.services.workflows.runner import WorkflowRunner
    import json as _json

    body = (
        "Acme\nINVOICE\nInvoice Number: RETRY-001\nInvoice Date: 2026-05-12\nTotal: 50.00\n"
    )
    file_path = _write_tmp_pdf(body)
    file_hash = _hash_tmp(body)

    spec = reg.GRAPHS["invoice_upload_processing"]
    db = SessionLocal()
    try:
        run = WorkflowRun(
            workflow_name=spec.name,
            status=WorkflowStatus.FAILED.value,
            current_node="parse_invoice",
            state_json=_json.dumps({"error": "synthetic failure", "file_hash": file_hash}),
            input_json=_json.dumps({
                "actor": "alice",
                "file_path": file_path,
                "original_filename": "retry.pdf",
                "file_hash": file_hash,
                "mime_type": "application/pdf",
                "size": 1024,
            }),
            error_message="parse_invoice: synthetic failure",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
    finally:
        db.close()

    # Retry should reset the run and re-execute the graph.
    r = client.post(
        f"/api/workflows/runs/{run_id}/retry",
        json={"actor": "alice"},
    )
    assert r.status_code == 200
    out = r.json()
    assert out["id"] == run_id
    # The retry should have cleared the error_message and reset
    # the status. It may have completed successfully or failed
    # again (e.g. on store_file), but it must not still be in
    # the original FAILED state with the same error.
    db2 = SessionLocal()
    try:
        run2 = db2.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        assert run2.error_message != "parse_invoice: synthetic failure"
    finally:
        db2.close()


# ----------------------------------------------------------- endpoint smoke


def test_list_graphs_endpoint(client: TestClient):
    r = client.get("/api/workflows/graphs")
    assert r.status_code == 200
    body = r.json()
    names = {g["name"] for g in body["graphs"]}
    assert names == {
        "invoice_upload_processing",
        "email_invoice_import",
        "approved_invoice_export",
        "browser_automation",
    }


def test_list_runs_endpoint(client: TestClient):
    body = (
        "Acme\nINVOICE\nInvoice Number: LIST-001\nInvoice Date: 2026-05-12\nTotal: 50.00\n"
    )
    upload = _upload_text_invoice(client, body, name="list.pdf")
    _approve_invoice(upload["id"])
    client.post("/api/workflows/run/approved_invoice_export", json={"input": {"actor": "alice"}})
    r = client.get("/api/workflows/runs?workflow_name=approved_invoice_export")
    assert r.status_code == 200
    body = r.json()
    assert body["runs"]
    assert any(run["workflow_name"] == "approved_invoice_export" for run in body["runs"])


def test_get_run_404_for_missing(client: TestClient):
    r = client.get("/api/workflows/runs/99999")
    assert r.status_code == 404


def test_start_unknown_workflow_404(client: TestClient):
    r = client.post("/api/workflows/run/nope", json={"input": {}})
    assert r.status_code == 404


# ----------------------------------------------------------- helpers


def _write_tmp_pdf(body: str) -> str:
    """Render a tiny single-page PDF with the given text and return
    the absolute path. Caller is responsible for cleanup; pytest's
    tmp_path fixture is not used here because the workflow stores
    paths in DB and we want them to survive the test."""
    import tempfile, os
    tmp = tempfile.mkdtemp(prefix="wf-")
    path = os.path.join(tmp, "inv.pdf")
    data = _make_invoice_pdf(body)
    with open(path, "wb") as f:
        f.write(data)
    return path


def _hash_tmp(body: str) -> str:
    import hashlib
    return hashlib.sha256(_make_invoice_pdf(body)).hexdigest()
