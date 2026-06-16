"""Connected email account (Phase 2). Stores encrypted OAuth tokens."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class EmailProvider(str, enum.Enum):
    GMAIL = "gmail"


class EmailAccountStatus(str, enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[EmailProvider] = mapped_column(
        Enum(EmailProvider, native_enum=False, length=16),
        default=EmailProvider.GMAIL,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    # Encrypted (Fernet) token payload. The plaintext is a serialized dict.
    access_token_enc: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    refresh_token_enc: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    token_uri: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    scopes: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    expiry: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[EmailAccountStatus] = mapped_column(
        Enum(EmailAccountStatus, native_enum=False, length=16),
        default=EmailAccountStatus.CONNECTED,
        nullable=False,
        index=True,
    )
    last_error: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    imports = relationship("EmailImport", back_populates="account", cascade="all, delete-orphan")
