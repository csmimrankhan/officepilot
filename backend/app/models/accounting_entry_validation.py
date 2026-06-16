"""Phase 13 — read-back validation that compares the source
invoice fields against the created accounting record."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


VALIDATION_STATUSES = {"validated", "mismatch", "needs_review", "failed"}


class AccountingEntryValidation(Base):
    __tablename__ = "accounting_entry_validations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    invoice_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sync_log_id: Mapped[int] = mapped_column(Integer, nullable=False)
    external_record_id: Mapped[str] = mapped_column(
        String(255), default="", nullable=False
    )
    source_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    accounting_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    differences_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    validation_status: Mapped[str] = mapped_column(
        String(16), default="needs_review", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
