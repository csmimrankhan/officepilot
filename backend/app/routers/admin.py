from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..config import get_settings, Settings
from ..db import get_db
from ..models.audit_log import AuditLog
from ..models.app_release import AppRelease
from ..models.oauth_account import OAuthAccount
from ..models.user import User
from ..models.user_session import UserSession
from ..services.auth import (
    create_password_reset_token,
    hash_password,
    require_admin,
    revoke_all_user_sessions,
    validate_password_strength,
)
from ..services import windows_voice_layer as voice_svc
from .auth import get_current_admin_user, get_current_user

logger = logging.getLogger("officepilot.admin_router")
APP_PHASE = 37

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Schemas ──────────────────────────────────────────────────────────


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "user"
    email_verified: bool = False


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserListResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    status: str
    email_verified: bool
    auth_provider: str = "email"
    created_at: str
    last_login_at: Optional[str] = None
    last_active_at: Optional[str] = None
    login_count: int = 0
    gmail_connected: bool = False
    cloud_ai_allowed: bool = False

    class Config:
        from_attributes = True


class UserListResult(BaseModel):
    items: list[UserListResponse]
    total: int
    page: int
    page_size: int


class UserDetailResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    status: str
    email_verified: bool
    auth_provider: str = "email"
    created_at: str
    updated_at: str
    last_login_at: Optional[str] = None
    last_active_at: Optional[str] = None
    login_count: int = 0
    failed_login_count: int = 0
    is_active: bool = True
    gmail_connected: bool = False
    cloud_ai_allowed: bool = False

    class Config:
        from_attributes = True


class AuditLogEntry(BaseModel):
    id: int
    timestamp: str
    actor: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    details: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogResult(BaseModel):
    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int


# ── Helpers ──────────────────────────────────────────────────────────


def _format_user_response(user: User, db: Session) -> UserListResponse:
    settings = get_settings()
    gmail_connected = db.query(OAuthAccount).filter(
        OAuthAccount.user_id == user.id,
        OAuthAccount.provider == "gmail",
    ).count() > 0
    cloud_ai_allowed = settings.agent_allow_cloud or settings.ai_mode_allow_cloud or (
        settings.voice_provider == "openai" and settings.voice_allow_cloud_stt
    )
    return UserListResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        status=user.status,
        email_verified=user.email_verified,
        auth_provider=user.auth_provider or "email",
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        last_active_at=user.last_active_at.isoformat() if user.last_active_at else None,
        login_count=user.login_count or 0,
        gmail_connected=gmail_connected,
        cloud_ai_allowed=cloud_ai_allowed,
    )


def _format_user_detail(user: User, db: Session) -> UserDetailResponse:
    settings = get_settings()
    gmail_connected = db.query(OAuthAccount).filter(
        OAuthAccount.user_id == user.id,
        OAuthAccount.provider == "gmail",
    ).count() > 0
    cloud_ai_allowed = settings.agent_allow_cloud or settings.ai_mode_allow_cloud or (
        settings.voice_provider == "openai" and settings.voice_allow_cloud_stt
    )
    return UserDetailResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        status=user.status,
        email_verified=user.email_verified,
        auth_provider=user.auth_provider or "email",
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        last_active_at=user.last_active_at.isoformat() if user.last_active_at else None,
        login_count=user.login_count or 0,
        failed_login_count=user.failed_login_count or 0,
        is_active=user.is_active,
        gmail_connected=gmail_connected,
        cloud_ai_allowed=cloud_ai_allowed,
    )


def _write_audit_log(db: Session, actor: str, action: str, entity_type: str, entity_id: str, details: str = "") -> None:
    log = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=int(entity_id) if entity_id.isdigit() else None,
        details=details,
        timestamp=datetime.utcnow(),
    )
    db.add(log)
    db.flush()


# ── User Management Endpoints ────────────────────────────────────────


