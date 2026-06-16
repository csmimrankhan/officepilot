"""Phase 17 — Authentication service (password hash, JWT, register, login)."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.user import User

logger = logging.getLogger("officepilot.auth")

# ── Password hashing ────────────────────────────────────────────────
# Use hashlib.pbkdf2_hmac (no external bcrypt dependency needed)
# with a random salt for each password.

_HASH_ALGO = "sha256"
_HASH_ITERATIONS = 600000
_HASH_DKLEN = 32
_SALT_BYTES = 16


def _random_salt() -> bytes:
    return secrets.token_bytes(_SALT_BYTES)


def hash_password(password: str) -> str:
    salt = _random_salt()
    dk = hashlib.pbkdf2_hmac(_HASH_ALGO, password.encode("utf-8"), salt, _HASH_ITERATIONS, dklen=_HASH_DKLEN)
    return f"$pbkdf2${_HASH_ALGO}${_HASH_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        parts = password_hash.split("$")
        if len(parts) != 6 or parts[0] != "" or parts[1] != "pbkdf2":
            return False
        algo = parts[2]
        iterations = int(parts[3])
        salt = bytes.fromhex(parts[4])
        expected = bytes.fromhex(parts[5])
        dk = hashlib.pbkdf2_hmac(algo, password.encode("utf-8"), salt, iterations, dklen=len(expected))
        return hmac.compare_digest(dk, expected)
    except (ValueError, IndexError):
        return False


# ── JWT ─────────────────────────────────────────────────────────────


def _get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", getattr(get_settings(), "jwt_secret", ""))
    if not secret:
        secret = secrets.token_hex(32)
        os.environ["JWT_SECRET"] = secret
    return secret


def create_access_token(user_id: int, email: str, role: str) -> str:
    secret = _get_jwt_secret()
    expiry_minutes = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "iat": int(time.time()),
        "exp": int(time.time() + expiry_minutes * 60),
    }
    return _encode_jwt(payload, secret)


def create_refresh_token(user_id: int) -> str:
    secret = _get_jwt_secret()
    expiry_days = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": int(time.time()),
        "exp": int(time.time() + expiry_days * 86400),
    }
    return _encode_jwt(payload, secret)


def _encode_jwt(payload: dict, secret: str) -> str:
    import json as _json
    import base64 as _b64

    header = _b64.urlsafe_b64encode(_json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = _b64.urlsafe_b64encode(_json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=").decode()
    sig = hmac.new(secret.encode(), f"{header}.{body}".encode(), "sha256").digest()
    sig_b64 = _b64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{header}.{body}.{sig_b64}"


def decode_token(token: str) -> Optional[dict]:
    import base64 as _b64
    import json as _json

    secret = _get_jwt_secret()
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, body_b64, sig_b64 = parts

        expected_sig = hmac.new(secret.encode(), f"{header_b64}.{body_b64}".encode(), "sha256").digest()
        actual_sig = _b64.urlsafe_b64decode(sig_b64 + "==")
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        padded = body_b64 + "=" * (4 - len(body_b64) % 4)
        payload = _json.loads(_b64.urlsafe_b64decode(padded))

        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


# ── User registration / login / bootstrap ──────────────────────────


def get_user_count(db: Session) -> int:
    return db.query(User).count()


def register_user(db: Session, email: str, password: str, full_name: str = "") -> User:
    user_count = get_user_count(db)
    allow_open = os.environ.get("ALLOW_OPEN_REGISTRATION", "false").lower() in ("1", "true", "yes", "on")
    allow_bootstrap = os.environ.get("ALLOW_FIRST_OWNER_BOOTSTRAP", "true").lower() in ("1", "true", "yes", "on")

    if user_count > 0 and not allow_open:
        raise ValueError("Registration is closed. Contact an administrator.")

    role = "owner" if user_count == 0 and allow_bootstrap else "staff"

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ValueError("A user with this email already exists")

    pw_hash = hash_password(password)
    now = datetime.utcnow()
    user = User(
        email=email,
        password_hash=pw_hash,
        full_name=full_name or email.split("@")[0],
        role=role,
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.flush()
    logger.info("User registered: email=%s role=%s (total users=%d)", email, role, user_count + 1)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if user.status != "active":
        return None
    if not verify_password(password, user.password_hash):
        return None
    user.last_login_at = datetime.utcnow()
    db.flush()
    return user


def login_user(db: Session, email: str, password: str) -> Optional[dict]:
    user = authenticate_user(db, email, password)
    if user is None:
        return None
    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token(user.id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


def refresh_access_token(db: Session, refresh_token_str: str) -> Optional[dict]:
    payload = decode_token(refresh_token_str)
    if payload is None:
        return None
    if payload.get("type") != "refresh":
        return None
    user_id = int(payload["sub"])
    user = db.get(User, user_id)
    if user is None or user.status != "active":
        return None
    access_token = create_access_token(user.id, user.email, user.role)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
