"""OAuth 2.0 flow helpers for Gmail (Phase 2).

Scope is strictly ``gmail.readonly``. The flow is a server-side flow that:

1. ``build_flow()``  — builds a google_auth_oauthlib Flow.
2. ``authorization_url(state)``  — returns the URL the browser should visit.
3. ``exchange_code(code, state)``  — exchanges the callback code for credentials.
4. ``credentials_to_dict()``  / ``dict_to_credentials()`` — serialize for storage.

We never ask for write/modify scopes and we never mark messages as read.
"""

from __future__ import annotations

import json
import logging
import secrets
from typing import Optional

from ...config import Settings
from .gmail_client import GMAIL_SCOPES, GmailClientError

logger = logging.getLogger(__name__)


class OAuthConfigError(Exception):
    pass


def _settings_or_raise(settings: Settings):
    if not settings.gmail_configured:
        raise OAuthConfigError(
            "Gmail OAuth is not configured. Set OFFICEPILOT_GMAIL_CLIENT_ID and "
            "OFFICEPILOT_GMAIL_CLIENT_SECRET (and optionally the redirect URI) "
            "in your environment or .env file."
        )
    return settings


def build_flow(settings: Settings, state: str):
    """Build a Flow configured for offline access and the readonly scope."""
    s = _settings_or_raise(settings)
    try:
        from google_auth_oauthlib.flow import Flow  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise GmailClientError(
            "google-auth-oauthlib is required for the OAuth flow"
        ) from exc
    client_config = {
        "web": {
            "client_id": s.gmail_client_id,
            "client_secret": s.gmail_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [s.gmail_redirect_uri],
        }
    }
    flow = Flow.from_client_config(
        client_config, scopes=GMAIL_SCOPES, state=state, redirect_uri=s.gmail_redirect_uri
    )
    return flow


def authorization_url(settings: Settings, state: str) -> str:
    flow = build_flow(settings, state)
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url


def exchange_code(settings: Settings, code: str, state: str):
    flow = build_flow(settings, state)
    flow.fetch_token(code=code)
    return flow.credentials


def credentials_to_dict(creds) -> dict:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or []),
        "expiry": creds.expiry.isoformat() if getattr(creds, "expiry", None) else None,
    }


def dict_to_credentials(data: dict):
    try:
        from google.oauth2.credentials import Credentials  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise GmailClientError(
            "google-auth is required to reconstruct OAuth credentials"
        ) from exc
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes") or [],
    )
    expiry = data.get("expiry")
    if expiry:
        try:
            from datetime import datetime
            creds.expiry = datetime.fromisoformat(expiry)
        except Exception:
            creds.expiry = None
    return creds


def new_state() -> str:
    return secrets.token_urlsafe(24)


# ----- State persistence (connect <-> callback) -----

# The state token is short-lived and stored server-side under
# OFFICEPILOT_GMAIL_STATE_DIR/state/<state>.json so a refresh of the browser
# after the Google consent screen still finds it.

def _state_path(settings: Settings, state: str):
    s = _settings_or_raise(settings)
    folder = s.gmail_state_dir / "state"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{state}.json"


def remember_state(settings: Settings, state: str, *, payload: Optional[dict] = None) -> None:
    p = _state_path(settings, state)
    p.write_text(json.dumps({"payload": payload or {}}), encoding="utf-8")


def pop_state(settings: Settings, state: str) -> dict:
    p = _state_path(settings, state)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8") or "{}")
    except Exception:
        data = {}
    try:
        p.unlink()
    except Exception:
        pass
    return data.get("payload") or {}
