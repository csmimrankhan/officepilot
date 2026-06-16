"""Stores the original uploaded file path, hash, mime, size."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class InvoiceFile(Base):
    __tablename__ = "invoice_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    # Phase 2: nullable provenance links back to email imports.
    source: Mapped[str] = mapped_column(String(16), default="upload", nullable=False)
    email_import_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("email_imports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    email_attachment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("email_attachments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Phase 3: file organization
    original_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    current_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    organized_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    invoices = relationship(
        "Invoice",
        back_populates="file",
        foreign_keys="Invoice.file_id",
    )
    email_import = relationship("EmailImport", foreign_keys=[email_import_id])
    email_attachment = relationship("EmailAttachment", foreign_keys=[email_attachment_id])
