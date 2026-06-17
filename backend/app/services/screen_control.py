"""Phase 16A — Screen Control Service.

Provides:
- Real OCR (pytesseract / Windows OCR / fallback)
- Real click/type executor (PyAutoGUI / UI Automation)
- Browser delegation to Phase 12
- Emergency stop hardening (thread-safe flag, step loop enforcement)
- App/window allowlist enforcement with normalization
- Richer action preview
- Result validation

Safety: disabled by default, every write/click/type requires
approval, blocked/unknown apps are blocked.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.audit_log import AuditLog
from ..models.screen_control import (
    DEFAULT_ALLOWED_APPS,
    DEFAULT_BLOCKED_APPS,
    DEFAULT_BLOCKED_DOMAINS,
    ScreenControlAction,
    ScreenControlPolicy,
    ScreenControlSession,
    ScreenControlStepLog,
)

logger = logging.getLogger("officepilot.screen_control")

# ---------------------------------------------------------------------------
# Thread-safe emergency-stop flag
# ---------------------------------------------------------------------------

_emergency_stop_flag: dict[int, threading.Event] = {}
_em_stop_lock = threading.Lock()


def _set_emergency_stop(session_id: int) -> None:
    with _em_stop_lock:
        ev = _emergency_stop_flag.get(session_id)
        if ev is None:
            ev = threading.Event()
            _emergency_stop_flag[session_id] = ev
        ev.set()


def _clear_emergency_stop(session_id: int) -> None:
    with _em_stop_lock:
        ev = _emergency_stop_flag.get(session_id)
        if ev:
            ev.clear()


def _is_emergency_stop(session_id: int) -> bool:
    with _em_stop_lock:
        ev = _emergency_stop_flag.get(session_id)
        return ev is not None and ev.is_set()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SENSITIVE_LABELS = {
    "password", "secret", "token", "api_key", "2fa", "otp",
    "cvv", "ssn", "pin", "credit_card", "bank_account",
}


def _redact_sensitive(text: str) -> str:
    if not text:
        return text
    lower = text.lower()
    if any(label in lower for label in SENSITIVE_LABELS):
        return "[REDACTED]"
    return text


def _safe_str(val: str, default: str = "") -> str:
    return val if val else default


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Policy helpers
# ---------------------------------------------------------------------------


def get_or_create_policy(db: Session) -> ScreenControlPolicy:
    policy = db.query(ScreenControlPolicy).first()
    if policy is None:
        policy = ScreenControlPolicy(
            enabled=False,
            permission_level=0,
            allowed_apps_json=json.dumps(DEFAULT_ALLOWED_APPS),
            blocked_apps_json=json.dumps(DEFAULT_BLOCKED_APPS),
            blocked_domains_json=json.dumps(DEFAULT_BLOCKED_DOMAINS),
        )
        db.add(policy)
        db.flush()
    return policy


def _get_allowed_apps(policy: ScreenControlPolicy) -> list[str]:
    return json.loads(policy.allowed_apps_json or "[]")


def _get_blocked_apps(policy: ScreenControlPolicy) -> list[str]:
    return json.loads(policy.blocked_apps_json or "[]")


def _get_allowed_folders(policy: ScreenControlPolicy) -> list[str]:
    return json.loads(policy.allowed_folders_json or "[]")


def _get_blocked_domains(policy: ScreenControlPolicy) -> list[str]:
    return json.loads(policy.blocked_domains_json or "[]")


# ---------------------------------------------------------------------------
# App name normalization
# ---------------------------------------------------------------------------


def normalize_app_name(name: str) -> str:
    """Normalize an app name for matching.

    - lowercase
    - underscores become spaces (password_manager -> password manager)
    - remove trailing .exe
    """
    n = name.lower().strip()
    n = n.replace("_", " ")
    if n.endswith(".exe"):
        n = n[:-4]
    return n.strip()


# ---------------------------------------------------------------------------
# Permission and blocklist checks
# ---------------------------------------------------------------------------


PERMISSION_LEVEL_DESCRIPTION = {
    0: "Disabled",
    1: "Read-only screen assistance",
    2: "Copy/open only",
    3: "Edit with approval",
    4: "Controlled automation in approved apps only",
    5: "Admin-only full desktop control (not enabled)",
}


def check_permission_level(policy: ScreenControlPolicy, required: int) -> bool:
    return policy.enabled and policy.permission_level >= required


def blocked_app_check(app_name: str, blocked_apps: list[str]) -> bool:
    app_norm = normalize_app_name(app_name)
    for pattern in blocked_apps:
        p_norm = normalize_app_name(pattern)
        if p_norm in app_norm or app_norm in p_norm:
            return True
    return False


def allowed_app_check(app_name: str, allowed_apps: list[str]) -> bool:
    app_norm = normalize_app_name(app_name)
    if not allowed_apps:
        return False
    for pattern in allowed_apps:
        p_norm = normalize_app_name(pattern)
        if p_norm in app_norm or app_norm in p_norm:
            return True
    return False


def blocked_domain_check(domain: str, blocked_domains: list[str]) -> bool:
    domain_lower = domain.lower()
    return any(pattern.lower() in domain_lower for pattern in blocked_domains)


def enforce_app_allowlist(app_name: str, policy: ScreenControlPolicy) -> tuple[bool, str]:
    """Enforce blocked-first, then allowed, then unknown-blocked.

    Returns (allowed, reason).
    """
    settings = get_settings()
    blocked_apps = _get_blocked_apps(policy)
    allowed_apps = _get_allowed_apps(policy)
    block_unknown = settings.screen_block_unknown_apps

    app_norm = normalize_app_name(app_name)

    # 1. Blocked check
    for pattern in blocked_apps:
        p_norm = normalize_app_name(pattern)
        if p_norm in app_norm or app_norm in p_norm:
            return False, f"Application '{app_name}' is blocked"

    # 2. Allowed check
    for pattern in allowed_apps:
        p_norm = normalize_app_name(pattern)
        if p_norm in app_norm or app_norm in p_norm:
            return True, ""

    # 3. Unknown
    if block_unknown:
        return False, f"Application '{app_name}' is not in the allowlist"
    return True, ""


# ---------------------------------------------------------------------------
# Risk classifier
# ---------------------------------------------------------------------------


def classify_screen_risk(action_type: str, app_name: str = "", target: str = "") -> tuple[str, bool, list[str]]:
    """Return (risk_level, requires_approval, reasons)."""
    reasons = []

    high_risk_actions = {
        "click", "type_text", "paste_text", "hotkey",
        "submit_form", "save_file", "delete_file", "send_email",
        "run_browser_action", "run_accounting_action",
    }
    medium_risk_actions = {
        "open_file", "open_folder", "copy_to_clipboard",
        "scroll", "focus_window",
    }

    if action_type in high_risk_actions:
        reasons.append(f"Action type '{action_type}' is high risk")
        return "high", True, reasons

    if action_type in medium_risk_actions:
        reasons.append(f"Action type '{action_type}' is medium risk")
        return "medium", True, reasons

    reasons.append(f"Action type '{action_type}' is low risk")
    return "low", False, reasons


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


def get_capabilities() -> dict:
    """Return available capabilities based on installed dependencies."""
    settings = get_settings()
    ocr_available = _ocr_engine_available()
    cap = {
        "ocr_engine": settings.screen_ocr_engine,
        "ocr_available": ocr_available,
        "click_enabled": settings.screen_click_enabled,
        "type_enabled": settings.screen_type_enabled,
        "clipboard_enabled": settings.screen_clipboard_enabled,
        "ui_automation_enabled": settings.screen_ui_automation_enabled,
        "pyautogui_fallback": settings.screen_pyautogui_fallback,
        "block_unknown_apps": settings.screen_block_unknown_apps,
        "pyautogui_available": _pyautogui_available(),
        "tesseract_installed": ocr_available,
    }
    return cap


def _ocr_engine_available() -> bool:
    """Check if the configured OCR engine is available."""
    settings = get_settings()
    if settings.screen_ocr_engine == "tesseract":
        try:
            import pytesseract
            if settings.screen_tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = settings.screen_tesseract_cmd
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            try:
                r = subprocess.run(
                    ["tesseract", "--version"],
                    capture_output=True, timeout=5,
                )
                return r.returncode == 0
            except Exception:
                return False
    if settings.screen_ocr_engine == "windows_ocr":
        try:
            from windows_ocr import WindowsOcrEngine
            return True
        except ImportError:
            return False
    return False


def _pyautogui_available() -> bool:
    try:
        import pyautogui
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Real OCR implementation
# ---------------------------------------------------------------------------


def extract_visible_text_ocr(screenshot_path: str) -> str:
    """Extract visible text from a screenshot using the configured OCR engine.

    Returns the raw text or a clear error/status string.
    """
    if not screenshot_path or not Path(screenshot_path).exists():
        return ""

    settings = get_settings()

    if settings.screen_ocr_engine == "tesseract":
        return _ocr_tesseract(screenshot_path)
    if settings.screen_ocr_engine == "windows_ocr":
        return _ocr_windows(screenshot_path)
    return ""


def _ocr_tesseract(screenshot_path: str) -> str:
    settings = get_settings()
    try:
        import pytesseract
        if settings.screen_tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.screen_tesseract_cmd
        text = pytesseract.image_to_string(Path(screenshot_path))
        if text.strip():
            return _redact_sensitive(text)
        return "(no text detected)"
    except ImportError:
        return "[OCR engine not installed: pytesseract not available]"
    except Exception as exc:
        logger.debug("Tesseract OCR failed: %s", exc)
        try:
            r = subprocess.run(
                ["tesseract", screenshot_path, "stdout"],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0 and r.stdout.strip():
                return _redact_sensitive(r.stdout)
            return "(no text detected)"
        except FileNotFoundError:
            return "[OCR engine not installed: tesseract binary not found]"
        except Exception as exc2:
            return f"[OCR error: {exc2}]"


def _ocr_windows(screenshot_path: str) -> str:
    try:
        from windows_ocr import WindowsOcrEngine
        engine = WindowsOcrEngine()
        text = engine.recognize(Path(screenshot_path))
        if text.strip():
            return _redact_sensitive(text)
        return "(no text detected)"
    except ImportError:
        return "[OCR engine not installed: windows_ocr package not available]"
    except Exception as exc:
        return f"[Windows OCR error: {exc}]"


# ---------------------------------------------------------------------------
# Screen context service
# ---------------------------------------------------------------------------


def detect_active_window() -> dict:
    """Detect active app and window title via PowerShell."""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                (
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "[System.Windows.Forms.Cursor]::Position | Out-Null; "
                    "try { "
                    "  $h = (Get-Process | Where-Object { $_.MainWindowHandle -ne 0 } "
                    "    | Sort-Object StartTime -Descending | Select-Object -First 1); "
                    "  if ($h) { "
                    "    Write-Output \"$($h.ProcessName)|$($h.MainWindowTitle)\""
                    "  } else { Write-Output 'unknown|' }"
                    "} catch { Write-Output 'unknown|' }"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.strip()
        if "|" in output:
            app, title = output.split("|", 1)
            return {"app": app.strip() or "unknown", "window_title": title.strip()}
    except Exception as exc:
        logger.debug("Active window detection failed: %s", exc)
    return {"app": "unknown", "window_title": ""}


def capture_screenshot(session_id: int) -> str:
    """Capture a screenshot and store it locally."""
    settings = get_settings()
    snap_dir = settings.data_dir / "screen_snapshots" / str(session_id)
    snap_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    path = snap_dir / f"screen_{ts}.png"

    try:
        subprocess.run(
            [
                "powershell",
                "-Command",
                (
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "$bmp = [System.Drawing.Bitmap]::new("
                    "  [System.WindowsForms.Screen]::PrimaryScreen.Bounds.Width, "
                    "  [System.WindowsForms.Screen]::PrimaryScreen.Bounds.Height); "
                    "$gfx = [System.Drawing.Graphics]::FromImage($bmp); "
                    f"$gfx.CopyFromScreen(0,0,0,0,$bmp.Size); "
                    f"$bmp.Save('{path}'); "
                    "$gfx.Dispose(); $bmp.Dispose()"
                ),
            ],
            capture_output=True,
            timeout=10,
        )
        if path.exists():
            return str(path)
    except Exception as exc:
        logger.debug("Screenshot capture failed: %s", exc)
    return ""


def summarize_screen_context(app: str, window_title: str, ocr_text: str = "") -> str:
    parts = [f"Active application: {app}"]
    if window_title:
        parts.append(f"Window: {window_title}")
    if ocr_text:
        lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]
        text_preview = " | ".join(lines[:10])
        if len(text_preview) > 300:
            text_preview = text_preview[:300] + "..."
        parts.append(f"Visible text: {text_preview}")
    return ". ".join(parts)


# ---------------------------------------------------------------------------
# Action planner
# ---------------------------------------------------------------------------


def parse_action_type(source_type: str, source_id: str, request: dict) -> str:
    raw = (request.get("intent") or request.get("action_type") or "").lower()
    intent_map = {
        "what is on my screen": "read_screen",
        "read current window": "read_window",
        "read visible text": "ocr_screen",
        "open invoice folder": "open_folder",
        "open invoice file": "open_file",
        "open this invoice": "open_file",
        "copy vendor and amount": "copy_to_clipboard",
        "copy invoice data": "copy_to_clipboard",
        "fill test form": "paste_to_target",
        "fill this invoice": "paste_to_target",
        "stop automation": "stop",
        "emergency stop": "emergency_stop",
        "show screen logs": "show_logs",
        "open file": "open_file",
        "open folder": "open_folder",
        "click button": "click",
        "type text": "type_text",
        "paste": "paste_text",
        "hotkey": "hotkey",
    }
    for key, val in intent_map.items():
        if key in raw:
            return val
    return "read_screen"


def build_action_preview(
    action_type: str,
    app_name: str,
    window_title: str,
    target: str = "",
    text_to_type: str = "",
) -> dict:
    """Build a richer preview dict for a planned action."""
    risk_level, requires_approval, reasons = classify_screen_risk(action_type, app_name, target)

    settings = get_settings()
    permission_warnings = []
    if action_type in ("click",) and not settings.screen_click_enabled:
        permission_warnings.append("Click actions are disabled in policy")
    if action_type in ("type_text", "paste_text", "hotkey") and not settings.screen_type_enabled:
        permission_warnings.append("Type actions are disabled in policy")
    if action_type in ("copy_to_clipboard", "paste_text") and not settings.screen_clipboard_enabled:
        permission_warnings.append("Clipboard actions are disabled in policy")

    return {
        "action_type": action_type,
        "app_name": app_name,
        "window_title": window_title,
        "target_description": target,
        "risk_level": risk_level,
        "requires_approval": requires_approval,
        "risk_reasons": reasons,
        "permission_warnings": permission_warnings,
        "text_to_type_redacted": _redact_sensitive(text_to_type) if text_to_type else "",
        "expected_result": _expected_result_text(action_type, target),
    }


def _expected_result_text(action_type: str, target: str = "") -> str:
    mapping = {
        "open_file": f"File '{target}' will be opened with default application",
        "open_folder": f"Folder '{target}' will be opened in Explorer",
        "copy_to_clipboard": "Text will be copied to clipboard",
        "click": f"Element '{target}' will be clicked",
        "type_text": "Text will be typed into the active window",
        "paste_text": "Clipboard content will be pasted",
        "hotkey": "Keyboard shortcut will be sent",
        "paste_to_target": "Text will be pasted into the target application",
        "run_browser_action": "Action will be delegated to browser automation",
        "read_screen": "Screen context will be read (no changes made)",
        "read_window": "Window information will be read (no changes made)",
        "ocr_screen": "Visible text will be extracted (no changes made)",
    }
    return mapping.get(action_type, f"Action '{action_type}' will be executed")


# ---------------------------------------------------------------------------
# Real click/type executor
# ---------------------------------------------------------------------------


def _compute_delay_ms() -> float:
    settings = get_settings()
    return settings.screen_execution_step_delay_ms / 1000.0


def _send_hotkey(keys: str) -> dict:
    """Send a keyboard hotkey combo."""
    try:
        import pyautogui
        # Parse "ctrl+c" or "alt+tab" into pyautogui hotkey
        parts = keys.lower().replace(" ", "").split("+")
        pyautogui.hotkey(*parts)
        return {"success": True, "hotkey": keys}
    except ImportError:
        # Fallback: PowerShell
        mapping = {
            "ctrl+c": "^c", "ctrl+v": "^v", "ctrl+x": "^x",
            "ctrl+a": "^a", "ctrl+z": "^z", "ctrl+s": "^s",
            "alt+tab": "%{tab}", "alt+f4": "%{f4}",
            "ctrl+shift+o": "^+o",
        }
        ps_key = mapping.get(keys, keys)
        try:
            subprocess.run(
                ["powershell", "-Command", f"[System.Windows.Forms.SendKeys]::SendWait('{ps_key}')"],
                capture_output=True, timeout=3,
            )
            return {"success": True, "hotkey": keys}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


def _type_text(text: str) -> dict:
    """Type text into the active window."""
    try:
        import pyautogui
        import time
        for char in text:
            if _is_emergency_stop(0):
                return {"success": False, "error": "Emergency stop triggered"}
            pyautogui.write(char)
            time.sleep(0.01)
        return {"success": True, "typed_length": len(text)}
    except ImportError:
        try:
            escaped = text.replace("'", "''").replace("{", "{{").replace("}", "}}")
            subprocess.run(
                ["powershell", "-Command",
                 f"[System.Windows.Forms.SendKeys]::SendWait('{escaped}')"],
                capture_output=True, timeout=30,
            )
            return {"success": True, "typed_length": len(text)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


def _click_approved_target(target_description: str, coordinates: tuple = None) -> dict:
    """Click a target. Uses UI Automation if possible, PyAutoGUI fallback."""
    if coordinates:
        try:
            import pyautogui
            pyautogui.click(coordinates[0], coordinates[1])
            return {"success": True, "clicked": target_description, "coordinates": coordinates}
        except ImportError:
            pass

    # Try UI Automation
    try:
        import uiautomation as auto
        control = auto.ControlFromControl()
        if control:
            # Try finding by name
            found = control.FindControl(searchDepth=1, Name=target_description)
            if found:
                found.Click()
                return {"success": True, "clicked": target_description, "method": "uiautomation"}
    except ImportError:
        pass

    return {"success": False, "error": "Click requires pyautogui or uiautomation package"}


def _wait_step_delay() -> None:
    import time
    time.sleep(_compute_delay_ms())


# ---------------------------------------------------------------------------
# Action executor
# ---------------------------------------------------------------------------


def _execute_open_file(file_path: str) -> dict:
    try:
        p = Path(file_path)
        if not p.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        os.startfile(str(p))
        _wait_step_delay()
        # Result validation: check file existence (it was opened)
        return {"success": True, "opened": str(p), "filename": p.name}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _execute_open_folder(folder_path: str) -> dict:
    try:
        p = Path(folder_path)
        if not p.exists():
            return {"success": False, "error": f"Folder not found: {folder_path}"}
        os.startfile(str(p))
        _wait_step_delay()
        return {"success": True, "opened": str(p), "foldername": p.name}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _execute_copy_to_clipboard(text: str) -> dict:
    try:
        escaped = text.replace("'", "''")
        subprocess.run(
            ["powershell", "-Command", f"Set-Clipboard -Value '{escaped}'"],
            capture_output=True, timeout=5,
        )
        _wait_step_delay()
        # Result validation: read clipboard back
        result = subprocess.run(
            ["powershell", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5,
        )
        clipboard_content = result.stdout.strip() if result.returncode == 0 else ""
        return {
            "success": True,
            "copied_length": len(text),
            "clipboard_verify_length": len(clipboard_content),
            "clipboard_matches": clipboard_content == text,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _execute_paste_to_target(text: str) -> dict:
    """Copy text to clipboard then paste into active window."""
    clip_result = _execute_copy_to_clipboard(text)
    if not clip_result.get("success"):
        return clip_result
    try:
        import pyautogui
        pyautogui.hotkey("ctrl", "v")
        _wait_step_delay()
        return {"success": True, "pasted": True, "clipboard_length": len(text)}
    except ImportError:
        try:
            _send_hotkey("ctrl+v")
            _wait_step_delay()
            return {"success": True, "pasted": True, "clipboard_length": len(text)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


def _delegate_browser_action(
    db: Session,
    action_type: str,
    params: dict,
) -> dict:
    """Delegate a browser-targeted action to Phase 12 browser automation."""
    try:
        from ..services.browser_automation import get_adapter, DomainPolicy, build_browser_preview
        from ..models.browser_automation_policy import BrowserAutomationPolicy

        bpol = db.query(BrowserAutomationPolicy).first()
        if not bpol:
            return {"success": False, "error": "Browser automation policy not found", "delegated": False}

        url = params.get("url", "")
        intent = params.get("intent", "")
        action = params.get("browser_action", "navigate")

        domain_policy = DomainPolicy(
            allowed=bpol.allowed_domains_json or [],
            blocked=bpol.blocked_domains_json or [],
        )
        decision = domain_policy.decide(url)

        if not decision.allowed:
            return {"success": False, "error": decision.reason, "delegated": False, "domain_blocked": True}

        browser_run = {
            "action_type": action,
            "url": url,
            "intent": intent,
        }
        return {
            "success": True,
            "delegated": True,
            "browser_run": browser_run,
            "message": f"Delegated to browser automation for URL: {url}",
        }
    except Exception as exc:
        return {"success": False, "error": f"Browser delegation failed: {exc}", "delegated": False}


def _should_delegate_to_browser(action_type: str, app_name: str) -> bool:
    browser_indicators = [
        "chrome", "firefox", "edge", "brave", "opera",
        "browser", "chromium", "internet explorer", "msedge",
    ]
    app_norm = normalize_app_name(app_name)
    for indicator in browser_indicators:
        if indicator in app_norm:
            return True
    if action_type in ("run_browser_action",):
        return True
    return False


def execute_action(
    action_type: str,
    params: dict,
    db: Session = None,
    session_id: int = 0,
) -> dict:
    """Execute a single screen action with safety checks.

    Returns a dict with ``success`` and action-specific keys.
    """
    settings = get_settings()

    # Check emergency stop before every action
    if _is_emergency_stop(session_id):
        return {"success": False, "error": "Emergency stop triggered before execution"}

    # Permission checks
    if action_type in ("click",) and not settings.screen_click_enabled:
        return {"success": False, "error": "Click actions are disabled in policy"}
    if action_type in ("type_text", "paste_text", "hotkey") and not settings.screen_type_enabled:
        return {"success": False, "error": "Type actions are disabled in policy"}
    if action_type in ("copy_to_clipboard",) and not settings.screen_clipboard_enabled:
        return {"success": False, "error": "Clipboard actions are disabled in policy"}

    # Check emergency stop
    if _is_emergency_stop(session_id):
        return {"success": False, "error": "Emergency stop triggered"}

    # Execute based on action type
    if action_type == "open_file":
        return _execute_open_file(params.get("file_path", ""))
    if action_type == "open_folder":
        return _execute_open_folder(params.get("folder_path", ""))
    if action_type == "copy_to_clipboard":
        return _execute_copy_to_clipboard(params.get("text", ""))
    if action_type == "paste_text":
        return _execute_paste_to_target(params.get("text", ""))
    if action_type == "paste_to_target":
        return _execute_paste_to_target(params.get("text", ""))
    if action_type == "type_text":
        return _type_text(params.get("text", ""))
    if action_type == "hotkey":
        return _send_hotkey(params.get("keys", ""))
    if action_type == "click":
        coords = params.get("coordinates")
        return _click_approved_target(params.get("target", ""), coords)
    if action_type == "run_browser_action":
        if db:
            return _delegate_browser_action(db, action_type, params)
        return {"success": False, "error": "Database required for browser delegation"}

    return {"success": False, "error": f"Unknown action type: {action_type}"}


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


def start_screen_session(db: Session, user_id: str = "user") -> dict:
    policy = get_or_create_policy(db)
    if not policy.enabled:
        raise ValueError("Screen control is disabled")

    ctx = detect_active_window()
    session = ScreenControlSession(
        user_id=user_id,
        status="active",
        permission_level=policy.permission_level,
        active_app=ctx.get("app", "unknown"),
        active_window_title=ctx.get("window_title", ""),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    _clear_emergency_stop(session.id)
    _log_audit(db, "screen.session_start", f"Screen session #{session.id} started", user_id)

    return {
        "session_id": session.id,
        "status": session.status,
        "permission_level": session.permission_level,
    }


def end_screen_session(db: Session, session_id: int, stopped_by: str = "user", reason: str = "") -> dict:
    session = db.get(ScreenControlSession, session_id)
    if session is None:
        raise ValueError("Screen session not found")

    session.status = "ended"
    session.ended_at = datetime.utcnow()
    session.stopped_by = stopped_by
    session.stop_reason = reason
    db.commit()

    _clear_emergency_stop(session_id)
    _log_audit(db, "screen.session_end", f"Screen session #{session_id} ended by {stopped_by}", stopped_by)

    return {"session_id": session.id, "status": session.status}


def emergency_stop_screen(db: Session, session_id: Optional[int] = None, stopped_by: str = "user") -> dict:
    """Emergency stop — sets the in-memory flag, stops session and actions."""
    if session_id:
        _set_emergency_stop(session_id)

        session = db.get(ScreenControlSession, session_id)
        if session and session.status == "active":
            session.status = "stopped"
            session.ended_at = datetime.utcnow()
            session.stopped_by = stopped_by
            session.stop_reason = "Emergency stop"

        running_actions = (
            db.query(ScreenControlAction)
            .filter(
                ScreenControlAction.session_id == session_id,
                ScreenControlAction.status.in_(["planned", "approved", "running"]),
            )
            .all()
        )
        for act in running_actions:
            act.status = "stopped"
            act.stopped_by = stopped_by
            act.stop_reason = "Emergency stop"
            act.error_message = "Emergency stop"

        # Stop all pending/running step logs
        step_logs = (
            db.query(ScreenControlStepLog)
            .join(ScreenControlAction, ScreenControlStepLog.action_id == ScreenControlAction.id)
            .filter(
                ScreenControlAction.session_id == session_id,
                ScreenControlStepLog.status.in_(["pending", "running"]),
            )
            .all()
        )
        for sl in step_logs:
            sl.status = "skipped"
            sl.stopped_by = stopped_by
            sl.stop_reason = "Emergency stop"
    else:
        # Global stop — flag all active sessions
        sessions = (
            db.query(ScreenControlSession)
            .filter(ScreenControlSession.status == "active")
            .all()
        )
        for s in sessions:
            _set_emergency_stop(s.id)
            s.status = "stopped"
            s.ended_at = datetime.utcnow()
            s.stopped_by = stopped_by
            s.stop_reason = "Emergency stop (global)"

        running_actions = (
            db.query(ScreenControlAction)
            .filter(ScreenControlAction.status.in_(["planned", "approved", "running"]))
            .all()
        )
        for act in running_actions:
            act.status = "stopped"
            act.stopped_by = stopped_by
            act.stop_reason = "Emergency stop (global)"
            act.error_message = "Emergency stop (global)"

        step_logs = (
            db.query(ScreenControlStepLog)
            .filter(ScreenControlStepLog.status.in_(["pending", "running"]))
            .all()
        )
        for sl in step_logs:
            sl.status = "skipped"
            sl.stopped_by = stopped_by
            sl.stop_reason = "Emergency stop (global)"

    db.commit()

    _log_audit(db, "screen.emergency_stop", f"Emergency stop by {stopped_by}", stopped_by)

    return {"stopped": True, "session_id": session_id}


# ---------------------------------------------------------------------------
# Action CRUD
# ---------------------------------------------------------------------------


def create_screen_action(
    db: Session,
    session_id: int,
    action_type: str,
    source_type: str = "ui",
    source_id: str = "",
    app_name: str = "",
    window_title: str = "",
    target_description: str = "",
    planned_action: dict = None,
) -> dict:
    text_to_type = (planned_action or {}).get("text", "")
    preview = build_action_preview(action_type, app_name, window_title, target_description, text_to_type)

    action = ScreenControlAction(
        session_id=session_id,
        source_type=source_type,
        source_id=source_id,
        action_type=action_type,
        app_name=app_name,
        window_title=window_title,
        target_description=target_description,
        planned_action_json=planned_action or {},
        risk_level=preview["risk_level"],
        approval_status="pending" if preview["requires_approval"] else "not_required",
        status="planned",
    )
    db.add(action)
    db.commit()
    db.refresh(action)

    _log_audit(
        db, "screen.action_created",
        f"Screen action #{action.id} type={action_type} risk={action.risk_level}",
        source_id or "user",
    )

    return {
        "action_id": action.id,
        "action_type": action.action_type,
        "app_name": action.app_name,
        "window_title": action.window_title,
        "target_description": action.target_description,
        "risk_level": action.risk_level,
        "approval_status": action.approval_status,
        "requires_approval": preview["requires_approval"],
        "risk_reasons": preview["risk_reasons"],
        "permission_warnings": preview.get("permission_warnings", []),
        "text_to_type_redacted": preview.get("text_to_type_redacted", ""),
        "expected_result": preview.get("expected_result", ""),
        "steps": [
            {
                "step_order": 1,
                "step_type": action_type,
                "target_description": target_description,
                "requires_approval": preview["requires_approval"],
            }
        ],
    }


def approve_screen_action(db: Session, action_id: int) -> dict:
    action = db.get(ScreenControlAction, action_id)
    if action is None:
        raise ValueError("Screen action not found")
    if action.status != "planned":
        raise ValueError(f"Action is not in 'planned' state (status={action.status})")

    action.approval_status = "approved"
    action.status = "approved"
    db.commit()

    _log_audit(db, "screen.action_approved", f"Screen action #{action_id} approved", "user")

    return {
        "action_id": action.id,
        "status": action.status,
        "approval_status": action.approval_status,
    }


def reject_screen_action(db: Session, action_id: int) -> dict:
    action = db.get(ScreenControlAction, action_id)
    if action is None:
        raise ValueError("Screen action not found")

    action.approval_status = "rejected"
    action.status = "rejected"
    db.commit()

    _log_audit(db, "screen.action_rejected", f"Screen action #{action_id} rejected", "user")

    return {
        "action_id": action.id,
        "status": action.status,
        "approval_status": action.approval_status,
    }


def execute_screen_action_step(
    db: Session,
    action_id: int,
    approve_before_execute: bool = True,
) -> dict:
    action = db.get(ScreenControlAction, action_id)
    if action is None:
        raise ValueError("Screen action not found")

    if approve_before_execute and action.approval_status != "approved":
        raise ValueError("Action has not been approved yet")

    if action.status not in ("approved", "planned"):
        raise ValueError(f"Action cannot be executed (status={action.status})")

    # Emergency stop check
    if _is_emergency_stop(action.session_id):
        action.status = "stopped"
        action.stopped_by = "emergency_stop"
        action.stop_reason = "Emergency stop triggered before step execution"
        db.commit()
        raise ValueError("Emergency stop triggered before step execution")

    # Create step log
    step_log = ScreenControlStepLog(
        action_id=action_id,
        step_order=1,
        step_type=action.action_type,
        target_description=action.target_description,
        status="running",
    )
    db.add(step_log)
    db.flush()

    action.status = "running"

    params = {
        "file_path": action.planned_action_json.get("file_path", ""),
        "folder_path": action.planned_action_json.get("folder_path", ""),
        "text": action.planned_action_json.get("text", ""),
        "keys": action.planned_action_json.get("keys", ""),
        "target": action.planned_action_json.get("target", ""),
        "coordinates": action.planned_action_json.get("coordinates"),
        "url": action.planned_action_json.get("url", ""),
        "intent": action.planned_action_json.get("intent", ""),
        "browser_action": action.planned_action_json.get("browser_action", ""),
    }

    result = execute_action(
        action.action_type, params,
        db=db, session_id=action.session_id,
    )

    # Check emergency stop during execution
    if _is_emergency_stop(action.session_id):
        step_log.status = "skipped"
        step_log.stopped_by = "emergency_stop"
        step_log.stop_reason = "Emergency stop during execution"
        step_log.result_json = {"stopped": True}
        action.status = "stopped"
        action.stopped_by = "emergency_stop"
        action.stop_reason = "Emergency stop during execution"
        action.error_message = "Emergency stop during execution"
    elif result.get("success"):
        step_log.status = "completed"
        action.status = "completed"
        action.completed_at = datetime.utcnow()
        if result.get("delegated") and result.get("browser_run"):
            action.browser_action_run_id = result["browser_run"].get("action_id")
    else:
        step_log.status = "failed"
        action.status = "failed"
        step_log.error_message = result.get("error", "Unknown error")
        action.error_message = result.get("error", "Unknown error")

    step_log.result_json = result
    action.executed_action_json = params
    action.result_json = result

    db.commit()
    db.refresh(step_log)

    _log_audit(
        db, "screen.action_executed",
        f"Screen action #{action_id} step_log #{step_log.id} -> {step_log.status}",
        "user",
    )

    return {
        "step_log_id": step_log.id,
        "step_order": step_log.step_order,
        "status": step_log.status,
        "result": result,
    }


def execute_all_approved_steps(
    db: Session,
    action_id: int,
) -> list[dict]:
    """Execute all steps in an approved action sequentially.

    Returns a list of step execution results.
    """
    action = db.get(ScreenControlAction, action_id)
    if action is None:
        raise ValueError("Screen action not found")
    if action.approval_status != "approved":
        raise ValueError("Action has not been approved yet")

    results = []
    step_result = execute_screen_action_step(db, action_id, approve_before_execute=False)
    results.append(step_result)

    return results


def cancel_screen_action(db: Session, action_id: int) -> dict:
    action = db.get(ScreenControlAction, action_id)
    if action is None:
        raise ValueError("Screen action not found")

    action.status = "cancelled"
    db.commit()

    _log_audit(db, "screen.action_cancelled", f"Screen action #{action_id} cancelled", "user")

    return {
        "action_id": action.id,
        "status": action.status,
    }


# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------


def _log_audit(db: Session, action: str, details: str, actor: str = "user") -> None:
    try:
        log = AuditLog(
            actor=actor,
            action=action,
            entity_type="screen_control",
            entity_id="",
            details=details,
        )
        db.add(log)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to write audit log: %s", exc)


# ---------------------------------------------------------------------------
# Voice intent dispatcher
# ---------------------------------------------------------------------------


KNOWN_VOICE_INTENTS: list[dict] = [
    {"intent": "what is on my screen", "action_type": "read_screen", "risk": "low"},
    {"intent": "read current window", "action_type": "read_window", "risk": "low"},
    {"intent": "open invoice folder", "action_type": "open_folder", "risk": "low"},
    {"intent": "open this invoice file", "action_type": "open_file", "risk": "low"},
    {"intent": "copy vendor and amount from this invoice", "action_type": "copy_to_clipboard", "risk": "medium"},
    {"intent": "fill this invoice into the test form", "action_type": "paste_to_target", "risk": "medium"},
    {"intent": "stop automation", "action_type": "stop", "risk": "low"},
    {"intent": "emergency stop", "action_type": "emergency_stop", "risk": "low"},
    {"intent": "show screen-control logs", "action_type": "show_logs", "risk": "low"},
]


def dispatch_voice_intent(
    db: Session,
    intent: str,
    source_id: str = "",
    session_id: Optional[int] = None,
) -> dict:
    """Map a voice intent to a screen action preview."""
    intent_lower = intent.lower()
    action_type = "read_screen"

    for known in KNOWN_VOICE_INTENTS:
        if known["intent"] in intent_lower:
            action_type = known["action_type"]
            break

    if action_type in ("stop", "emergency_stop"):
        if session_id:
            emergency_stop_screen(db, session_id=session_id)
        return {
            "intent": intent,
            "parsed_action": action_type,
            "preview": {
                "action_id": 0,
                "action_type": action_type,
                "app_name": "",
                "window_title": "",
                "target_description": "",
                "risk": {"risk_level": "low", "requires_approval": False, "reasons": []},
                "steps": [],
            },
        }

    if action_type == "show_logs":
        return {
            "intent": intent,
            "parsed_action": action_type,
            "preview": {
                "action_id": 0,
                "action_type": action_type,
                "app_name": "",
                "window_title": "",
                "target_description": "",
                "risk": {"risk_level": "low", "requires_approval": False, "reasons": []},
                "steps": [],
            },
        }

    ctx = detect_active_window()

    if not session_id:
        try:
            session_info = start_screen_session(db, source_id or "voice")
            session_id = session_info["session_id"]
        except ValueError:
            return {
                "intent": intent,
                "parsed_action": action_type,
                "error": "Screen control is disabled",
            }

    preview = build_action_preview(action_type, ctx.get("app", ""), ctx.get("window_title", ""))

    action_info = create_screen_action(
        db=db,
        session_id=session_id,
        action_type=action_type,
        source_type="voice",
        source_id=source_id or "voice",
        app_name=ctx.get("app", ""),
        window_title=ctx.get("window_title", ""),
        target_description=action_type.replace("_", " ").title(),
        planned_action={"intent": intent},
    )

    return {
        "intent": intent,
        "parsed_action": action_type,
        "preview": {
            "action_id": action_info["action_id"],
            "action_type": action_type,
            "app_name": ctx.get("app", ""),
            "window_title": ctx.get("window_title", ""),
            "target_description": action_type.replace("_", " ").title(),
            "risk": {
                "risk_level": preview["risk_level"],
                "requires_approval": preview["requires_approval"],
                "reasons": preview["risk_reasons"],
            },
            "steps": action_info["steps"],
        },
    }
