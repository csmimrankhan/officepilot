"""Phase 15 — screen control policy (single-row config)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


PERMISSION_LEVELS = {0, 1, 2, 3, 4, 5}

DEFAULT_ALLOWED_APPS: list[str] = [
    "officepilot",
    "invoicepilot",
]

DEFAULT_BLOCKED_APPS: list[str] = [
    "password_manager",
    "banking",
    "security_settings",
    "credential_dialog",
]

DEFAULT_ALLOWED_FOLDERS: list[str] = []

DEFAULT_BLOCKED_DOMAINS: list[str] = [
    "chase.com", "bankofamerica.com", "wellsfargo.com", "citi.com",
    "paypal.com", "venmo.com", "coinbase.com", "kraken.com",
    "binance.com", "gemini.com", "1password.com", "lastpass.com",
    "bitwarden.com", "irs.gov", "hmrc.gov.uk",
]


class ScreenControlPolicy(Base):
    __tablename__ = "screen_control_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permission_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    screenshots_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ocr_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    click_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    type_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clipboard_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allowed_apps_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    blocked_apps_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    allowed_folders_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    blocked_domains_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    require_approval_for_click: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_approval_for_type: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_approval_for_submit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_approval_for_clipboard: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    emergency_stop_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
