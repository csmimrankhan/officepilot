"""Phase 16B — Role-based permission enforcement."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from ..models.role_permission import PERMISSION_NAMES, ROLES, RolePermission

# Default permission map for each role.
# These are applied when no rows exist in the DB.
DEFAULT_PERMISSIONS: dict[str, set[str]] = {
    "owner": PERMISSION_NAMES,
    "admin": {
        "manage_integrations",
        "manage_workflows",
        "manage_workflow_recording",
        "manage_users",
        "export_audit",
        "view_audit_logs",
        "approve_invoices",
        "approve_sync_previews",
        "edit_extracted_fields",
        "upload_invoices",
        "import_invoices",
        "view_reports",
        "view_logs",
    },
    "reviewer": {
        "view_audit_logs",
        "approve_invoices",
        "approve_sync_previews",
        "edit_extracted_fields",
        "upload_invoices",
        "import_invoices",
        "view_reports",
        "view_logs",
    },
    "staff": {
        "upload_invoices",
        "import_invoices",
        "edit_extracted_fields",
        "view_logs",
    },
    "viewer": {
        "view_reports",
        "view_logs",
    },
}


def seed_default_permissions(db: Session) -> None:
    existing = db.query(RolePermission).count()
    if existing > 0:
        return
    now = datetime.utcnow()
    for role, perms in DEFAULT_PERMISSIONS.items():
        for perm in perms:
            db.add(RolePermission(
                role=role,
                permission_name=perm,
                enabled=True,
                created_at=now,
                updated_at=now,
            ))
    db.flush()


def get_role_permissions(db: Session, role: str) -> set[str]:
    rows = (
        db.query(RolePermission)
        .filter(RolePermission.role == role, RolePermission.enabled == True)
        .all()
    )
    return {r.permission_name for r in rows}


def check_permission(db: Session, role: str, permission: str) -> bool:
    row = (
        db.query(RolePermission)
        .filter(
            RolePermission.role == role,
            RolePermission.permission_name == permission,
            RolePermission.enabled == True,
        )
        .first()
    )
    return row is not None


def update_permissions(
    db: Session, role: str, entries: list[dict]
) -> list[RolePermission]:
    updated = []
    for entry in entries:
        name = entry["permission_name"]
        enabled = entry.get("enabled", True)
        row = (
            db.query(RolePermission)
            .filter(
                RolePermission.role == role,
                RolePermission.permission_name == name,
            )
            .first()
        )
        if row:
            row.enabled = enabled
            row.updated_at = datetime.utcnow()
        else:
            row = RolePermission(
                role=role,
                permission_name=name,
                enabled=enabled,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(row)
        db.flush()
        updated.append(row)
    return updated


def get_user_role(user_id: str) -> str:
    normalized = user_id.strip().lower()
    if normalized in ROLES:
        return normalized
    return "staff"
