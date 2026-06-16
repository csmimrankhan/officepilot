"""Phase 17 — Authentication endpoints (register, login, logout, refresh, me)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..services.auth import (
    decode_token,
    login_user,
    refresh_access_token,
    register_user,
)

logger = logging.getLogger("officepilot.auth_router")

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Request / Response schemas ──────────────────────────────────────


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str = ""
    role: str = "staff"
    status: str = "active"


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


# ── Dependency to get current user from token ───────────────────────


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
    if user.status != "active":
        raise HTTPException(status_code=401, detail="User account is disabled")

    return user


# ── Endpoints ───────────────────────────────────────────────────────


@router.post("/register", response_model=AuthResponse)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    try:
        user = register_user(
            db=db,
            email=body.email.strip().lower(),
            password=body.password,
            full_name=body.full_name.strip(),
        )
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = login_user(db, body.email.strip().lower(), body.password)
    if result is None:
        raise HTTPException(status_code=500, detail="Registration succeeded but login failed")
    return AuthResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type="bearer",
        user=UserRead(**result["user"]),
    )


@router.post("/login", response_model=AuthResponse)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    result = login_user(db, body.email.strip().lower(), body.password)
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
    return TokenResponse(**result)


@router.post("/logout", response_model=dict)
def logout():
    return {"ok": True, "message": "Logged out (client should discard tokens)"}


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
        )
    )
