"""Pydantic schemas for invoices, files, line items, and audit logs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.invoice import InvoiceStatus


class InvoiceFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_filename: str
    stored_path: str
    file_hash: str
    mime_type: str
    size: int
    source: str = "upload"
    email_import_id: Optional[int] = None
    email_attachment_id: Optional[int] = None
    original_path: Optional[str] = None
    current_path: Optional[str] = None
    organized_path: Optional[str] = None
    created_at: datetime


class InvoiceLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None
    position: int


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    confidence_score: float
    warnings_json: list[str] = Field(default_factory=list)
    status: InvoiceStatus
    notes: Optional[str] = None
    duplicate_of_invoice_id: Optional[int] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    file: Optional[InvoiceFileRead] = None
    line_items: list[InvoiceLineItemRead] = Field(default_factory=list)


class InvoiceUpdate(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    notes: Optional[str] = None
    line_items: Optional[list[dict]] = None


class InvoiceCreate(BaseModel):
    """Used internally; uploads go through a dedicated endpoint."""
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total_amount: Optional[float] = None


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: datetime
    actor: str
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[str] = None
    extra_json: dict = Field(default_factory=dict)
    before_data_json: Optional[dict] = None
    after_data_json: Optional[dict] = None


class ReviewQueueItem(BaseModel):
    """Item shape for the grouped review-queue endpoint."""
    id: int
    status: InvoiceStatus
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    confidence_score: float
    updated_at: datetime
    source: Optional[str] = None
    duplicate_of_invoice_id: Optional[int] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None


class ReviewQueueRead(BaseModel):
    by_status: dict[str, list[ReviewQueueItem]]
    counts: dict[str, int]
