"""Gmail sync orchestrator (Phase 2).

Pipeline (per user-triggered sync):

1. Build a GmailClient from stored credentials (or use the injected fake).
2. Search for invoice candidates (``has:attachment newer_than:Nd``).
3. Score each message (subject, body, attachments, sender).
4. For each candidate above the score threshold:
   a. Download each eligible attachment.
   b. Reject duplicates by file hash (already-seen attachments are logged and skipped).
   c. Hand the bytes to the Phase 1 extraction pipeline, which produces an
      Invoice + InvoiceFile + line items + audit log entries.
   d. Link InvoiceFile back to EmailImport + EmailAttachment.
5. Update EmailImport / EmailAttachment rows and write a sync-level audit log.

The orchestrator never mutates the mailbox: no message is marked as read,
archived, deleted, labelled, or sent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from ...config import Settings
from ...models.email_account import EmailAccount, EmailAccountStatus
from ...models.email_attachment import EmailAttachment
from ...models.email_import import EmailImport, EmailImportStatus
from ...models.invoice import Invoice
from ...models.invoice_file import InvoiceFile
from ...services import extraction, storage
from ...services.storage import UnsupportedFileType
from . import scoring
from .gmail_client import (
    FakeGmailClient,
    GmailClient,
    GmailClientError,
    MessageSummary,
    get_gmail_client,
)
from .oauth import dict_to_credentials

logger = logging.getLogger(__name__)


@dataclass
class SyncReport:
    account_id: int
    candidates: int = 0
    imported: int = 0
    duplicates: int = 0
    skipped: int = 0
    errors: int = 0
    invoices: list[int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.invoices is None:
            self.invoices = []

    def as_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "candidates": self.candidates,
            "imported": self.imported,
            "duplicates": self.duplicates,
            "skipped": self.skipped,
            "errors": self.errors,
            "invoice_ids": list(self.invoices),
        }


# --------------------------------------------------------------------- public


def get_or_create_account(
    db: Session,
    *,
    email: str,
    credentials: dict,
    provider: str = "gmail",
) -> EmailAccount:
    """Upsert an EmailAccount row. Replaces stored credentials."""
    from ...models.email_account import EmailProvider
    from .crypto import encrypt_str

    acct = (
        db.query(EmailAccount)
        .filter(EmailAccount.provider == EmailProvider(provider), EmailAccount.email == email)
        .first()
    )
    enc_access = encrypt_str(credentials.get("token") or "")
    enc_refresh = encrypt_str(credentials.get("refresh_token") or "")
    scopes = " ".join(credentials.get("scopes") or [])
    expiry = _parse_iso(credentials.get("expiry"))

    if acct is None:
        acct = EmailAccount(
            provider=EmailProvider(provider),
            email=email,
            access_token_enc=enc_access,
            refresh_token_enc=enc_refresh,
            token_uri=credentials.get("token_uri"),
            scopes=scopes,
            expiry=expiry,
            status=EmailAccountStatus.CONNECTED,
        )
        db.add(acct)
    else:
        acct.access_token_enc = enc_access
        acct.refresh_token_enc = enc_refresh
        acct.token_uri = credentials.get("token_uri")
        acct.scopes = scopes
        acct.expiry = expiry
        acct.status = EmailAccountStatus.CONNECTED
        acct.last_error = None
    db.flush()
    return acct


def disconnect_account(db: Session, account_id: int) -> bool:
    """Mark the account as disconnected. Tokens are purged from disk.

    A future re-connect starts a brand-new OAuth flow.
    """
    acct = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
    if acct is None:
        return False
    acct.status = EmailAccountStatus.DISCONNECTED
    acct.access_token_enc = None
    acct.refresh_token_enc = None
    acct.expiry = None
    db.flush()
    return True


def list_known_vendors(db: Session) -> list[str]:
    """Vendor names that have ever produced an approved or pending invoice."""
    rows = (
        db.query(Invoice.vendor_name)
        .filter(Invoice.vendor_name.isnot(None))
        .filter(Invoice.vendor_name != "")
        .distinct()
        .all()
    )
    return [r[0] for r in rows if r and r[0]]


def run_sync(
    db: Session,
    settings: Settings,
    *,
    account_id: int,
    actor: str = "user",
    client: Optional[GmailClient] = None,
) -> SyncReport:
    """Run one sync pass for the given account. Idempotent per attachment hash."""
    from ...services.audit import log_action

    acct = db.query(EmailAccount).filter(EmailAccount.id == account_id).first()
    if acct is None:
        raise GmailClientError(f"Email account {account_id} not found")
    if acct.status != EmailAccountStatus.CONNECTED:
        raise GmailClientError(
            f"Email account {account_id} is {acct.status.value}; reconnect first."
        )

    if client is None:
        creds_data = {
            "token": _decrypt(acct.access_token_enc),
            "refresh_token": _decrypt(acct.refresh_token_enc),
            "token_uri": acct.token_uri,
            "scopes": (acct.scopes or "").split() or None,
            "expiry": acct.expiry.isoformat() if acct.expiry else None,
        }
        if not creds_data["token"] and not creds_data["refresh_token"]:
            raise GmailClientError(
                "Account has no usable tokens. Please reconnect."
            )
        creds = dict_to_credentials(creds_data)
        client = get_gmail_client(settings, credentials=creds)

    messages = client.search_invoice_candidates(
        days_back=settings.gmail_search_days, max_results=settings.gmail_max_results
    )

    log_action(
        db,
        actor=actor,
        action="email.sync.start",
        entity_type="email_account",
        entity_id=acct.id,
        details=f"Scanning {len(messages)} message(s) from last {settings.gmail_search_days} day(s).",
        extra={
            "provider": acct.provider.value,
            "max_results": settings.gmail_max_results,
            "min_score": settings.gmail_min_score,
        },
    )
    db.flush()

    vendors = list_known_vendors(db)
    report = SyncReport(account_id=acct.id, candidates=len(messages))

    for msg in messages:
        try:
            _ingest_message(
                db, settings, account=acct, message=msg, client=client,
                known_vendors=vendors, report=report, actor=actor,
            )
        except Exception as exc:  # never let one bad message kill the sync
            logger.exception("Failed to ingest message %s", msg.id)
            report.errors += 1
            _record_error(db, account=acct, msg=msg, error=str(exc), actor=actor)

    log_action(
        db,
        actor=actor,
        action="email.sync.finish",
        entity_type="email_account",
        entity_id=acct.id,
        details=(
            f"Sync complete: {report.imported} imported, {report.duplicates} duplicates, "
            f"{report.skipped} skipped, {report.errors} errors."
        ),
        extra=report.as_dict(),
    )
    db.commit()
    return report


# --------------------------------------------------------------------- internals


def _decrypt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    from .crypto import decrypt_str
    return decrypt_str(value)


def _parse_iso(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _record_error(
    db: Session,
    *,
    account: EmailAccount,
    msg: MessageSummary,
    error: str,
    actor: str,
) -> None:
    from ...services.audit import log_action

    imp = (
        db.query(EmailImport)
        .filter(EmailImport.account_id == account.id)
        .filter(EmailImport.provider_message_id == msg.id)
        .first()
    )
    if imp is None:
        imp = EmailImport(
            account_id=account.id,
            provider_message_id=msg.id,
            thread_id=msg.thread_id,
            sender=msg.sender,
            subject=msg.subject,
            snippet=msg.snippet,
            received_at=msg.received_at.replace(tzinfo=None) if msg.received_at else None,
            status=EmailImportStatus.ERROR,
            error=error[:2000],
        )
        db.add(imp)
        db.flush()
    else:
        imp.status = EmailImportStatus.ERROR
        imp.error = error[:2000]

    log_action(
        db,
        actor=actor,
        action="email.sync.error",
        entity_type="email_import",
        entity_id=imp.id,
        details=f"Failed to process message {msg.id}",
        extra={"gmail_message_id": msg.id, "error": error[:500]},
    )
    db.flush()


def _ingest_message(
    db: Session,
    settings: Settings,
    *,
    account: EmailAccount,
    message: MessageSummary,
    client: GmailClient,
    known_vendors: list[str],
    report: SyncReport,
    actor: str,
) -> None:
    from ...services.audit import log_action

    # Get full message (real client already returns full; fake may need get_message).
    try:
        full = message if message.body or message.attachments else client.get_message(message.id)
    except GmailClientError:
        full = message

    hints = [
        scoring.AttachmentHint(filename=a.filename, mime_type=a.mime_type, size=a.size)
        for a in full.attachments
    ]
    scored = scoring.score_message(
        subject=full.subject,
        body=full.body or full.snippet,
        sender=full.sender,
        attachments=hints,
        known_vendors=known_vendors,
    )
    breakdown = scored.to_breakdown()

    imp = (
        db.query(EmailImport)
        .filter(EmailImport.account_id == account.id)
        .filter(EmailImport.provider_message_id == full.id)
        .first()
    )
    if imp is None:
        imp = EmailImport(
            account_id=account.id,
            provider_message_id=full.id,
            thread_id=full.thread_id,
            sender=full.sender,
            subject=full.subject,
            snippet=full.snippet,
            received_at=full.received_at.replace(tzinfo=None) if full.received_at else None,
            score=scored.score,
            score_breakdown=breakdown,
            status=EmailImportStatus.CANDIDATE,
        )
        db.add(imp)
        db.flush()
    else:
        imp.score = scored.score
        imp.score_breakdown = breakdown
        imp.status = EmailImportStatus.CANDIDATE

    if scored.score < settings.gmail_min_score or not scored.eligible_attachments:
        imp.status = EmailImportStatus.SKIPPED
        imp.notes = "; ".join(breakdown.get("reasons", []))
        log_action(
            db,
            actor=actor,
            action="email.sync.skip",
            entity_type="email_import",
            entity_id=imp.id,
            details=f"Skipped: score={scored.score:.2f} < threshold={settings.gmail_min_score}",
            extra={"breakdown": breakdown},
        )
        report.skipped += 1
        return

    imp.status = EmailImportStatus.DOWNLOADING
    log_action(
        db,
        actor=actor,
        action="email.sync.candidate",
        entity_type="email_import",
        entity_id=imp.id,
        details=(
            f"Candidate: {full.subject or '(no subject)'} from {full.sender or '?'} "
            f"(score={scored.score:.2f})"
        ),
        extra={"breakdown": breakdown},
    )

    imported_invoices: list[int] = []
    for hint in scored.eligible_attachments:
        # Find the matching attachment ref
        ref = next(
            (a for a in full.attachments if a.filename == hint.filename),
            None,
        )
        if ref is None:
            continue
        try:
            data = client.download_attachment(full.id, ref.attachment_id)
        except GmailClientError as exc:
            report.errors += 1
            _record_attachment_error(db, imp, hint.filename, str(exc))
            continue

        att = (
            db.query(EmailAttachment)
            .filter(EmailAttachment.email_import_id == imp.id)
            .filter(EmailAttachment.provider_attachment_id == ref.attachment_id)
            .first()
        )
        if att is None:
            att = EmailAttachment(
                email_import_id=imp.id,
                provider_attachment_id=ref.attachment_id,
                filename=ref.filename,
                mime_type=ref.mime_type,
                size=ref.size or len(data),
                status="downloaded",
            )
            db.add(att)
            db.flush()
        else:
            att.status = "downloaded"
            att.size = ref.size or len(data)

        # Duplicate detection by file hash.
        from ...utils.hashing import sha256_bytes
        file_hash = sha256_bytes(data)
        existing = (
            db.query(InvoiceFile).filter(InvoiceFile.file_hash == file_hash).first()
        )
        if existing is not None:
            att.file_hash = file_hash
            att.status = "duplicate"
            att.processed_invoice_id = existing.id
            report.duplicates += 1
            log_action(
                db,
                actor=actor,
                action="email.sync.duplicate",
                entity_type="email_attachment",
                entity_id=att.id,
                details=(
                    f"Duplicate attachment {ref.filename} (already on invoice "
                    f"#{existing.id})"
                ),
                extra={"file_hash": file_hash, "invoice_id": existing.id},
            )
            continue

        # Store + run Phase 1 pipeline
        try:
            stored = storage.store_upload(
                settings, data=data, original_filename=ref.filename
            )
        except UnsupportedFileType as exc:
            att.status = "skipped"
            att.error = str(exc)[:1000]
            report.skipped += 1
            log_action(
                db,
                actor=actor,
                action="email.sync.attachment_skipped",
                entity_type="email_attachment",
                entity_id=att.id,
                details=f"Skipped {ref.filename}: {exc}",
            )
            continue

        att.file_hash = stored.file_hash
        att.stored_path = stored.stored_path
        att.status = "extracting"

        inv = extraction.extract_and_persist(
            db,
            settings,
            stored_path=stored.stored_path,
            original_filename=stored.original_filename,
            file_hash=stored.file_hash,
            mime_type=stored.mime_type,
            size=stored.size,
            actor=actor,
            record_audit=False,  # we attach our own richer audit entries below
        )
        # Attach provenance on the InvoiceFile row
        if inv.file is not None:
            inv.file.source = "email"
            inv.file.email_import_id = imp.id
            inv.file.email_attachment_id = att.id
            db.flush()

        att.processed_invoice_id = inv.id
        att.status = "imported"
        imported_invoices.append(inv.id)
        report.imported += 1
        report.invoices.append(inv.id)

        log_action(
            db,
            actor=actor,
            action="email.sync.imported",
            entity_type="email_attachment",
            entity_id=att.id,
            details=f"Imported {ref.filename} as invoice #{inv.id}",
            extra={
                "file_hash": stored.file_hash,
                "invoice_id": inv.id,
                "invoice_status": inv.status.value,
            },
        )

    if imported_invoices:
        imp.status = EmailImportStatus.IMPORTED
    elif report.duplicates and not imported_invoices:
        imp.status = EmailImportStatus.DUPLICATE
    else:
        imp.status = EmailImportStatus.SKIPPED
    db.flush()


def _record_attachment_error(
    db: Session, imp: EmailImport, filename: str, error: str
) -> None:
    from ...services.audit import log_action

    att = EmailAttachment(
        email_import_id=imp.id,
        filename=filename,
        status="error",
        error=error[:1000],
    )
    db.add(att)
    db.flush()
    log_action(
        db,
        actor="system",
        action="email.sync.attachment_error",
        entity_type="email_attachment",
        entity_id=att.id,
        details=f"Error downloading {filename}: {error[:200]}",
    )
