"""Phase 16B/17 — Role-based permission endpoints (authenticated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.role_permission import PERMISSION_NAMES, ROLES, RolePermission
from ..models.user import User
from ..routers.auth import get_current_user
from ..schemas.safety import (
    MyPermissionsRead,
    PermissionEntry,
    RolePermissionRead,
    RolePermissionUpdateRequest,
)
from ..services.permissions import (
    check_permission,
    get_role_permissions,
    seed_default_permissions,
    update_permissions,
)

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


@router.get("", response_model=list[RolePermissionRead])
def list_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_permission(db, current_user.role, "manage_permissions") and current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    seed_default_permissions(db)
    rows = db.query(RolePermission).order_by(RolePermission.role, RolePermission.permission_name).all()
    return [
        RolePermissionRead(
            id=r.id,
            role=r.role,
            permission_name=r.permission_name,
            enabled=r.enabled,
            created_at=r.created_at.isoformat() if r.created_at else None,
            updated_at=r.updated_at.isoformat() if r.updated_at else None,
        )
        for r in rows
    ]


@router.patch("/{role}", response_model=list[RolePermissionRead])
def patch_role_permissions(
    role: str,
    body: RolePermissionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_permission(db, current_user.role, "manage_permissions") and current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Only owner can manage permissions")

    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role: %s" % role)

    entries = [e.model_dump() for e in body.entries]
    updated = update_permissions(db, role, entries)
    db.commit()
    return [
        RolePermissionRead(
            id=r.id,
            role=r.role,
            permission_name=r.permission_name,
            enabled=r.enabled,
            created_at=r.created_at.isoformat() if r.created_at else None,
            updated_at=r.updated_at.isoformat() if r.updated_at else None,
        )
        for r in updated
    ]


@router.get("/me", response_model=MyPermissionsRead)
def my_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    seed_default_permissions(db)
    perms = get_role_permissions(db, current_user.role)
    return MyPermissionsRead(role=current_user.role, permissions=sorted(perms))


@router.get("/roles")
def list_roles(
    current_user: User = Depends(get_current_user),
):
    return sorted(ROLES)


@router.get("/permission-names")
def list_permission_names(
    current_user: User = Depends(get_current_user),
):
    return sorted(PERMISSION_NAMES)
