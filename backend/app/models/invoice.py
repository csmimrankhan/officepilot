"""Invoice model: status, confidence, warnings, extracted fields."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class InvoiceStatus(str, enum.Enum):
    IMPORTED = "imported"          # just arrived (upload or email)
    EXTRACTING = "extracting"      # extraction in progress
    NEEDS_REVIEW = "needs_review"  # low confidence or missing required fields
    READY_FOR_APPROVAL = "ready_for_approval"  # all required fields, awaiting user
    APPROVED = "approved"          # user approved, eligible for export
    REJECTED = "rejected"          # user rejected
    DUPLICATE = "duplicate"        # blocked by file_hash collision or manual mark
    EXPORTED = "exported"          # included in an Excel export


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Required / business fields
    vendor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    invoice_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    subtotal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tax: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Extraction quality
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    warnings_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Status & tracking
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, native_enum=False, length=32),
        default=InvoiceStatus.IMPORTED,
        nullable=False,
        index=True,
    )
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text_source: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Phase 3: trust layer
    duplicate_of_invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejected_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    file_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("invoice_files.id", ondelete="SET NULL"),
        nullable=True,
    )
    email_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    file = relationship("InvoiceFile", back_populates="invoices", foreign_keys=[file_id])
    line_items = relationship(
        "InvoiceLineItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    duplicate_of = relationship(
        "Invoice",
        remote_side="Invoice.id",
        foreign_keys=[duplicate_of_invoice_id],
    )
