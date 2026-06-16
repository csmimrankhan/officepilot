"""End-to-end sync tests using a FakeGmailClient.

These tests cover the entire Phase 2 pipeline:
  fake Gmail -> scoring -> download -> store -> Phase 1 extraction ->
  email import + attachment rows + audit log.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.config import get_settings
from app.db import SessionLocal
from app.models.email_account import EmailAccount, EmailAccountStatus
from app.models.email_attachment import EmailAttachment
from app.models.email_import import EmailImport, EmailImportStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.services.email import gmail_client as gc
from app.services.email import sync
from app.services.email.gmail_client import (
    AttachmentRef,
    FakeGmailClient,
    MessageSummary,
)
from tests.test_api import _make_pdf_bytes


def _seed_account(db, email: str = "user@example.com") -> EmailAccount:
    return sync.get_or_create_account(
        db,
        email=email,
        credentials={
            "token": "ya29.fake-access",
            "refresh_token": "1//fake-refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
            "expiry": None,
        },
    )


def _seed_message(
    msg_id: str,
    *,
    subject: str,
    body: str,
    sender: str = "billing@acme.com",
    received: datetime | None = None,
    attachments: list[AttachmentRef] | None = None,
) -> MessageSummary:
    return MessageSummary(
        id=msg_id,
        thread_id="t-" + msg_id,
        sender=sender,
        subject=subject,
        snippet=body[:80],
        received_at=received or datetime.utcnow() - timedelta(days=1),
        body=body,
        attachments=attachments or [],
    )


def _reset_fake() -> FakeGmailClient:
    fake = FakeGmailClient()
    gc._FAKE_HANDLE["client"] = fake
    return fake


def test_run_sync_imports_candidate_with_pdf_attachment():
    db = SessionLocal()
    try:
        settings = get_settings()
        fake = _reset_fake()
        acct = _seed_account(db)
        db.commit()

        att_id = "att-1"
        msg = _seed_message(
            "m1",
            subject="Invoice INV-2026-100",
            body="Please pay the attached invoice. Total: $123.45",
            attachments=[AttachmentRef(
                attachment_id=att_id, filename="INV-2026-100.pdf",
                mime_type="application/pdf", size=4096,
            )],
        )
        fake.add_message(msg, attachments={att_id: _make_pdf_bytes()})

        report = sync.run_sync(db, settings, account_id=acct.id, client=fake, actor="tester")

        assert report.candidates == 1
        assert report.imported == 1
        assert report.duplicates == 0
        assert report.errors == 0
        assert len(report.invoices) == 1

        # EmailImport row updated to IMPORTED
        imp = db.query(EmailImport).filter(EmailImport.account_id == acct.id).first()
        assert imp is not None
        assert imp.status == EmailImportStatus.IMPORTED
        assert imp.score > 0

        # Attachment row linked to the created invoice
        att = db.query(EmailAttachment).filter(EmailAttachment.email_import_id == imp.id).first()
        assert att is not None
        assert att.processed_invoice_id is not None
        assert att.status == "imported"

        # The created invoice has file.source == "email" with FKs set
        inv = db.query(Invoice).filter(Invoice.id == att.processed_invoice_id).first()
        assert inv is not None
        assert inv.file is not None
        assert inv.file.source == "email"
        assert inv.file.email_import_id == imp.id
        assert inv.file.email_attachment_id == att.id
    finally:
        db.close()


def test_run_sync_skips_below_threshold():
    db = SessionLocal()
    try:
        settings = get_settings()
        fake = _reset_fake()
        acct = _seed_account(db)
        from dataclasses import replace
        new_settings = replace(settings, gmail_min_score=0.99)
        db.commit()

        msg = _seed_message(
            "m-low",
            subject="Your invoice",
            body="see attached",
            attachments=[AttachmentRef(
                attachment_id="att-low", filename="inv.pdf",
                mime_type="application/pdf", size=10,
            )],
        )
        fake.add_message(msg, attachments={"att-low": _make_pdf_bytes()})

        report = sync.run_sync(db, new_settings, account_id=acct.id, client=fake)
        assert report.candidates == 1
        assert report.imported == 0
        assert report.skipped == 1
        imp = (
            db.query(EmailImport)
            .filter(EmailImport.account_id == acct.id)
            .filter(EmailImport.provider_message_id == "m-low")
            .first()
        )
        assert imp is not None
        assert imp.status == EmailImportStatus.SKIPPED
    finally:
        db.close()


def test_run_sync_detects_duplicate_attachment():
    db = SessionLocal()
    try:
        settings = get_settings()
        fake = _reset_fake()
        acct = _seed_account(db)
        db.commit()

        pdf = _make_pdf_bytes()
        # First message: should import
        msg1 = _seed_message(
            "m-dup-1",
            subject="Invoice INV-DUP",
            body="attached",
            attachments=[AttachmentRef(
                attachment_id="att-dup", filename="inv-dup.pdf",
                mime_type="application/pdf", size=len(pdf),
            )],
        )
        fake.add_message(msg1, attachments={"att-dup": pdf})
        report1 = sync.run_sync(db, settings, account_id=acct.id, client=fake)
        assert report1.imported == 1
        assert report1.duplicates == 0

        # Second message: same attachment bytes — should be duplicate
        msg2 = _seed_message(
            "m-dup-2",
            subject="Invoice INV-DUP (resend)",
            body="attached again",
            attachments=[AttachmentRef(
                attachment_id="att-dup-2", filename="inv-dup-2.pdf",
                mime_type="application/pdf", size=len(pdf),
            )],
        )
        fake.add_message(msg2, attachments={"att-dup-2": pdf})
        report2 = sync.run_sync(db, settings, account_id=acct.id, client=fake)
        # Both messages were processed: the first is duplicate of the second-run's
        # first-attempt creation... actually the first message has already produced
        # an InvoiceFile with that hash. So the second message's attachment is
        # detected as a duplicate. (The first message is also re-evaluated, so we
        # count both as duplicate by hash.)
        assert report2.candidates == 2
        assert report2.duplicates >= 1
        assert report2.imported == 0
    finally:
        db.close()


def test_run_sync_writes_audit_logs():
    db = SessionLocal()
    try:
        settings = get_settings()
        fake = _reset_fake()
        acct = _seed_account(db)
        db.commit()

        from app.models.audit_log import AuditLog
        msg = _seed_message(
            "m-aud",
            subject="Invoice INV-AUD",
            body="attached",
            attachments=[AttachmentRef(
                attachment_id="att-aud", filename="inv-aud.pdf",
                mime_type="application/pdf", size=10,
            )],
        )
        fake.add_message(msg, attachments={"att-aud": _make_pdf_bytes()})

        sync.run_sync(db, settings, account_id=acct.id, client=fake, actor="alice")

        actions = {
            row.action for row in db.query(AuditLog).order_by(AuditLog.id.asc()).all()
        }
        for needed in (
            "email.sync.start",
            "email.sync.candidate",
            "email.sync.imported",
            "email.sync.finish",
        ):
            assert needed in actions, f"missing audit action: {needed}"
    finally:
        db.close()


def test_disconnect_purges_tokens():
    db = SessionLocal()
    try:
        _ = _seed_account(db)
        db.commit()
        acct = db.query(EmailAccount).filter(EmailAccount.email == "user@example.com").first()
        assert acct.access_token_enc is not None
        ok = sync.disconnect_account(db, acct.id)
        db.commit()
        assert ok
        db.refresh(acct)
        assert acct.status == EmailAccountStatus.DISCONNECTED
        assert acct.access_token_enc is None
        assert acct.refresh_token_enc is None
    finally:
        db.close()


def test_sync_continues_after_one_bad_message():
    db = SessionLocal()
    try:
        settings = get_settings()
        fake = _reset_fake()
        acct = _seed_account(db)
        db.commit()

        # One good message...
        good = _seed_message(
            "m-good",
            subject="Invoice INV-GOOD",
            body="attached",
            attachments=[AttachmentRef(
                attachment_id="att-good", filename="inv-good.pdf",
                mime_type="application/pdf", size=10,
            )],
        )
        fake.add_message(good, attachments={"att-good": _make_pdf_bytes()})

        # ...and one that will fail to download
        bad = _seed_message(
            "m-bad",
            subject="Invoice INV-BAD",
            body="attached",
            attachments=[AttachmentRef(
                attachment_id="att-missing", filename="inv-bad.pdf",
                mime_type="application/pdf", size=10,
            )],
        )
        fake.add_message(bad)  # no attachment bytes added -> download will fail

        report = sync.run_sync(db, settings, account_id=acct.id, client=fake)
        assert report.candidates == 2
        assert report.imported == 1
        assert report.errors == 1
    finally:
        db.close()
