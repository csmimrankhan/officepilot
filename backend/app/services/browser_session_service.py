"""Phase 32 — browser session service for export automation.

Manages per-user/run browser sessions with safety controls.
Connects to the real Playwright adapter when BROWSER_AUTOMATION_MODE=playwright
and BROWSER_AUTOMATION_ALLOW_LIVE=true.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from ..config import get_settings
from ..models.browser_session import BrowserSession, SESSION_STATUSES
from .browser_automation import get_adapter, reset_adapter

logger = logging.getLogger(__name__)

# ── Blocked action keywords ──────────────────────────────────────────────

BLOCKED_ACTION_KEYWORDS = [
    "pay", "payment", "transfer", "bank transfer",
    "delete", "remove", "erase", "destroy",
    "payroll", "salary", "wage submission",
    "tax filing", "file tax", "submit tax",
    "approve payment", "authorize payment",
    "submit final", "final submit", "irreversible",
]

SENSITIVE_FIELD_PATTERNS = (
    "password", "passwd", "pwd",
    "token", "secret", "api_key", "apikey", "api-key",
    "otp", "2fa", "mfa", "verification code",
    "cvv", "cvc", "ssn", "sin", "pin",
    "card number", "credit card", "debit card",
    "security code", "security answer",
)

SAFE_EXPORT_EXTENSIONS = {".xlsx", ".xls", ".csv", ".pdf", ".txt", ".tsv"}


# ── Safety helpers ────────────────────────────────────────────────────────


def is_action_blocked(action_text: str) -> tuple[bool, str]:
    """Check if action contains blocked keywords. Returns (blocked, reason)."""
    text = action_text.lower()
    for kw in BLOCKED_ACTION_KEYWORDS:
        if kw in text:
            return True, f"Action contains blocked keyword: '{kw}'"
    return False, ""


def is_sensitive_field(label: str) -> bool:
    """Check if a field label looks sensitive (password, OTP, etc.)."""
    text = label.lower().replace("_", " ").replace("-", " ")
    for pat in SENSITIVE_FIELD_PATTERNS:
        if pat in text:
            return True
    return False


def input_is_sensitive(input_text: str) -> bool:
    """Check if input text looks like a password/token/secret."""
    lowered = input_text.lower()
    for pat in SENSITIVE_FIELD_PATTERNS:
        if pat in lowered and len(input_text) <= 128:
            return True
    return False


# ── Browser mode check ────────────────────────────────────────────────────


def _browser_can_run_live() -> tuple[bool, str]:
    """Check if browser automation can run live."""
    s = get_settings()
    if s.browser_automation_mode != "playwright":
        return False, f"browser_automation_mode={s.browser_automation_mode} (need 'playwright')"
    if not s.browser_automation_allow_live:
        return False, "browser_automation_allow_live is false (set BROWSER_AUTOMATION_ALLOW_LIVE=true)"
    return True, ""


# ── Session CRUD ──────────────────────────────────────────────────────────


def create_session(
    db: DBSession,
    user_id: str,
    target_url: str = "",
    run_id: Optional[int] = None,
    guided_mode: bool = False,
) -> BrowserSession:
    """Create a new browser session."""
    s = get_settings()
    download_dir = s.browser_download_watch_dir or str(Path.home() / "Downloads")
    output_dir = str(s.data_dir / "browser_exports" / datetime.utcnow().strftime("%Y_%m_%d"))
    session = BrowserSession(
        user_id=user_id,
        run_id=run_id,
        status="active",
        target_url=target_url,
        download_dir=download_dir,
        output_dir=output_dir,
        guided_mode=1 if guided_mode else 0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("Created browser session %d for user %s", session.id, user_id)
    return session


def get_session(db: DBSession, session_id: int, user_id: str) -> Optional[BrowserSession]:
    """Get a browser session by id, scoped to user."""
    return db.query(BrowserSession).filter(
        BrowserSession.id == session_id,
        BrowserSession.user_id == user_id,
    ).first()


def get_active_session(db: DBSession, user_id: str) -> Optional[BrowserSession]:
    """Get the active session for a user (if any)."""
    return db.query(BrowserSession).filter(
        BrowserSession.user_id == user_id,
        BrowserSession.status.in_(["active", "waiting_login", "logged_in", "navigating", "exporting"]),
    ).order_by(BrowserSession.created_at.desc()).first()


def get_session_by_run(db: DBSession, run_id: int, user_id: str) -> Optional[BrowserSession]:
    """Get a browser session by workflow run id."""
    return db.query(BrowserSession).filter(
        BrowserSession.run_id == run_id,
        BrowserSession.user_id == user_id,
    ).first()


def update_session_status(db: DBSession, session: BrowserSession, status: str) -> None:
    """Update session status."""
    if status in SESSION_STATUSES:
        session.status = status
        session.updated_at = datetime.utcnow()
        if status in ("completed", "stopped", "error"):
            session.closed_at = datetime.utcnow()
        db.commit()


def update_session_url(db: DBSession, session: BrowserSession, url: str, title: str = "") -> None:
    """Update current URL and title."""
    session.current_url = url
    if title:
        session.current_title = title
    session.updated_at = datetime.utcnow()
    db.commit()


def update_session_screenshot(db: DBSession, session: BrowserSession, screenshot_path: str) -> None:
    """Update screenshot path."""
    session.screenshot_path = screenshot_path
    session.updated_at = datetime.utcnow()
    db.commit()


def update_session_downloaded(db: DBSession, session: BrowserSession, file_path: str) -> None:
    """Record downloaded file path."""
    session.downloaded_file_path = file_path
    session.updated_at = datetime.utcnow()
    db.commit()


def close_session(db: DBSession, session: BrowserSession) -> None:
    """Close a browser session."""
    session.status = "stopped"
    session.closed_at = datetime.utcnow()
    session.updated_at = datetime.utcnow()
    db.commit()
    logger.info("Closed browser session %d", session.id)


# ── Live adapter interaction ──────────────────────────────────────────────


def open_url_live(db: DBSession, session: BrowserSession, url: str) -> dict:
    """Open URL using real Playwright adapter (only if mode=playwright and live allowed)."""
    can_run, reason = _browser_can_run_live()
    if not can_run:
        return {"ok": False, "error": reason, "mode": "mock"}

    try:
        adapter = get_adapter()
        result = adapter.open_url(url)
        if not result.ok:
            return {"ok": False, "error": result.error}

        payload = result.payload or {}
        title = payload.get("title", "")
        update_session_url(db, session, url, title)
        update_session_status(db, session, "waiting_login")
        return {"ok": True, "title": title, "mode": "playwright", "url": url}
    except Exception as e:
        logger.exception("Failed to open URL live: %s", url)
        update_session_status(db, session, "error")
        return {"ok": False, "error": str(e)}


def take_screenshot_live(db: DBSession, session: BrowserSession, step_name: str = "browser") -> dict:
    """Take a screenshot using the real adapter."""
    try:
        adapter = get_adapter()
        result = adapter.screenshot(session.id, step_name)
        if result.ok and result.screenshot_path:
            update_session_screenshot(db, session, result.screenshot_path)
            return {"ok": True, "screenshot_path": result.screenshot_path}
        return {"ok": result.ok, "error": result.error, "screenshot_path": result.screenshot_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def read_page_live() -> dict:
    """Read current page text from the real adapter."""
    try:
        adapter = get_adapter()
        if adapter.is_live() and adapter._page is not None:
            from playwright.sync_api import TimeoutError
            try:
                title = adapter._page.title() or ""
                text = (adapter._page.inner_text("body") or "")[:5000]
                url = adapter._page.url or ""
                return {"ok": True, "title": title, "text": text, "url": url}
            except TimeoutError:
                return {"ok": False, "error": "Page load timeout"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "Not in live mode", "mode": "mock"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Guided download watcher ──────────────────────────────────────────────


def watch_for_download(
    db: DBSession,
    session: BrowserSession,
    timeout_seconds: int = 120,
    poll_interval: float = 1.0,
) -> dict:
    """Watch the download directory for a new file. Returns detected file path."""
    download_dir = Path(session.download_dir)
    if not download_dir.exists():
        return {"ok": False, "error": f"Download directory does not exist: {download_dir}"}

    known_files = {str(f) for f in download_dir.iterdir() if f.is_file()}
    deadline = time.time() + timeout_seconds

    logger.info("Watching %s for new downloads (timeout=%ds)", download_dir, timeout_seconds)

    while time.time() < deadline:
        current_files = {str(f) for f in download_dir.iterdir() if f.is_file()}
        new_files = current_files - known_files

        for f_path_str in new_files:
            f_path = Path(f_path_str)
            ext = f_path.suffix.lower()
            if ext in SAFE_EXPORT_EXTENSIONS:
                # Wait a moment for the file to finish writing
                try:
                    initial_size = f_path.stat().st_size
                    time.sleep(0.5)
                    if f_path.stat().st_size == initial_size:
                        logger.info("Detected new downloaded file: %s", f_path)
                        return {"ok": True, "file_path": str(f_path), "filename": f_path.name, "extension": ext}
                except OSError:
                    continue

        time.sleep(poll_interval)

    return {"ok": False, "error": f"No new file detected after {timeout_seconds}s"}


def copy_to_output(session: BrowserSession, file_path: str) -> dict:
    """Copy downloaded file to output directory. Original file is not modified."""
    try:
        src = Path(file_path)
        if not src.exists():
            return {"ok": False, "error": f"Source file not found: {file_path}"}

        output_dir = Path(session.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%H%M%S")
        dest = output_dir / f"{src.stem}_{timestamp}{src.suffix}"

        # Copy, never move — original stays in Downloads
        shutil.copy2(str(src), str(dest))
        logger.info("Copied %s -> %s", src, dest)
        return {"ok": True, "output_path": str(dest), "filename": dest.name}
    except Exception as e:
        logger.exception("Failed to copy downloaded file")
        return {"ok": False, "error": str(e)}


# ── Mock responses ────────────────────────────────────────────────────────


def mock_open_url(url: str) -> dict:
    """Return a mock response for browser_open_url."""
    return {
        "ok": True,
        "url": url,
        "title": f"(mock) {url}",
        "requires_user_login": True,
        "mode": "mock",
    }


def mock_wait_for_login(prompt: str = "") -> dict:
    """Return a mock response for wait_for_user_login."""
    return {
        "ok": True,
        "action": "wait_for_login",
        "status": "waiting",
        "prompt": prompt or "Please log in manually",
        "mode": "mock",
    }


def mock_read_page() -> dict:
    """Return mock page content."""
    return {
        "ok": True,
        "title": "Mock Page (dry-run)",
        "text": "[mock] Browser page content — this is a simulated response.",
        "mode": "mock",
    }


def mock_export_report(report_type: str = "report") -> dict:
    """Return a mock export response."""
    from datetime import date
    return {
        "ok": True,
        "filepath": f"exports/{report_type}_{date.today().isoformat()}.csv",
        "report_type": report_type,
        "exported": True,
        "mode": "mock",
    }


def mock_wait_for_download() -> dict:
    """Return a mock download response."""
    return {
        "ok": True,
        "found": True,
        "filepath": "downloads/mock_report.csv",
        "mode": "mock",
    }
