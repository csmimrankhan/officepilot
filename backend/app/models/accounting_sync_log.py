"""Phase 13 — sync log for every accounting API call (create,
update, validate). Request and response payloads are stored
redacted for audit."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


SYNC_LOG_STATUSES = {"pending", "success", "failed", "needs_review"}


class AccountingSyncLog(Base):
    __tablename__ = "accounting_sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    invoice_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    connection_id: Mapped[int] = mapped_column(Integer, nullable=False)
    preview_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    external_record_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    external_record_type: Mapped[str] = mapped_column(
        String(64), default="", nullable=False
    )
    request_json_redacted: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    response_json_redacted: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
