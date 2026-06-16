"""Gmail integration HTTP API (Phase 2).

All endpoints are read-only with respect to the user's mailbox. We never
send, delete, modify, mark-as-read, archive, or label emails.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, selectinload

from ..config import Settings, get_settings
from ..db import get_db
from ..models.email_account import EmailAccount, EmailAccountStatus, EmailProvider
from ..schemas.email import (
    EmailAccountRead,
    GmailStatusRead,
    SyncReportRead,
)
from ..services.audit import log_action
from ..services.email import oauth, sync
from ..services.email.gmail_client import GMAIL_SCOPES, GmailClientError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrations/gmail", tags=["gmail"])


# --------------------------------------------------------------------- helpers


def _get_active_account(db: Session) -> Optional[EmailAccount]:
    return (
        db.query(EmailAccount)
        .filter(EmailAccount.provider == EmailProvider.GMAIL)
        .filter(EmailAccount.status == EmailAccountStatus.CONNECTED)
        .order_by(EmailAccount.id.desc())
        .first()
    )


# --------------------------------------------------------------------- routes


@router.get("/status", response_model=GmailStatusRead)
def gmail_status(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    acct = _get_active_account(db)
    return GmailStatusRead(
        configured=settings.gmail_configured,
        connected=acct is not None,
        account=EmailAccountRead.model_validate(acct) if acct else None,
        scopes=list(GMAIL_SCOPES),
        note=None if settings.gmail_configured else (
            "Gmail OAuth is not configured. Set OFFICEPILOT_GMAIL_CLIENT_ID and "
            "OFFICEPILOT_GMAIL_CLIENT_SECRET to enable real Gmail sync."
        ),
    )


@router.get("/connect", status_code=status.HTTP_200_OK)
def gmail_connect(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: str = Query("user"),
):
    """Begin OAuth. Returns a URL the browser should visit."""
    if not settings.gmail_configured:
        raise HTTPException(
            status_code=409,
            detail=(
                "Gmail OAuth is not configured. Set OFFICEPILOT_GMAIL_CLIENT_ID and "
                "OFFICEPILOT_GMAIL_CLIENT_SECRET, then restart the backend."
            ),
        )
    state = oauth.new_state()
    oauth.remember_state(settings, state, payload={"actor": actor})
    try:
        url = oauth.authorization_url(settings, state)
    except oauth.OAuthConfigError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build auth URL: {exc}") from exc

    log_action(
        db,
        actor=actor,
        action="email.oauth.start",
        entity_type="email_account",
        entity_id=None,
        details="Started Gmail OAuth flow.",
        extra={"state": state[:12] + "…"},
    )
    db.commit()
    return {"authorization_url": url, "state": state}


@router.get("/callback")
def gmail_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Handle Google's redirect. Exchanges the code for credentials, stores
    them encrypted, and redirects the user to the integrations page."""
    if error:
        log_action(
            db,
            actor="system",
            action="email.oauth.error",
            entity_type="email_account",
            entity_id=None,
            details=f"OAuth error from Google: {error}",
        )
        db.commit()
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    payload = oauth.pop_state(settings, state)
    actor = (payload or {}).get("actor", "user")

    try:
        creds = oauth.exchange_code(settings, code, state)
    except Exception as exc:
        log_action(
            db,
            actor=actor,
            action="email.oauth.error",
            entity_type="email_account",
            entity_id=None,
            details=f"Token exchange failed: {exc}",
        )
        db.commit()
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {exc}") from exc

    # The access token may be missing the userinfo claim. To get the user's
    # email we use Google's userinfo endpoint with the access token.
    email = _fetch_user_email(creds.token)
    if not email:
        # Don't fail the connection just because email lookup failed; user can
        # re-connect if needed. But log it.
        log_action(
            db,
            actor=actor,
            action="email.oauth.warning",
            entity_type="email_account",
            entity_id=None,
            details="OAuth succeeded but userinfo lookup did not return an email.",
        )
        email = "unknown@gmail.com"

    creds_dict = oauth.credentials_to_dict(creds)
    acct = sync.get_or_create_account(db, email=email, credentials=creds_dict)

    log_action(
        db,
        actor=actor,
        action="email.oauth.connected",
        entity_type="email_account",
        entity_id=acct.id,
        details=f"Connected Gmail account {email} (readonly).",
        extra={"scopes": creds_dict.get("scopes") or []},
    )
    db.commit()
    # Redirect back to the frontend integrations page.
    origin = (settings.cors_origin_list or ["http://127.0.0.1:5173"])[0]
    return RedirectResponse(url=f"{origin}/integrations?gmail=connected", status_code=302)


@router.post("/sync-invoices", response_model=SyncReportRead)
def gmail_sync_invoices(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    actor: str = Query("user"),
):
    acct = _get_active_account(db)
    if acct is None:
        raise HTTPException(status_code=409, detail="Gmail is not connected.")
    try:
        report = sync.run_sync(
            db, settings, account_id=acct.id, actor=actor
        )
    except GmailClientError as exc:
        # Mark account as errored so the UI can show it.
        acct.status = EmailAccountStatus.ERROR
        acct.last_error = str(exc)[:1000]
        log_action(
            db,
            actor=actor,
            action="email.sync.error",
            entity_type="email_account",
            entity_id=acct.id,
            details=str(exc),
        )
        db.commit()
        raise HTTPException(status_code=502, detail=f"Sync failed: {exc}") from exc
    return SyncReportRead(**report.as_dict())


@router.post("/disconnect", status_code=status.HTTP_200_OK)
def gmail_disconnect(
    db: Session = Depends(get_db),
    actor: str = Query("user"),
):
    acct = _get_active_account(db)
    if acct is None:
        return {"disconnected": False, "reason": "No active Gmail account."}
    ok = sync.disconnect_account(db, acct.id)
    log_action(
        db,
        actor=actor,
        action="email.oauth.disconnected",
        entity_type="email_account",
        entity_id=acct.id,
        details=f"Disconnected Gmail account {acct.email}.",
    )
    db.commit()
    return {"disconnected": ok, "account_id": acct.id}


# --------------------------------------------------------------------- helpers


def _fetch_user_email(access_token: Optional[str]) -> Optional[str]:
    if not access_token:
        return None
    try:
        import requests  # local import keeps the dep optional
    except Exception:
        return None
    try:
        resp = requests.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("email")
    except Exception:
        return None
    return None
