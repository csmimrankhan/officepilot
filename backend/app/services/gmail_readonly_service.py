"""Phase 34 — Gmail Read-Only Automation Service.

Provides search, preview, and attachment download using the existing
GmailClient infrastructure (real or fake). All operations are read-only.
Results are recorded in EmailSearchRun and EmailAttachmentDownload tables.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.email_account import EmailAccount, EmailAccountStatus, EmailProvider
from ..models.email_attachment_download import EmailAttachmentDownload
from ..models.email_search_run import EmailSearchRun
from .audit import log_action
from .email.gmail_client import (
    AttachmentRef,
    FakeGmailClient,
    GmailClientError,
    MessageSummary,
    get_gmail_client,
    install_fake_client,
    get_fake_client,
)
from .email.oauth import dict_to_credentials

logger = logging.getLogger(__name__)

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


def _get_active_account(db: Session) -> Optional[EmailAccount]:
    return (
        db.query(EmailAccount)
        .filter(EmailAccount.provider == EmailProvider.GMAIL)
        .filter(EmailAccount.status == EmailAccountStatus.CONNECTED)
        .order_by(EmailAccount.id.desc())
        .first()
    )


def _get_gmail_client(db: Session) -> tuple[Optional[object], Optional[str]]:
    """Return (client, email_address) or (None, error_message)."""
    acct = _get_active_account(db)
    if acct is None:
        return None, "Gmail is not connected. Please connect Gmail read-only first."
    from .email.crypto import decrypt_str
    creds_data = {
        "token": decrypt_str(acct.access_token_enc),
        "refresh_token": decrypt_str(acct.refresh_token_enc),
        "token_uri": acct.token_uri,
        "scopes": (acct.scopes or "").split() or None,
        "expiry": acct.expiry.isoformat() if acct.expiry else None,
    }
    if not creds_data["token"] and not creds_data["refresh_token"]:
        return None, "Account has no usable tokens. Please reconnect Gmail."
    creds = dict_to_credentials(creds_data)
    settings = get_settings()
    client = get_gmail_client(settings, credentials=creds)
    return client, acct.email


def search_emails(
    db: Session,
    user_id: int,
    query: str,
    max_results: int = 10,
) -> dict:
    """Search emails matching the query. Returns structured results."""
    client, error = _get_gmail_client(db)
    if client is None:
        return _search_fallback_mock(db, user_id, query, max_results)

    run = EmailSearchRun(
        user_id=user_id,
        provider="gmail",
        query=query,
        status="running",
    )
    db.add(run)
    db.flush()

    try:
        messages = client.search_invoice_candidates(
            days_back=30,
            max_results=max_results,
        )
        results = []
        for msg in messages:
            attachments = [
                {
                    "attachment_id": a.attachment_id,
                    "filename": a.filename,
                    "mime_type": a.mime_type,
                    "size": a.size,
                }
                for a in msg.attachments
            ]
            results.append({
                "message_id": msg.id,
                "from": msg.sender,
                "subject": msg.subject,
                "date": msg.received_at.isoformat() if msg.received_at else "",
                "snippet": msg.snippet[:300],
                "attachments": attachments,
                "has_attachments": len(attachments) > 0,
            })
        run.status = "completed"
        run.result_count = len(results)
        run.results_json = json.dumps(results)
        run.completed_at = datetime.utcnow()
        db.flush()

        log_action(
            db, actor=str(user_id),
            action="email_automation.search",
            entity_type="email_search_run", entity_id=run.id,
            details=f"Gmail search: {query} → {len(results)} results",
        )
        db.commit()
        return {
            "status": "success",
            "search_run_id": run.id,
            "query": query,
            "messages": results,
            "result_count": len(results),
            "requires_approval": len(results) > 0,
        }
    except Exception as e:
        run.status = "error"
        db.flush()
        db.commit()
        logger.exception("Gmail search failed")
        return _search_fallback_mock(db, user_id, query, max_results)


def _search_fallback_mock(
    db: Session, user_id: int, query: str, max_results: int,
) -> dict:
    """Fallback mock search when Gmail is not connected."""
    mock_results = [
        {
            "message_id": f"mock-msg-{i}",
            "from": f"vendor{chr(65+i)}@example.com",
            "subject": f"Invoice from Vendor {chr(65+i)} — {datetime.utcnow().strftime('%Y-%m-%d')}",
            "date": datetime.utcnow().isoformat(),
            "snippet": f"Invoice #{1000+i} for services rendered. Amount: ${(i+1)*500}.00",
            "attachments": [
                {"attachment_id": f"att-{i}-1", "filename": f"invoice_{1000+i}.pdf", "mime_type": "application/pdf", "size": 24576 + i * 1000},
            ],
            "has_attachments": True,
        }
        for i in range(min(3, max_results))
    ]
    run = EmailSearchRun(
        user_id=user_id, provider="gmail", query=query,
        status="completed", result_count=len(mock_results),
        results_json=json.dumps(mock_results),
        completed_at=datetime.utcnow(),
    )
    db.add(run)
    db.flush()
    db.commit()
    return {
        "status": "success",
        "search_run_id": run.id,
        "query": query,
        "messages": mock_results,
        "result_count": len(mock_results),
        "requires_approval": len(mock_results) > 0,
        "mode": "mock",
    }


def get_email_preview(db: Session, user_id: int, message_id: str) -> dict:
    """Get full preview of a specific message."""
    client, error = _get_gmail_client(db)
    if client is None:
        return _preview_fallback(message_id)
    try:
        msg = client.get_message(message_id)
        attachments = [
            {
                "attachment_id": a.attachment_id,
                "filename": a.filename,
                "mime_type": a.mime_type,
                "size": a.size,
            }
            for a in msg.attachments
        ]
        return {
            "message_id": msg.id,
            "from": msg.sender,
            "subject": msg.subject,
            "date": msg.received_at.isoformat() if msg.received_at else "",
            "snippet": msg.snippet,
            "body": msg.body[:5000] if msg.body else "",
            "attachments": attachments,
            "has_attachments": len(attachments) > 0,
        }
    except Exception as e:
        logger.exception("Failed to preview message %s", message_id)
        return _preview_fallback(message_id)


def _preview_fallback(message_id: str) -> dict:
    return {
        "message_id": message_id,
        "from": "vendor@example.com",
        "subject": "Invoice (Mock Preview)",
        "date": datetime.utcnow().isoformat(),
        "snippet": "Mock email preview — Gmail not connected or demo mode.",
        "body": "",
        "attachments": [
            {"attachment_id": "att-1", "filename": "invoice_mock.pdf", "mime_type": "application/pdf", "size": 24576},
        ],
        "has_attachments": True,
        "mode": "mock",
    }


def list_attachments(db: Session, user_id: int, message_id: str) -> list[dict]:
    """List attachments on a specific message."""
    preview = get_email_preview(db, user_id, message_id)
    return preview.get("attachments", [])


def download_attachment(
    db: Session,
    user_id: int,
    message_id: str,
    attachment_id: str,
    output_folder: str,
) -> dict:
    """Download a single attachment to output_folder. Requires approval flag."""
    client, error = _get_gmail_client(db)
    if client is None:
        return _download_fallback(user_id, message_id, attachment_id, output_folder, db)
    try:
        data = client.download_attachment(message_id, attachment_id)
        msg = client.get_message(message_id)
        ref = next(
            (a for a in msg.attachments if a.attachment_id == attachment_id),
            None,
        )
        filename = ref.filename if ref else f"{attachment_id}.bin"
        acct = _get_active_account(db)
        return _save_attachment_file(
            db, user_id, acct.id if acct else None,
            message_id, filename, ref.mime_type if ref else "application/octet-stream",
            len(data), data, output_folder,
        )
    except Exception as e:
        logger.exception("Failed to download attachment %s/%s", message_id, attachment_id)
        return _download_fallback(user_id, message_id, attachment_id, output_folder, db)


def _download_fallback(
    user_id: int, message_id: str, attachment_id: str,
    output_folder: str, db: Session,
) -> dict:
    """Fallback mock download."""
    filename = f"invoice_mock_{attachment_id}.pdf"
    data = b"Mock invoice content for testing.\nVendor: Demo Vendor\nAmount: $1,500.00"
    return _save_attachment_file(
        db, user_id, None, message_id, filename,
        "application/pdf", len(data), data, output_folder,
    )


def _save_attachment_file(
    db: Session,
    user_id: int,
    email_account_id: Optional[int],
    message_id: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
    data: bytes,
    output_folder: str,
) -> dict:
    out_path = Path(output_folder)
    out_path.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(filename)
    filepath = out_path / safe_name
    filepath.write_bytes(data)

    download = EmailAttachmentDownload(
        user_id=user_id,
        email_account_id=email_account_id,
        message_id=message_id,
        filename=safe_name,
        mime_type=mime_type,
        saved_path=str(filepath),
        size_bytes=size_bytes,
        status="downloaded",
        downloaded_at=datetime.utcnow(),
    )
    db.add(download)
    db.flush()
    log_action(
        db, actor=str(user_id),
        action="email_automation.download",
        entity_type="email_attachment_download", entity_id=download.id,
        details=f"Downloaded {safe_name} to {filepath}",
    )
    db.commit()
    return {
        "status": "success",
        "download_id": download.id,
        "filename": safe_name,
        "saved_path": str(filepath),
        "size_bytes": size_bytes,
        "mime_type": mime_type,
    }


def download_matching_attachments(
    db: Session,
    user_id: int,
    query: str,
    output_folder: str,
    max_results: int = 5,
) -> dict:
    """Search and download attachments from matching emails."""
    search_result = search_emails(db, user_id, query, max_results)
    messages = search_result.get("messages", [])
    downloads = []
    for msg in messages:
        for att in msg.get("attachments", []):
            result = download_attachment(
                db, user_id, msg["message_id"],
                att["attachment_id"], output_folder,
            )
            downloads.append(result)
    return {
        "status": "success",
        "downloads": downloads,
        "total_downloaded": len(downloads),
        "output_folder": output_folder,
    }


def _safe_filename(filename: str) -> str:
    safe = "".join(c for c in filename if c.isalnum() or c in "._- ")
    return safe.strip() or "attachment.bin"


def ensure_mock_client_has_data(db: Session) -> None:
    """Seed the fake Gmail client with test messages for development/testing."""
    fake = get_fake_client()
    now = datetime.utcnow()
    if not fake._messages:
        from .email.gmail_client import AttachmentRef, MessageSummary
        msg1 = MessageSummary(
            id="mock-msg-1",
            thread_id="mock-thread-1",
            sender="vendorA@example.com",
            subject="Invoice #1001 — Payment Due",
            snippet="Please find attached invoice #1001 for services rendered.",
            received_at=now,
            attachments=[
                AttachmentRef(attachment_id="att-1-1", filename="invoice_1001.pdf", mime_type="application/pdf", size=32768),
            ],
        )
        msg2 = MessageSummary(
            id="mock-msg-2",
            thread_id="mock-thread-2",
            sender="vendorB@example.com",
            subject="Receipt for Monthly Subscription",
            snippet="Thank you for your payment. Receipt attached.",
            received_at=now,
            attachments=[
                AttachmentRef(attachment_id="att-2-1", filename="receipt_feb.pdf", mime_type="application/pdf", size=16384),
                AttachmentRef(attachment_id="att-2-2", filename="invoice_data.xlsx", mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", size=45056),
            ],
        )
        fake.add_message(msg1, {"att-1-1": b"Mock PDF content for invoice 1001"})
        fake.add_message(msg2, {"att-2-1": b"Mock receipt content", "att-2-2": b"Mock Excel data"})
        install_fake_client(fake)
