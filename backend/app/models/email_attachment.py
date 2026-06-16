"""Attachment rows for each EmailImport. Each is hashed and may be linked
back to the InvoiceFile it produced."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class EmailAttachment(Base):
    __tablename__ = "email_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email_import_id: Mapped[int] = mapped_column(
        ForeignKey("email_imports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_attachment_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    stored_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    processed_invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    error: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    email_import = relationship("EmailImport", back_populates="attachments")
    processed_invoice = relationship("Invoice", foreign_keys=[processed_invoice_id])
