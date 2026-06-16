"""Phase 12 — browser automation policy.

A single-row configuration table for the browser automation
feature. The same row is upserted whenever the user toggles a
setting, manages the domain allowlist / blocklist, or enables /
disables screenshots. We keep ``allowed_domains_json`` and
``blocked_domains_json`` as JSON arrays (instead of a separate
``browser_allowed_domain`` table) because the lists are tiny
(dozens, not thousands) and the row is always read as a single
object by the adapter.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


DEFAULT_ALLOWED_DOMAINS: list[str] = [
    "localhost",
    "127.0.0.1",
    "docs.google.com",
    "sheets.google.com",
    # QuickBooks
    "sandbox.qbo.intuit.com",
    "qbo.intuit.com",
    "developer.intuit.com",
    "appcenter.intuit.com",
    # Xero
    "login.xero.com",
    "go.xero.com",
    "api.xero.com",
    # FreshBooks
    "my.freshbooks.com",
    "api.freshbooks.com",
    # Wave
    "waveapps.com",
    "api.waveapps.com",
    # Zoho Books
    "books.zoho.com",
    "accounts.zoho.com",
    "api.books.zoho.com",
    # Sage
    "login.sage.com",
    "my.sage.com",
    # Odoo
    "odoo.com",
    "www.odoo.com",
]

DEFAULT_BLOCKED_DOMAINS: list[str] = [
    "chase.com",
    "bankofamerica.com",
    "wellsfargo.com",
    "citi.com",
    "paypal.com",
    "venmo.com",
    "coinbase.com",
    "kraken.com",
    "binance.com",
    "gemini.com",
    "1password.com",
    "lastpass.com",
    "bitwarden.com",
    "irs.gov",
    "hmrc.gov.uk",
]


class BrowserAutomationPolicy(Base):
    __tablename__ = "browser_automation_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    allowed_domains_json: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    blocked_domains_json: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    require_approval_for_submit: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    require_approval_for_write: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    screenshots_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    headless: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Free-text note for the operator explaining what is / isn't
    # in scope for the current policy.
    notes: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
