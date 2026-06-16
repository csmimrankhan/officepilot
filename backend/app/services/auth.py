"""OfficePilot Auth 2.0 — password hashing, JWT, sessions, OAuth, user management."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.email_token import EmailVerificationToken, PasswordResetToken
from ..models.oauth_account import OAuthAccount
from ..models.user import User
from ..models.user_session import UserSession

logger = logging.getLogger("officepilot.auth")

_HASH_ALGO = "sha256"
_HASH_ITERATIONS = 600000
_HASH_DKLEN = 32
_SALT_BYTES = 16
_SESSION_EXPIRE_DAYS = 30

RESET_TOKEN_EXPIRE_HOURS = 1
VERIFICATION_TOKEN_EXPIRE_HOURS = 24

# ── Password hashing ────────────────────────────────────────────────


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


# ── Token helpers ────────────────────────────────────────────────────


def _generate_secure_token() -> str:
    return secrets.token_urlsafe(48)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ── JWT ─────────────────────────────────────────────────────────────


def _get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", getattr(get_settings(), "jwt_secret", ""))
    if not secret:
        secret = secrets.token_hex(32)
        os.environ["JWT_SECRET"] = secret
    return secret


def _encode_jwt(payload: dict, secret: str) -> str:
    import base64 as _b64

    header = _b64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = _b64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=").decode()
    sig = hmac.new(secret.encode(), f"{header}.{body}".encode(), "sha256").digest()
    sig_b64 = _b64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{header}.{body}.{sig_b64}"


def decode_token(token: str) -> Optional[dict]:
    import base64 as _b64

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
        payload = json.loads(_b64.urlsafe_b64decode(padded))

        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


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


# ── Session management ──────────────────────────────────────────────


def create_session(db: Session, user_id: int, refresh_token: str, user_agent: str = "", ip_address: str = "") -> UserSession:
    token_hash = _hash_token(refresh_token)
    now = datetime.utcnow()
    session = UserSession(
        user_id=user_id,
        refresh_token_hash=token_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        created_at=now,
        expires_at=now + timedelta(days=_SESSION_EXPIRE_DAYS),
        last_seen_at=now,
    )
    db.add(session)
    db.flush()
    return session


def revoke_session_by_token(db: Session, refresh_token: str) -> None:
    token_hash = _hash_token(refresh_token)
    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == token_hash,
        UserSession.revoked_at.is_(None),
    ).first()
    if session:
        session.revoked_at = datetime.utcnow()
        db.flush()


def revoke_all_user_sessions(db: Session, user_id: int) -> int:
    count = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.revoked_at.is_(None),
    ).update({"revoked_at": datetime.utcnow()})
    db.flush()
    return count


def validate_session(db: Session, refresh_token: str) -> Optional[UserSession]:
    token_hash = _hash_token(refresh_token)
    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == token_hash,
        UserSession.revoked_at.is_(None),
    ).first()
    if not session:
        return None
    if datetime.utcnow() > session.expires_at:
        return None
    return session


# ── Password validation ──────────────────────────────────────────────


def validate_password_strength(password: str) -> Optional[str]:
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number"
    if not any(not c.isalnum() for c in password):
        return "Password must contain at least one special character"
    return None


# ── Email verification ──────────────────────────────────────────────


def create_email_verification_token(db: Session, user_id: int) -> str:
    token = _generate_secure_token()
    token_hash = _hash_token(token)
    expires = datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)

    record = EmailVerificationToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires,
    )
    db.add(record)
    db.flush()
    return token


def verify_email_token(db: Session, token: str) -> Optional[User]:
    token_hash = _hash_token(token)
    record = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token_hash == token_hash,
        EmailVerificationToken.used_at.is_(None),
    ).first()
    if not record:
        return None
    if datetime.utcnow() > record.expires_at:
        return None
    user = db.get(User, record.user_id)
    if not user:
        return None
    user.email_verified = True
    record.used_at = datetime.utcnow()
    db.flush()
    return user


# ── Password reset ──────────────────────────────────────────────────


def create_password_reset_token(db: Session, user_id: int) -> str:
    token = _generate_secure_token()
    token_hash = _hash_token(token)
    expires = datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)

    record = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires,
    )
    db.add(record)
    db.flush()
    return token


def reset_password_with_token(db: Session, token: str, new_password: str) -> Optional[User]:
    token_hash = _hash_token(token)
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used_at.is_(None),
    ).first()
    if not record:
        return None
    if datetime.utcnow() > record.expires_at:
        return None
    user = db.get(User, record.user_id)
    if not user or user.status != "active":
        return None
    user.password_hash = hash_password(new_password)
    record.used_at = datetime.utcnow()
    db.flush()
    return user


# ── User registration / login / bootstrap ──────────────────────────


def get_user_count(db: Session) -> int:
    return db.query(User).count()


def register_user(db: Session, email: str, password: str, full_name: str = "") -> User:
    user_count = get_user_count(db)
    allow_open = os.environ.get("ALLOW_OPEN_REGISTRATION", "false").lower() in ("1", "true", "yes", "on")
    allow_bootstrap = os.environ.get("ALLOW_FIRST_OWNER_BOOTSTRAP", "true").lower() in ("1", "true", "yes", "on")

    if user_count > 0 and not allow_open:
        raise ValueError("Registration is closed. Contact an administrator.")

    role = "owner" if user_count == 0 and allow_bootstrap else "user"

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ValueError("A user with this email already exists")

    if not full_name or not full_name.strip():
        raise ValueError("Full name is required")

    if len(full_name.strip()) > 255:
        raise ValueError("Full name must be 255 characters or less")

    pw_hash = hash_password(password)
    now = datetime.utcnow()
    user = User(
        email=email,
        password_hash=pw_hash,
        full_name=full_name.strip(),
        role=role,
        status="active",
        auth_provider="email",
        created_at=now,
        updated_at=now,
        email_verified=False,
        is_active=True,
        failed_login_count=0,
        login_count=0,
    )
    db.add(user)
    db.flush()
    logger.info("User registered: email=%s role=%s (total users=%d)", email, role, user_count + 1)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if user.status not in ("active",):
        logger.warning("login_blocked_status: email=%s status=%s", email, user.status)
        return None
    if not user.is_active:
        return None
    if user.deleted_at is not None:
        return None
    if user.password_hash is None:
        return None
    if user.locked_until and datetime.utcnow() < user.locked_until:
        logger.warning("login_blocked_locked: email=%s locked_until=%s", email, user.locked_until)
        return None
    if not verify_password(password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.flush()
        return None
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    user.last_active_at = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    db.flush()
    return user


def login_user(db: Session, email: str, password: str, user_agent: str = "", ip_address: str = "") -> Optional[dict]:
    user = authenticate_user(db, email, password)
    if user is None:
        return None
    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token(user.id)
    create_session(db, user.id, refresh_token, user_agent, ip_address)
    db.flush()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "email_verified": user.email_verified,
            "status": user.status,
            "auth_provider": user.auth_provider,
            "onboarding_completed": user.onboarding_completed,
        },
    }


def refresh_access_token(db: Session, refresh_token_str: str) -> Optional[dict]:
    session = validate_session(db, refresh_token_str)
    if not session:
        return None
    user = db.get(User, session.user_id)
    if user is None or user.status != "active" or not user.is_active or user.deleted_at is not None:
        return None
    access_token = create_access_token(user.id, user.email, user.role)
    session.last_seen_at = datetime.utcnow()
    db.flush()
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


def logout_user(db: Session, refresh_token: str) -> None:
    revoke_session_by_token(db, refresh_token)
    db.flush()


def change_user_password(db: Session, user_id: int, current_password: str, new_password: str) -> bool:
    user = db.get(User, user_id)
    if not user:
        return False
    if user.password_hash is None:
        return False
    if not verify_password(current_password, user.password_hash):
        return False
    user.password_hash = hash_password(new_password)
    db.flush()
    return True


# ── Google OAuth ────────────────────────────────────────────────────


def google_login_configured() -> bool:
    settings = get_settings()
    return bool(settings.google_client_id and settings.google_client_secret)


def get_google_authorization_url() -> Optional[str]:
    if not google_login_configured():
        return None
    settings = get_settings()
    state = _generate_secure_token()
    nonce = _generate_secure_token()
    os.environ["_GOOGLE_OAUTH_STATE"] = state
    os.environ["_GOOGLE_OAUTH_NONCE"] = nonce
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri or os.environ.get("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/google/callback"),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
    }
    import urllib.parse
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


def verify_google_id_token(id_token: str) -> Optional[dict]:
    """Verify a Google ID token and return the payload."""
    import base64 as _b64

    try:
        parts = id_token.split(".")
        if len(parts) != 3:
            return None
        padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(_b64.urlsafe_b64decode(padded))
        settings = get_settings()

        if payload.get("aud") != settings.google_client_id:
            logger.warning("google_token_aud_mismatch: expected=%s got=%s", settings.google_client_id, payload.get("aud"))
            return None
        if payload.get("iss") not in ("https://accounts.google.com", "accounts.google.com"):
            logger.warning("google_token_iss_mismatch: issuer=%s", payload.get("iss"))
            return None
        exp = payload.get("exp", 0)
        if time.time() > exp:
            logger.warning("google_token_expired")
            return None

        return payload
    except Exception as e:
        logger.warning("google_token_verify_failed: %s", e)
        return None


def google_exchange_code(code: str) -> Optional[dict]:
    """Exchange authorization code for tokens using Google's token endpoint."""
    settings = get_settings()
    import urllib.request

    redirect_uri = settings.google_redirect_uri or os.environ.get("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/api/auth/google/callback")
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result
    except Exception as e:
        logger.warning("google_token_exchange_failed: %s", e)
        return None


