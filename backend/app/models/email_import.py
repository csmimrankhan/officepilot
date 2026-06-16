"""Per-email import records (one per Gmail message we considered)."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class EmailImportStatus(str, enum.Enum):
    CANDIDATE = "candidate"      # matched keyword rules, score above threshold
    DOWNLOADING = "downloading"  # attachment download in progress
    IMPORTED = "imported"        # at least one attachment produced an invoice
    DUPLICATE = "duplicate"      # all attachments already existed by hash
    SKIPPED = "skipped"          # below score threshold or no usable attachment
    ERROR = "error"              # exception during processing


class EmailImport(Base):
    __tablename__ = "email_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_message_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    thread_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    sender: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[EmailImportStatus] = mapped_column(
        Enum(EmailImportStatus, native_enum=False, length=16),
        default=EmailImportStatus.CANDIDATE,
        nullable=False,
        index=True,
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    account = relationship("EmailAccount", back_populates="imports")
    attachments = relationship(
        "EmailAttachment", back_populates="email_import", cascade="all, delete-orphan"
    )
