"""Phase 13 — sync preview for an approved invoice before
the actual accounting API call is made.

The preview holds the mapped payload, blockers, warnings, and
risk level. The user must explicitly approve the preview before
the sync executes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


PREVIEW_STATUSES = {"pending", "approved", "rejected", "synced", "failed"}


class AccountingSyncPreview(Base):
    __tablename__ = "accounting_sync_previews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    invoice_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    preview_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    warnings_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    blockers_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risk_level: Mapped[str] = mapped_column(
        String(16), default="medium", nullable=False
    )
    approval_required: Mapped[bool] = mapped_column(default=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
