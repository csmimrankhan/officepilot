"""OfficePilot Auth 2.0 — standardized authentication router."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.oauth_account import OAuthAccount
from ..models.user import User
from ..models.user_session import UserSession
from ..services.auth import (
    change_user_password,
    create_email_verification_token,
    create_password_reset_token,
    decode_token,
    get_google_authorization_url,
    get_user_count,
    google_exchange_code,
    google_login_configured,
    hash_password,
    login_or_register_google_user,
    login_user,
    logout_user,
    refresh_access_token,
    register_user,
    require_admin,
    reset_password_with_token,
    revoke_all_user_sessions,
    validate_password_strength,
    verify_email_token,
    verify_google_id_token,
    verify_password,
)
from ..services.email_service import send_password_reset_email, send_verification_email

logger = logging.getLogger("officepilot.auth_router")

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    full_name: str = ""
    email: str
    password: str
    confirm_password: str = ""

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if v and "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str = ""
    role: str = "user"
    status: str = "active"
    email_verified: bool = False
    auth_provider: str = "email"
    onboarding_completed: bool = False

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user: UserRead


class GoogleAuthUrlResponse(BaseModel):
    url: str
    configured: bool


# ── Dependencies ─────────────────────────────────────────────────────


def get_current_user(
    authorization: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = int(payload.get("sub", 0))
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if user.status != "active" or not user.is_active:
        raise HTTPException(status_code=401, detail="User account is disabled")
    if user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="User account has been deleted")

    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not require_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def get_optional_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    user_id = int(payload.get("sub", 0))
    return db.get(User, user_id)


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(
    body: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    pw_err = validate_password_strength(body.password)
    if pw_err:
        raise HTTPException(status_code=400, detail=pw_err)
    try:
        user = register_user(
            db=db,
            email=body.email.strip().lower(),
            password=body.password,
            full_name=body.full_name.strip(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Seed default Excel skills for new users
    try:
        from ..services.accounting_skills import seed_default_excel_skills
        seed_default_excel_skills(db, user.id)
    except Exception:
        logger.warning("Failed to seed default Excel skills", exc_info=True)

    # Create email verification token
    ver_token = create_email_verification_token(db, user.id)

    # Send verification email (non-blocking)
    try:
        send_verification_email(user.email, ver_token)
    except Exception:
        logger.warning("Failed to send verification email to %s", user.email)

    client_host = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")
    result = login_user(db, body.email.strip().lower(), body.password, user_agent=user_agent, ip_address=client_host)
    if result is None:
        raise HTTPException(status_code=500, detail="Registration succeeded but login failed")
    db.commit()
    return AuthResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type="bearer",
        user=UserRead(**result["user"]),
    )


@router.post("/login", response_model=AuthResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_host = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")
    result = login_user(db, body.email.strip().lower(), body.password, user_agent=user_agent, ip_address=client_host)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    db.commit()
    return AuthResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type="bearer",
        user=UserRead(**result["user"]),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    result = refresh_access_token(db, body.refresh_token)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    db.commit()
    return TokenResponse(**result)


@router.post("/logout", response_model=dict)
def logout(
    body: Optional[RefreshRequest] = None,
    authorization: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    if body and body.refresh_token:
        logout_user(db, body.refresh_token)
        db.commit()
    return {"ok": True, "message": "Logged out successfully"}


@router.get("/me", response_model=MeResponse)
def me(
    current_user: User = Depends(get_current_user),
):
    return MeResponse(
        user=UserRead(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role,
            status=current_user.status,
            email_verified=current_user.email_verified,
            auth_provider=current_user.auth_provider,
            onboarding_completed=current_user.onboarding_completed,
        )
    )


@router.post("/verify-email", response_model=dict)
def verify_email(
    body: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    user = verify_email_token(db, body.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    db.commit()
    return {"message": "Email verified successfully", "email": user.email}


@router.post("/resend-verification", response_model=dict)
def resend_verification(
    body: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    email = body.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"message": "If the email is registered, a new verification link has been sent."}
    if user.email_verified:
        return {"message": "Email is already verified."}

    ver_token = create_email_verification_token(db, user.id)
    db.commit()
    try:
        send_verification_email(user.email, ver_token)
    except Exception:
        logger.warning("Failed to resend verification email to %s", user.email)
    return {"message": "If the email is registered, a new verification link has been sent."}


@router.post("/forgot-password", response_model=dict)
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    email = body.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.info("forgot_password_unknown: email=%s", email)
        return {"message": "If the email is registered, a password reset link has been sent."}

    reset_token = create_password_reset_token(db, user.id)
    db.commit()
    try:
        send_password_reset_email(user.email, reset_token)
    except Exception:
        logger.warning("Failed to send password reset email to %s", user.email)
    return {"message": "If the email is registered, a password reset link has been sent."}


@router.post("/reset-password", response_model=dict)
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    pw_err = validate_password_strength(body.new_password)
    if pw_err:
        raise HTTPException(status_code=400, detail=pw_err)

    user = reset_password_with_token(db, body.token, body.new_password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    db.commit()
    return {"message": "Password has been reset successfully"}


@router.post("/change-password", response_model=dict)
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pw_err = validate_password_strength(body.new_password)
    if pw_err:
        raise HTTPException(status_code=400, detail=pw_err)
    if not change_user_password(db, current_user.id, body.current_password, body.new_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    db.commit()
    return {"message": "Password changed successfully"}


# ── Google OAuth ────────────────────────────────────────────────────


@router.get("/google/start")
def google_start():
    if not google_login_configured():
        return GoogleAuthUrlResponse(url="", configured=False)
    url = get_google_authorization_url()
    if not url:
        return GoogleAuthUrlResponse(url="", configured=False)
    return GoogleAuthUrlResponse(url=url, configured=True)


@router.get("/google/callback", response_model=AuthResponse)
def google_callback(
    code: str = "",
    state: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    if error:
        raise HTTPException(status_code=400, detail=f"Google login failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    if not google_login_configured():
        raise HTTPException(status_code=400, detail="Google login not configured")

    saved_state = os.environ.get("_GOOGLE_OAUTH_STATE", "")
    if state and saved_state and state != saved_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    token_result = google_exchange_code(code)
    if not token_result:
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

    id_token = token_result.get("id_token", "")
    if not id_token:
        raise HTTPException(status_code=400, detail="No ID token in response")

    payload = verify_google_id_token(id_token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid Google ID token")

    result = login_or_register_google_user(db, payload)
    if not result:
        raise HTTPException(status_code=400, detail="Google login failed")
    db.commit()
    return AuthResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type="bearer",
        user=UserRead(**result["user"]),
    )
