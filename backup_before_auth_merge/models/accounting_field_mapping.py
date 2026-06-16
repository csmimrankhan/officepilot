"""Phase 13 — field-level mappings between local invoice fields and
external accounting provider fields."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class AccountingFieldMapping(Base):
    __tablename__ = "accounting_field_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    local_field: Mapped[str] = mapped_column(String(64), nullable=False)
    external_field: Mapped[str] = mapped_column(String(128), nullable=False)
    mapping_config_json: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