@router.get("/users", response_model=UserListResult)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    auth_provider: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(User)
    if search:
        like = f"%{search}%"
        q = q.filter(User.email.ilike(like) | User.full_name.ilike(like))
    if role:
        q = q.filter(User.role == role)
    if status:
        q = q.filter(User.status == status)
    if auth_provider:
        q = q.filter(User.auth_provider == auth_provider)

    total = q.count()
    items = q.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return UserListResult(
        items=[_format_user_response(u, db) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/users", response_model=UserDetailResponse, status_code=201)
def admin_create_user(
    body: CreateUserRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    pw_err = validate_password_strength(body.password)
    if pw_err:
        raise HTTPException(status_code=400, detail=pw_err)

    if not body.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required")

    allowed_roles = ("owner", "admin", "user", "viewer")
    if body.role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(allowed_roles)}")

    pw_hash = hash_password(body.password)
    now = datetime.utcnow()
    user = User(
        email=body.email,
        password_hash=pw_hash,
        full_name=body.full_name.strip(),
        role=body.role,
        status="active",
        auth_provider="email",
        created_at=now,
        updated_at=now,
        email_verified=body.email_verified,
        is_active=True,
        failed_login_count=0,
        login_count=0,
    )
    db.add(user)
    db.flush()
    _write_audit_log(db, current_user.email, "admin.create_user", "user", str(user.id),
                     f"Created user {body.email} with role {body.role} by {current_user.email}")
    db.commit()
    db.refresh(user)
    return _format_user_detail(user, db)


@router.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _format_user_detail(user, db)


@router.patch("/users/{user_id}", response_model=UserDetailResponse)
def update_user(
    user_id: int,
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.email is not None:
        existing = db.query(User).filter(User.email == body.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = body.email
    if body.role is not None:
        user.role = body.role
    if body.status is not None:
        user.status = body.status
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = hash_password(body.password)

    user.updated_at = datetime.utcnow()
    _write_audit_log(db, current_user.email, "admin.update_user", "user", str(user_id), f"Updated fields by {current_user.email}")
    db.commit()
    db.refresh(user)
    return _format_user_detail(user, db)


@router.post("/users/{user_id}/suspend", response_model=dict)
def suspend_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "owner" and current_user.id != user.id:
        other_owners = db.query(User).filter(User.role == "owner", User.id != user_id, User.status == "active").count()
        if other_owners == 0:
            raise HTTPException(status_code=400, detail="Cannot suspend the only owner")
    user.status = "suspended"
    user.updated_at = datetime.utcnow()
    revoke_all_user_sessions(db, user_id)
    _write_audit_log(db, current_user.email, "admin.suspend_user", "user", str(user_id), f"Suspended by {current_user.email}")
    db.commit()
    return {"ok": True, "message": f"User {user_id} suspended"}


@router.post("/users/{user_id}/activate", response_model=dict)
def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "active"
    user.is_active = True
    user.failed_login_count = 0
    user.locked_until = None
    user.updated_at = datetime.utcnow()
    _write_audit_log(db, current_user.email, "admin.activate_user", "user", str(user_id), f"Activated by {current_user.email}")
    db.commit()
    return {"ok": True, "message": f"User {user_id} activated"}


@router.post("/users/{user_id}/force-logout", response_model=dict)
def force_logout(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    count = revoke_all_user_sessions(db, user_id)
    _write_audit_log(db, current_user.email, "admin.force_logout", "user", str(user_id), f"Forced logout by {current_user.email}, {count} sessions revoked")
    db.commit()
    return {"ok": True, "message": f"Force logged out user {user_id}", "sessions_revoked": count}


@router.post("/users/{user_id}/reset-password-link", response_model=dict)
def reset_password_link(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.password_hash is None:
        raise HTTPException(status_code=400, detail="User has no password (OAuth-only)")
    reset_token = create_password_reset_token(db, user.id)
    db.commit()
    _write_audit_log(db, current_user.email, "admin.reset_password_link", "user", str(user_id), f"Reset password link generated by {current_user.email}")
    return {"ok": True, "message": "Password reset link generated", "reset_token": reset_token}


@router.get("/users/{user_id}/audit", response_model=AuditLogResult)
def user_audit(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    q = db.query(AuditLog).filter(
        AuditLog.entity_type == "user",
        AuditLog.entity_id == str(user_id),
    )
    total = q.count()
    items = q.order_by(AuditLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return AuditLogResult(
        items=[
            AuditLogEntry(
                id=log.id,
                timestamp=log.timestamp.isoformat(),
                actor=log.actor,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=str(log.entity_id) if log.entity_id else None,
                details=log.details,
            )
            for log in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Audit Logs ───────────────────────────────────────────────────────


@router.get("/audit-logs", response_model=AuditLogResult)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    actor: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if actor:
        q = q.filter(AuditLog.actor.ilike(f"%{actor}%"))

    total = q.count()
    items = q.order_by(AuditLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return AuditLogResult(
        items=[
            AuditLogEntry(
                id=log.id,
                timestamp=log.timestamp.isoformat(),
                actor=log.actor,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=str(log.entity_id) if log.entity_id else None,
                details=log.details,
            )
            for log in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Release Admin ──────────────────────────────────────────────────────────


class ReleaseCreateRequest(BaseModel):
    version: str
    platform: str = "windows"
    channel: str = "stable"
    target: str | None = "windows-x86_64"
    artifact_type: str | None = "nsis"
    download_url: str
    updater_url: str | None = None
    updater_artifact_url: str | None = None
    updater_signature: str | None = None
    pub_date: str | None = None
    release_notes: str | None = None
    minimum_required_version: str | None = None
    is_critical: bool = False


class ReleaseResponse(BaseModel):
    id: int
    version: str
    platform: str
    channel: str
    target: str | None
    artifact_type: str | None
    download_url: str
    updater_url: str | None
    updater_artifact_url: str | None
    updater_signature: str | None
    pub_date: str | None
    release_notes: str | None
    minimum_required_version: str | None
    is_critical: bool
    created_at: str

    class Config:
        from_attributes = True


@router.get("/releases", response_model=list[ReleaseResponse])
def list_releases(
    platform: str | None = None,
    channel: str | None = None,
    _admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(AppRelease)
    if platform:
        q = q.filter(AppRelease.platform == platform)
    if channel:
        q = q.filter(AppRelease.channel == channel)
    releases = q.order_by(AppRelease.created_at.desc()).all()
    return releases


@router.post("/releases", response_model=ReleaseResponse, status_code=201)
def create_release(
    body: ReleaseCreateRequest,
    _admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    release = AppRelease(**body.model_dump())
    db.add(release)
    db.commit()
    db.refresh(release)
    return release


@router.delete("/releases/{release_id}")
def delete_release(
    release_id: int,
    _admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    release = db.query(AppRelease).filter(AppRelease.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    db.delete(release)
    db.commit()
    return {"ok": True}


# ── System Health ──────────────────────────────────────────────────────


@router.get("/system-health")
def system_health(
    _admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    import os as _os
    import sys as _sys
    from .. import __version__

    is_frozen = bool(getattr(_sys, "frozen", False))
    sidecar_env = _os.environ.get("OFFICEPILOT_SIDECAR", "")
    is_sidecar = is_frozen or sidecar_env.lower() in ("1", "true", "yes", "on")

    db_ok = False
    db_error = None
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_error = str(e)

    whisper_status = voice_svc.detect_whisper_status()
    whisper_ok = whisper_status.get("whisper_configured", False)
    gmail_ok = settings.gmail_configured
    browser_ok = settings.browser_enabled
    excel_ok = True
    recorder_ok = settings.workflow_recording_enabled

    return {
        "version": __version__,
        "phase": APP_PHASE,
        "timestamp": datetime.utcnow().isoformat(),
        "backend": {"status": "ok"},
        "database": {"status": "ok" if db_ok else "error", "error": db_error},
        "sidecar": {"status": "bundled" if is_sidecar else "system-python", "bundled": is_sidecar},
        "updater": {"status": "enabled"},
        "gmail_readonly": {"status": "configured" if gmail_ok else "not_configured", "configured": gmail_ok},
        "excel_automation": {"status": "ok", "enabled": excel_ok},
        "workflow_recorder": {"status": "enabled" if recorder_ok else "disabled", "enabled": recorder_ok},
        "browser_automation": {"status": "enabled" if browser_ok else "disabled", "enabled": browser_ok},
        "local_whisper": {
            "status": "ready" if whisper_ok else "not_configured",
            "cli_found": whisper_status.get("whisper_cli_found", False),
            "model_found": whisper_status.get("whisper_model_found", False),
            "message": whisper_status.get("message", ""),
        },
        "llm_provider": {
            "provider": settings.agent_provider,
            "allow_cloud": settings.agent_allow_cloud,
            "cloud_ai_allowed": settings.agent_allow_cloud,
        },
    }


# ── AI Status ──────────────────────────────────────────────────────────


@router.get("/ai-status")
def ai_status(
    _admin: User = Depends(get_current_admin_user),
    settings: Settings = Depends(get_settings),
):
    agent_provider = settings.agent_provider
    agent_allow_cloud = settings.agent_allow_cloud
    agent_key_configured = bool(settings.agent_api_key)
    agent_model = settings.agent_model or ("deepseek-chat" if agent_provider == "deepseek" else "")
    agent_api_base = settings.agent_api_base_url or (
        "https://api.deepseek.com" if agent_provider == "deepseek"
        else "https://api.openai.com/v1" if agent_provider == "openai_compatible"
        else ""
    )

    ai_mode_provider = settings.ai_mode_provider
    ai_mode_allow_cloud = settings.ai_mode_allow_cloud
    ai_mode_key_configured = bool(settings.ai_mode_api_key)
    ai_mode_model = settings.ai_mode_model or "gpt-4o-mini"

    voice_provider = settings.voice_provider
    voice_allow_cloud_stt = settings.voice_allow_cloud_stt
    openai_key_configured = bool(settings.openai_api_key)

    return {
        "agent_provider": agent_provider,
        "agent_model": agent_model,
        "agent_api_base_url": agent_api_base,
        "agent_api_key_configured": agent_key_configured,
        "agent_allow_cloud": agent_allow_cloud,
        "ai_mode_provider": ai_mode_provider,
        "ai_mode_model": ai_mode_model,
        "ai_mode_api_key_configured": ai_mode_key_configured,
        "ai_mode_allow_cloud": ai_mode_allow_cloud,
        "voice_provider": voice_provider,
        "voice_allow_cloud_stt": voice_allow_cloud_stt,
        "openai_api_key_configured": openai_key_configured,
        "cloud_ai_allowed": agent_allow_cloud or ai_mode_allow_cloud or (voice_provider == "openai" and voice_allow_cloud_stt),
        "zero_cloud_by_default": not agent_allow_cloud and not ai_mode_allow_cloud and (voice_provider != "openai" or not voice_allow_cloud_stt),
        "message": "OfficePilot runs fully without LLM. Cloud AI is optional and disabled by default.",
    }
