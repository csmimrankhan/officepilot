"""Phase 16B — Role-based permission definitions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


ROLES = {"owner", "admin", "reviewer", "staff", "viewer"}

PERMISSION_NAMES = {
    "manage_safety_policies",
    "manage_permissions",
    "manage_integrations",
    "manage_accounting_sync",
    "manage_screen_control",
    "manage_workflow_recording",
    "manage_browser_automation",
    "manage_users",
    "manage_workflows",
    "export_audit",
    "view_audit_logs",
    "approve_invoices",
    "approve_sync_previews",
    "edit_extracted_fields",
    "upload_invoices",
    "import_invoices",
    "view_reports",
    "view_logs",
}


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    permission_name: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