def login_or_register_google_user(db: Session, token_payload: dict) -> Optional[dict]:
    """Create or link a local user from verified Google ID token payload."""
    google_sub = token_payload.get("sub", "")
    email = (token_payload.get("email", "") or "").lower()
    email_verified = token_payload.get("email_verified", False)
    name = token_payload.get("name", "") or ""
    picture = token_payload.get("picture", "") or ""

    if not email:
        logger.warning("google_no_email_in_token")
        return None

    oauth_account = db.query(OAuthAccount).filter(
        OAuthAccount.provider == "google",
        OAuthAccount.provider_user_id == google_sub,
    ).first()

    if oauth_account:
        user = db.get(User, oauth_account.user_id)
        if user and user.status == "active" and not user.deleted_at:
            user.last_login_at = datetime.utcnow()
            user.last_active_at = datetime.utcnow()
            user.login_count = (user.login_count or 0) + 1
            oauth_account.display_name = name or oauth_account.display_name
            oauth_account.picture_url = picture or oauth_account.picture_url
            oauth_account.updated_at = datetime.utcnow()
            db.flush()
            access_token = create_access_token(user.id, user.email, user.role)
            refresh_token = create_refresh_token(user.id)
            create_session(db, user.id, refresh_token)
            db.flush()
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "email_verified": user.email_verified,
                    "status": user.status,
                    "auth_provider": "google",
                    "onboarding_completed": user.onboarding_completed,
                },
            }

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        if existing_user.deleted_at is not None:
            return None
        if existing_user.status != "active" or not existing_user.is_active:
            return None
        user = existing_user
        user.auth_provider = "google"
        user.email_verified = user.email_verified or email_verified
    else:
        user_count = get_user_count(db)
        role = "owner" if user_count == 0 and os.environ.get("ALLOW_FIRST_OWNER_BOOTSTRAP", "true").lower() in ("1", "true", "yes", "on") else "user"
        now = datetime.utcnow()
        user = User(
            email=email,
            password_hash=None,
            full_name=name or email.split("@")[0],
            role=role,
            status="active",
            auth_provider="google",
            email_verified=email_verified,
            is_active=True,
            created_at=now,
            updated_at=now,
            login_count=0,
        )
        db.add(user)
        db.flush()

    oauth_record = OAuthAccount(
        user_id=user.id,
        provider="google",
        provider_user_id=google_sub,
        email=email,
        email_verified=email_verified,
        display_name=name,
        picture_url=picture,
    )
    db.add(oauth_record)
    user.last_login_at = datetime.utcnow()
    user.last_active_at = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    db.flush()

    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token(user.id)
    create_session(db, user.id, refresh_token)
    db.flush()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "email_verified": user.email_verified,
            "status": user.status,
            "auth_provider": "google",
            "onboarding_completed": user.onboarding_completed,
        },
    }


# ── Role / Permission helpers ──────────────────────────────────────


ROLE_HIERARCHY = {
    "owner": 4,
    "admin": 3,
    "user": 2,
    "viewer": 1,
}


def require_role(user: User, *allowed_roles: str) -> bool:
    if not allowed_roles:
        return True
    return user.role in allowed_roles


def require_admin(user: User) -> bool:
    return user.role in ("owner", "admin")
