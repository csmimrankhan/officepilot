"""Phase 22.5 — central model for voice commands and history."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, JSON, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class VoiceCommand(Base):
    __tablename__ = "voice_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_intent: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # idle, listening, transcribing, detected, pending_approval, executing, completed, failed
    status: Mapped[str] = mapped_column(String(32), default="idle", nullable=False)
    
    # browser, accounting, screen, invoice, excel, etc.
    domain: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    
    # specific action within the domain
    intent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    
    # linking to actual domain-specific rows (optional)
    external_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Phase 22.6
    provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    clarification_needed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clarification_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
