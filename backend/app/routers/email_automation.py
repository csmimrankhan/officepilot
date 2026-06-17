"""Phase 34 — Email Automation HTTP API.

All endpoints under /api/email.
Every endpoint is user-scoped via JWT auth.
Read-only: never send, delete, modify, or mark emails.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.gmail_readonly_service import (
    download_attachment,
    download_matching_attachments,
    get_email_preview,
    list_attachments,
    search_emails,
)
from ..services.audit import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/email", tags=["email"])


# ── Request / Response models ───────────────────────────────────────────────


class SearchRequest(BaseModel):
    provider: str = "gmail"
    query: str = "has:attachment newer_than:30d invoice OR receipt OR bill"
    max_results: int = 10


class SearchResponse(BaseModel):
    status: str
    search_run_id: int = 0
    query: str = ""
    messages: list[dict] = []
    result_count: int = 0
    requires_approval: bool = False
    mode: str = "live"


class PreviewRequest(BaseModel):
    provider: str = "gmail"
    message_id: str
    account_email: str = ""


class PreviewResponse(BaseModel):
    message_id: str
    from_: str = ""
    subject: str = ""
    date: str = ""
    snippet: str = ""
    body: str = ""
    attachments: list[dict] = []
    has_attachments: bool = False
    mode: str = "live"


class AttachmentsRequest(BaseModel):
    provider: str = "gmail"
    message_ids: list[str]
    output_folder: str = ""


class DownloadRequest(BaseModel):
    provider: str = "gmail"
    message_id: str
    attachment_id: str
    output_folder: str = ""


class DownloadResponse(BaseModel):
    status: str
    download_id: int = 0
    filename: str = ""
    saved_path: str = ""
    size_bytes: int = 0
    mime_type: str = ""


class AccountListResponse(BaseModel):
    accounts: list[dict] = []
    connected: bool = False


# ── Routes ──────────────────────────────────────────────────────────────────


@router.get("/accounts", response_model=AccountListResponse)
def list_email_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List connected email accounts for the current user."""
    from ..models.email_account import EmailAccount, EmailAccountStatus, EmailProvider
    accounts = (
        db.query(EmailAccount)
        .filter(EmailAccount.provider == EmailProvider.GMAIL)
        .filter(EmailAccount.status == EmailAccountStatus.CONNECTED)
        .all()
    )
    return AccountListResponse(
        accounts=[
            {
                "id": a.id,
                "provider": a.provider.value,
                "email": a.email,
                "status": a.status.value,
                "connected_at": a.connected_at.isoformat() if a.connected_at else None,
            }
            for a in accounts
        ],
        connected=len(accounts) > 0,
    )


@router.post("/search", response_model=SearchResponse)
def email_search(
    payload: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search emails by query. Returns message list with attachment metadata."""
    if payload.provider != "gmail":
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {payload.provider}")
    result = search_emails(db, current_user.id, payload.query, payload.max_results)
    log_action(
        db, actor=str(current_user.id),
        action="email_automation.search",
        entity_type="email_search_run", entity_id=result.get("search_run_id", 0),
        details=f"Search: {payload.query} → {result.get('result_count', 0)} results",
    )
    return SearchResponse(
        status=result.get("status", "success"),
        search_run_id=result.get("search_run_id", 0),
        query=result.get("query", payload.query),
        messages=result.get("messages", []),
        result_count=result.get("result_count", 0),
        requires_approval=result.get("requires_approval", False),
        mode=result.get("mode", "live"),
    )


@router.post("/preview", response_model=PreviewResponse)
def email_preview(
    payload: PreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview a single email message with its attachments."""
    result = get_email_preview(db, current_user.id, payload.message_id)
    log_action(
        db, actor=str(current_user.id),
        action="email_automation.preview",
        entity_type="email_message",
        entity_id=0,
        details=f"Previewed message {payload.message_id[:20]}",
    )
    return PreviewResponse(
        message_id=result.get("message_id", payload.message_id),
        from_=result.get("from", ""),
        subject=result.get("subject", ""),
        date=result.get("date", ""),
        snippet=result.get("snippet", ""),
        body=result.get("body", ""),
        attachments=result.get("attachments", []),
        has_attachments=result.get("has_attachments", False),
        mode=result.get("mode", "live"),
    )


@router.post("/attachments/preview", response_model=PreviewResponse)
def email_attachments_preview(
    payload: PreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview attachments on a specific message."""
    return email_preview(payload, current_user, db)


@router.post("/attachments/download", response_model=DownloadResponse)
def email_attachment_download(
    payload: DownloadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a single attachment. Requires approval flag before calling."""
    from ..config import get_settings as _get_settings
    output = payload.output_folder or str(
        _get_settings().data_dir / "email_downloads"
    )
    result = download_attachment(
        db, current_user.id, payload.message_id,
        payload.attachment_id, output,
    )
    log_action(
        db, actor=str(current_user.id),
        action="email_automation.download",
        entity_type="email_attachment_download",
        entity_id=result.get("download_id", 0),
        details=f"Downloaded {result.get('filename', '?')}",
    )
    return DownloadResponse(
        status=result.get("status", "success"),
        download_id=result.get("download_id", 0),
        filename=result.get("filename", ""),
        saved_path=result.get("saved_path", ""),
        size_bytes=result.get("size_bytes", 0),
        mime_type=result.get("mime_type", ""),
    )


@router.post("/batch-download")
def email_batch_download(
    payload: AttachmentsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Batch download attachments from multiple messages."""
    from ..config import get_settings as _get_settings
    output = payload.output_folder or str(
        _get_settings().data_dir / "email_downloads"
    )
    downloads = []
    for msg_id in payload.message_ids:
        attachments = list_attachments(db, current_user.id, msg_id)
        for att in attachments:
            result = download_attachment(
                db, current_user.id, msg_id,
                att["attachment_id"], output,
            )
            downloads.append(result)
    return {
        "status": "success",
        "downloads": downloads,
        "total_downloaded": len(downloads),
        "output_folder": output,
    }
