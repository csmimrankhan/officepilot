"""Phase 13 — vendor/contact mappings between local invoice vendor
names and external accounting provider contact/vendor IDs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class AccountingVendorMapping(Base):
    __tablename__ = "accounting_vendor_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    local_vendor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_contact_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_contact_name: Mapped[str] = mapped_column(
        String(255), default="", nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
