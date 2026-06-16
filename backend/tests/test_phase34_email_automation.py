"""Phase 34 — Gmail Read-Only Email Automation tests."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.email_account import EmailAccount, EmailAccountStatus, EmailProvider
from app.models.user import User
from app.services.auth import create_access_token, hash_password


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_db():
    """Clear all data between tests using the app's own session."""
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        # Delete in dependency order (child tables first)
        from app.models.email_search_run import EmailSearchRun
        from app.models.email_attachment_download import EmailAttachmentDownload
        db.query(EmailAttachmentDownload).delete()
        db.query(EmailSearchRun).delete()
        db.query(EmailAccount).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def db_session():
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    user = User(
        email="test@officepilot.ai",
        password_hash=hash_password("test123"),
        role="owner",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def auth_token(test_user: User) -> str:
    return create_access_token(test_user.id, test_user.email, test_user.role)


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def client(db_session):
    from app.db import get_db

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def connected_gmail_account(db_session):
    """Create a connected Gmail account with encrypted token."""
    from app.services.email.crypto import encrypt_str
    acct = EmailAccount(
        provider=EmailProvider.GMAIL,
        email="testuser@gmail.com",
        access_token_enc=encrypt_str('{"token": "fake-token"}'),
        refresh_token_enc=encrypt_str('{"token": "fake-refresh"}'),
        scopes="https://www.googleapis.com/auth/gmail.readonly",
        status=EmailAccountStatus.CONNECTED,
    )
    db_session.add(acct)
    db_session.flush()
    return acct


# ── Test 1: Gmail connect URL uses gmail.readonly scope ─────────────────


def test_gmail_scope_is_readonly():
    from app.services.email.gmail_client import GMAIL_SCOPES
    assert GMAIL_SCOPES == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert len(GMAIL_SCOPES) == 1
    assert "gmail.modify" not in GMAIL_SCOPES
    assert "gmail.send" not in GMAIL_SCOPES
    assert "mail.google.com" not in GMAIL_SCOPES


# ── Test 2: Broader Gmail scopes are not used ────────────────────────


def test_no_broad_scopes():
    from app.services.email.gmail_client import GMAIL_SCOPES
    for scope in GMAIL_SCOPES:
        assert scope == "https://www.googleapis.com/auth/gmail.readonly"


# ── Test 3: Search works with mock client (no real Gmail) ──────────


def test_email_search_returns_mock_results(client: TestClient, auth_headers: dict):
    resp = client.post("/api/email/search", json={
        "query": "has:attachment newer_than:30d invoice",
        "max_results": 5,
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["result_count"] >= 0
    assert "messages" in data


def test_email_search_returns_messages(client: TestClient, auth_headers: dict):
    resp = client.post("/api/email/search", json={
        "query": "has:attachment invoice",
        "max_results": 3,
    }, headers=auth_headers)
    data = resp.json()
    if data["result_count"] > 0:
        msg = data["messages"][0]
        assert "message_id" in msg
        assert "from" in msg
        assert "subject" in msg
        assert "attachments" in msg


# ── Test 4: Preview returns attachment metadata ────────────────────


def test_email_preview_returns_attachments(client: TestClient, auth_headers: dict):
    resp = client.post("/api/email/preview", json={
        "message_id": "mock-msg-1",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "attachments" in data
    assert "has_attachments" in data


# ── Test 5: Download saves file ─────────────────────────


def test_email_download_saves_file(client: TestClient, auth_headers: dict):
    with tempfile.TemporaryDirectory() as tmp:
        resp = client.post("/api/email/attachments/download", json={
            "message_id": "mock-msg-1",
            "attachment_id": "att-1-1",
            "output_folder": tmp,
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["filename"]
        saved = Path(data["saved_path"])
        assert saved.exists()


# ── Test 6: Batch download ───────────────────────────────────────


def test_email_batch_download(client: TestClient, auth_headers: dict):
    with tempfile.TemporaryDirectory() as tmp:
        resp = client.post("/api/email/batch-download", json={
            "provider": "gmail",
            "message_ids": ["mock-msg-1"],
            "output_folder": tmp,
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["total_downloaded"] >= 0


# ── Test 7: No send/delete/modify endpoints exist ──────────


def test_no_send_endpoint(client: TestClient):
    resp = client.post("/api/email/send", json={})
    assert resp.status_code in (404, 405)


def test_no_delete_endpoint(client: TestClient):
    resp = client.post("/api/email/messages/delete", json={})
    assert resp.status_code in (404, 405)


def test_no_modify_endpoint(client: TestClient):
    resp = client.post("/api/email/messages/modify", json={})
    assert resp.status_code in (404, 405)


# ── Test 8: Email accounts endpoint works ──────────────────────────


def test_email_accounts_endpoint(client: TestClient, auth_headers: dict):
    resp = client.get("/api/email/accounts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "accounts" in data
    assert "connected" in data


# ── Test 9: Search with connected account ───


def test_search_with_connected_account(client: TestClient, auth_headers: dict, connected_gmail_account):
    from app.services.email.gmail_client import install_fake_client, FakeGmailClient, MessageSummary, AttachmentRef
    fake = FakeGmailClient()
    from datetime import datetime
    now = datetime.utcnow()
    msg = MessageSummary(
        id="real-msg-1",
        thread_id="thread-1",
        sender="vendor@example.com",
        subject="Invoice #5000",
        snippet="Invoice attached",
        received_at=now,
        attachments=[AttachmentRef(attachment_id="att-1", filename="inv_5000.pdf", mime_type="application/pdf", size=50000)],
    )
    fake.add_message(msg, {"att-1": b"fake pdf content"})
    install_fake_client(fake)

    resp = client.post("/api/email/search", json={
        "query": "has:attachment invoice",
        "max_results": 10,
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"


# ── Test 10: Token safety — tokens not logged ──────────────────────


def test_tokens_not_in_logs(client: TestClient, auth_headers: dict, caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    resp = client.get("/api/email/accounts", headers=auth_headers)
    assert resp.status_code == 200
    log_text = caplog.text.lower()
    assert "access_token" not in log_text or "encrypted" in log_text
    assert "refresh_token" not in log_text or "encrypted" in log_text


# ── Test 11: Disconnect tool ─────────────────────────────────────


def test_email_connect_gmail_tool_needs_account():
    """email_connect_gmail executor returns mock when no account."""
    from app.services.agent_tool_executor import _execute_email_connect_gmail
    from unittest.mock import MagicMock
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
    user = MagicMock(id=1)

    with patch("app.services.agent_tool_executor.get_settings") as mock_settings:
        s = MagicMock()
        s.gmail_configured = False
        s.gmail_client_id = ""
        mock_settings.return_value = s
        result = _execute_email_connect_gmail({}, db, user)
        assert result["status"] == "success"
        assert result["output"].get("status") == "mock"
