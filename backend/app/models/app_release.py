from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class AppRelease(Base):
    __tablename__ = "app_releases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default="windows")
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="stable")
    target: Mapped[str | None] = mapped_column(String(64), nullable=True, default="windows-x86_64")
    artifact_type: Mapped[str | None] = mapped_column(String(32), nullable=True, default="nsis")
    download_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    updater_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updater_artifact_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updater_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    pub_date: Mapped[str | None] = mapped_column(String(64), nullable=True)
    release_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    minimum_required_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
