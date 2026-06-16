"""Phase 16B — Audit export jobs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class AuditExport(Base):
    __tablename__ = "audit_exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    export_type: Mapped[str] = mapped_column(String(20), default="json", nullable=False)
    date_from: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    date_to: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    log_types_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(String(500), default="", nullable=False)
