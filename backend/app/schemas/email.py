"""Pydantic schemas for email integrations (Phase 2)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.email_account import EmailAccountStatus, EmailProvider
from ..models.email_import import EmailImportStatus


class EmailAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email_import_id: int
    provider_attachment_id: Optional[str] = None
    filename: str
    mime_type: Optional[str] = None
    size: int
    file_hash: Optional[str] = None
    stored_path: Optional[str] = None
    processed_invoice_id: Optional[int] = None
    status: str
    error: Optional[str] = None
    created_at: datetime


class EmailImportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    account_id: int
    provider_message_id: str
    thread_id: Optional[str] = None
    sender: Optional[str] = None
    subject: Optional[str] = None
    snippet: Optional[str] = None
    received_at: Optional[datetime] = None
    score: float
    score_breakdown: dict = Field(default_factory=dict)
    status: EmailImportStatus
    error: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    attachments: list[EmailAttachmentRead] = Field(default_factory=list)


class EmailAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    provider: EmailProvider
    email: str
    status: EmailAccountStatus
    last_error: Optional[str] = None
    scopes: Optional[str] = None
    expiry: Optional[datetime] = None
    connected_at: datetime
    updated_at: datetime


class GmailStatusRead(BaseModel):
    configured: bool
    connected: bool
    account: Optional[EmailAccountRead] = None
    scopes: list[str] = Field(default_factory=list)
    note: Optional[str] = None


class SyncReportRead(BaseModel):
    account_id: int
    candidates: int
    imported: int
    duplicates: int
    skipped: int
    errors: int
    invoice_ids: list[int] = Field(default_factory=list)
