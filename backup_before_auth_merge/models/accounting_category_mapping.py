"""Phase 13 — category/account mappings between local invoice
categories and external accounting provider account/tax codes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class AccountingCategoryMapping(Base):
    __tablename__ = "accounting_category_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    local_category: Mapped[str] = mapped_column(String(255), nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_account_name: Mapped[str] = mapped_column(
        String(255), default="", nullable=False
    )
    external_tax_code: Mapped[str] = mapped_column(
        String(64), default="", nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
