"""Phase 18 — Demo mode service. Seeds/fakes all data in safe mode."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings

logger = logging.getLogger("officepilot.demo")

FAKE_VENDORS = [
    "Acme Corp",
    "Globex Industries",
    "Initech Solutions",
    "Umbrella Labs",
    "Stark Enterprises",
    "Wayne Technologies",
    "Cyberdyne Systems",
    "Wonka Foods",
]

FAKE_INVOICE_TEMPLATES: list[dict[str, Any]] = [
    {"vendor": "Acme Corp", "amount": 1234.56, "invoice_number": "INV-2026-001", "description": "Office supplies Q1"},
    {"vendor": "Globex Industries", "amount": 5678.90, "invoice_number": "INV-2026-002", "description": "Consulting services Feb"},
    {"vendor": "Initech Solutions", "amount": 999.99, "invoice_number": "INV-2026-003", "description": "Software license renewal"},
    {"vendor": "Umbrella Labs", "amount": 2500.00, "invoice_number": "INV-2026-004", "description": "Lab equipment maintenance"},
    {"vendor": "Stark Enterprises", "amount": 15000.00, "invoice_number": "INV-2026-005", "description": "R&D project Phase 2"},
    {"vendor": "Wayne Technologies", "amount": 3200.00, "invoice_number": "INV-2026-006", "description": "Network infrastructure upgrade"},
    {"vendor": "Cyberdyne Systems", "amount": 8750.00, "invoice_number": "INV-2026-007", "description": "Security audit Q1"},
    {"vendor": "Wonka Foods", "amount": 450.00, "invoice_number": "INV-2026-008", "description": "Catering - Annual meeting"},
]

DEFAULT_CHECKLIST = [
    {"step": "create_owner", "label": "Create owner account", "optional": False},
    {"step": "confirm_agent", "label": "Confirm local agent is online", "optional": False},
    {"step": "load_demo_data", "label": "Load sample data", "optional": False},
    {"step": "upload_invoice", "label": "Upload your first invoice", "optional": False},
    {"step": "review_invoice", "label": "Review an extracted invoice", "optional": False},
    {"step": "approve_invoice", "label": "Approve an invoice", "optional": False},
    {"step": "export_excel", "label": "Export to Excel", "optional": False},
    {"step": "view_audit_log", "label": "View the audit log", "optional": False},
    {"step": "run_backup", "label": "Run a backup", "optional": False},
    {"step": "check_readiness", "label": "Check readiness dashboard", "optional": False},
    {"step": "connect_gmail", "label": "Connect Gmail (optional)", "optional": True},
    {"step": "connect_accounting", "label": "Connect QuickBooks/Xero sandbox (optional)", "optional": True},
]


def is_demo_mode() -> bool:
    return get_settings().demo_mode


def seed_demo_data(db: Session) -> dict[str, int]:
    from ..models.invoice import Invoice, InvoiceStatus
    from ..models.audit_log import AuditLog
    from ..models.accounting_sync_preview import AccountingSyncPreview
    from ..models.browser_action_run import BrowserActionRun
    from ..models.workflow_recording_session import WorkflowRecordingSession

    count_invoices = 0
    for tpl in FAKE_INVOICE_TEMPLATES:
        existing = db.query(Invoice).filter(Invoice.invoice_number == tpl["invoice_number"]).first()
        if existing:
            continue
        inv = Invoice(
            vendor_name=tpl["vendor"],
            total_amount=tpl["amount"],
            invoice_number=tpl["invoice_number"],
            status=InvoiceStatus.READY_FOR_APPROVAL if count_invoices < 4 else InvoiceStatus.APPROVED,
            email_source="demo",
        )
        db.add(inv)
        count_invoices += 1
    db.flush()

    # Fake audit logs
    existing_logs = db.query(AuditLog).filter(AuditLog.actor == "demo").count()
    if existing_logs == 0:
        now = datetime.utcnow()
        for i in range(5):
            al = AuditLog(
                action=["demo.seed", "demo.invoice_upload", "demo.invoice_approve", "demo.export", "demo.backup"][i],
                details=f"Demo action #{i + 1}",
                actor="demo",
                entity_type="demo",
                timestamp=now - timedelta(minutes=5 * i),
            )
            db.add(al)

    # Get a demo invoice ID for related records
    demo_invoice = db.query(Invoice).filter(Invoice.email_source == "demo").first()
    demo_invoice_id = demo_invoice.id if demo_invoice else None

    # Fake accounting sync preview
    existing_acct = db.query(AccountingSyncPreview).first()
    if not existing_acct and demo_invoice_id:
        asp = AccountingSyncPreview(
            provider="quickbooks_sandbox",
            invoice_id=demo_invoice_id,
            preview_json={
                "invoice_number": "DEMO-INV-001",
                "vendor": "Acme Corp",
                "amount": 1234.56,
                "account": "Accounts Receivable",
            },
            status="pending",
        )
        db.add(asp)

    # Fake browser action run
    existing_browser = db.query(BrowserActionRun).first()
    if not existing_browser:
        bar = BrowserActionRun(
            target_url="http://localhost:5173/demo-test-form",
            action_type="fill_form",
            preview_json={"fields": [{"name": "vendor", "value": "Acme Corp"}]},
            risk_level="low",
            approval_status="approved",
            status="completed",
            result_json={"summary": "Demo form filled successfully"},
        )
        db.add(bar)

    # Fake workflow recording
    existing_rec = db.query(WorkflowRecordingSession).first()
    if not existing_rec:
        wrs = WorkflowRecordingSession(
            raw_events_json=json.dumps({
                "name": "Demo Invoice Processing",
                "steps": [
                    {"type": "open", "target": "invoices"},
                    {"type": "click", "target": "upload_button"},
                    {"type": "fill", "field": "vendor", "value": "Acme Corp"},
                ]
            }),
            event_count=3,
            status="stopped",
        )
        db.add(wrs)

    db.commit()
    return {"invoices": count_invoices, "audit_logs": 5, "accounting_preview": 1, "browser_run": 1, "workflow_recording": 1}


def reset_demo_data(db: Session) -> dict[str, int]:
    from ..models.invoice import Invoice
    from ..models.audit_log import AuditLog
    from ..models.accounting_sync_preview import AccountingSyncPreview
    from ..models.browser_action_run import BrowserActionRun
    from ..models.workflow_recording_session import WorkflowRecordingSession

    counts = {}
    for model, tbl in [
        (Invoice, "invoices"),
        (AuditLog, "audit_logs"),
        (AccountingSyncPreview, "accounting_previews"),
        (BrowserActionRun, "browser_runs"),
        (WorkflowRecordingSession, "workflow_recordings"),
    ]:
        rows = db.query(model).filter(model.__tablename__ != "__nonexistent__").all()
        demo_rows = [r for r in rows if getattr(r, "email_source", None) == "demo" or getattr(r, "actor", None) == "demo"]
        for r in demo_rows:
            db.delete(r)
        counts[tbl] = len(demo_rows)
    db.commit()
    return counts


def get_demo_status(db: Session) -> dict[str, Any]:
    from ..models.invoice import Invoice

    demo_invoices = db.query(Invoice).filter(Invoice.email_source == "demo").count()
    return {
        "demo_mode_enabled": is_demo_mode(),
        "demo_data_seeded": demo_invoices > 0,
        "demo_invoice_count": demo_invoices,
    }


def get_sample_files() -> list[dict[str, str]]:
    settings = get_settings()
    samples_dir = settings.project_root / "samples"
    if not samples_dir.exists():
        return []
    files = []
    for f in sorted(samples_dir.rglob("*")):
        if f.is_file() and f.name != "README.md":
            rel = f.relative_to(samples_dir)
            files.append({
                "name": f.name,
                "path": str(rel),
                "size": f.stat().st_size,
            })
    return files
