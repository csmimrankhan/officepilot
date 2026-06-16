"""Phase 38.6 Task 2 — QuickBooks sync state (read-only data)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class QuickBooksSyncState(Base):
    __tablename__ = "quickbooks_sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    accounts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    customers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invoices_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accounts_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    customers_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    invoices_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="never", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
