"""Phase 13 — accounting provider OAuth connection.

One row per connected QuickBooks / Xero account. Tokens are
encrypted with the same Fernet key used for Gmail tokens.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


CONNECTION_STATUSES = {"active", "expired", "error", "disconnected"}
PROVIDERS = {"quickbooks", "xero"}


class AccountingConnection(Base):
    __tablename__ = "accounting_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    realm_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(
        Text, default="", nullable=False
    )
    refresh_token_encrypted: Mapped[str] = mapped_column(
        Text, default="", nullable=False
    )
    scopes_json: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False
    )
    environment: Mapped[str] = mapped_column(
        String(16), default="sandbox", nullable=False
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    disconnected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
