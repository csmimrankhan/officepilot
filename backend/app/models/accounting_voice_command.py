"""Phase 13 — tracks voice-initiated accounting commands through
preview, approval, sync, and validation."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class AccountingVoiceCommand(Base):
    __tablename__ = "accounting_voice_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    voice_command_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    invoice_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preview_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approval_status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False
    )
    sync_log_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    validation_status: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
