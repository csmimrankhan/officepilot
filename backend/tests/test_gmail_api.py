"""HTTP API tests for Gmail integration endpoints (Phase 2)."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import SessionLocal
from app.services.email import gmail_client as gc
from app.services.email.gmail_client import (
    AttachmentRef,
    FakeGmailClient,
    MessageSummary,
)
from tests.test_api import _make_pdf_bytes


def _install_fake_with_messages(messages):
    fake = FakeGmailClient()
    gc._FAKE_HANDLE["client"] = fake
    for msg, atts in messages:
        fake.add_message(msg, atts or {})
    return fake


def test_status_when_not_connected(client: TestClient, monkeypatch):
    # Ensure OAuth is not configured for this test.
    monkeypatch.setenv("OFFICEPILOT_GMAIL_CLIENT_ID", "")
    monkeypatch.setenv("OFFICEPILOT_GMAIL_CLIENT_SECRET", "")
    from app.config import _settings_singleton
    _settings_singleton.cache_clear()

    r = client.get("/api/integrations/gmail/status")
    assert r.status_code == 200
    body = r.json()
    assert body["connected"] is False
    assert body["account"] is None
    assert body["configured"] is False


def test_connect_returns_url_when_configured(client: TestClient, monkeypatch):
    # Set env vars and clear the settings cache so the route sees a configured app.
    monkeypatch.setenv("OFFICEPILOT_GMAIL_CLIENT_ID", "test-id")
    monkeypatch.setenv("OFFICEPILOT_GMAIL_CLIENT_SECRET", "test-secret")
    from app.config import _settings_singleton
    _settings_singleton.cache_clear()

    r = client.get("/api/integrations/gmail/connect")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["authorization_url"].startswith("https://accounts.google.com/o/oauth2/auth")
    assert "state=" in data["authorization_url"]


def test_connect_rejects_when_unconfigured(client: TestClient):
    # Default settings have empty client_id/secret -> 409
    r = client.get("/api/integrations/gmail/connect")
    assert r.status_code == 409
    assert "not configured" in r.json()["detail"].lower()


def test_sync_finds_and_imports_via_fake(client: TestClient):
    pdf = _make_pdf_bytes()
    msg = MessageSummary(
        id="api-1",
        thread_id="t-api-1",
        sender="billing@acme.com",
        subject="Invoice INV-API-1",
        snippet="see attached",
        received_at=datetime.utcnow() - timedelta(days=1),
        body="Please find your invoice attached. Total: $10.00",
        attachments=[AttachmentRef(
            attachment_id="a-1", filename="inv-api-1.pdf",
            mime_type="application/pdf", size=len(pdf),
        )],
    )
    _install_fake_with_messages([(msg, {"a-1": pdf})])

    # Manually create a connected account (skipping OAuth for the test)
    db = SessionLocal()
    try:
        from app.services.email import sync
        sync.get_or_create_account(
            db,
            email="user@example.com",
            credentials={
                "token": "ya29.fake", "refresh_token": "1//fake",
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
                "expiry": None,
            },
        )
        db.commit()
    finally:
        db.close()

    r = client.post("/api/integrations/gmail/sync-invoices")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["candidates"] == 1
    assert body["imported"] == 1
    assert body["invoice_ids"]

    # Email import list should show the import
    r2 = client.get("/api/email-imports")
    assert r2.status_code == 200
    items = r2.json()
    assert any(i["provider_message_id"] == "api-1" for i in items)


def test_sync_fails_cleanly_when_not_connected(client: TestClient):
    # No account connected
    r = client.post("/api/integrations/gmail/sync-invoices")
    assert r.status_code == 409
    assert "not connected" in r.json()["detail"].lower()


def test_disconnect_clears_account(client: TestClient):
    db = SessionLocal()
    try:
        from app.services.email import sync
        sync.get_or_create_account(
            db,
            email="user@example.com",
            credentials={"token": "x", "refresh_token": "y", "scopes": []},
        )
        db.commit()
    finally:
        db.close()

    r = client.post("/api/integrations/gmail/disconnect")
    assert r.status_code == 200
    body = r.json()
    assert body["disconnected"] is True
    # Now status should be disconnected
    r2 = client.get("/api/integrations/gmail/status")
    assert r2.json()["connected"] is False


def test_email_imports_endpoint_paginates(client: TestClient):
    pdf = _make_pdf_bytes()
    # Use 3 distinct attachments (different bytes) so the duplicate filter
    # doesn't kick in.
    msgs = []
    for i in range(3):
        # Small per-message payload tweak keeps each PDF unique.
        unique_pdf = pdf + f"% msg-{i}".encode()
        msgs.append((
            MessageSummary(
                id=f"api-p-{i}",
                thread_id=f"t-p-{i}",
                sender="billing@acme.com",
                subject=f"Invoice INV-P-{i}",
                snippet="see attached",
                received_at=datetime.utcnow() - timedelta(days=1),
                body="please pay",
                attachments=[AttachmentRef(
                    attachment_id=f"ap-{i}", filename=f"inv-p-{i}.pdf",
                    mime_type="application/pdf", size=len(unique_pdf),
                )],
            ),
            {f"ap-{i}": unique_pdf},
        ))
    _install_fake_with_messages(msgs)

    db = SessionLocal()
    try:
        from app.services.email import sync
        sync.get_or_create_account(
            db,
            email="user@example.com",
            credentials={"token": "x", "refresh_token": "y", "scopes": []},
        )
        db.commit()
    finally:
        db.close()

    r = client.post("/api/integrations/gmail/sync-invoices")
    assert r.status_code == 200
    body = r.json()
    assert body["candidates"] == 3
    assert body["imported"] == 3
    assert body["duplicates"] == 0

    r2 = client.get("/api/email-imports", params={"status": "imported"})
    assert r2.status_code == 200
    assert len(r2.json()) == 3


def test_review_queue_contains_email_source_invoice(client: TestClient):
    pdf = _make_pdf_bytes()
    msg = MessageSummary(
        id="api-rq-1",
        thread_id="t-rq-1",
        sender="billing@acme.com",
        subject="Invoice INV-RQ-1",
        snippet="see attached",
        received_at=datetime.utcnow() - timedelta(days=1),
        body="please pay",
        attachments=[AttachmentRef(
            attachment_id="ar-1", filename="inv-rq-1.pdf",
            mime_type="application/pdf", size=len(pdf),
        )],
    )
    _install_fake_with_messages([(msg, {"ar-1": pdf})])
    db = SessionLocal()
    try:
        from app.services.email import sync
        sync.get_or_create_account(
            db,
            email="user@example.com",
            credentials={"token": "x", "refresh_token": "y", "scopes": []},
        )
        db.commit()
    finally:
        db.close()

    client.post("/api/integrations/gmail/sync-invoices")

    r = client.get("/api/invoices")
    assert r.status_code == 200
    items = r.json()
    email_invoices = [i for i in items if (i.get("file") or {}).get("source") == "email"]
    assert email_invoices, "expected at least one email-sourced invoice in the review queue"
    f = email_invoices[0]["file"]
    assert f["email_import_id"] is not None
    assert f["email_attachment_id"] is not None
