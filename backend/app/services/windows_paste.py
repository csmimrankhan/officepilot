"""
Windows paste service for the voice layer.

Provides clipboard-safe text pasting at the active cursor position.
Safety checks prevent pasting into password/secure fields.
"""

import logging
import subprocess
import sys

logger = logging.getLogger("officepilot.voice_layer.paste")

SENSITIVE_WINDOW_KEYWORDS = [
    "password", "pin", "otp", "2fa", "totp", "secret",
    "credential", "token", "security", "login",
    "sign in", "authenticate", "mfa",
]

SENSITIVE_PROCESS_NAMES = [
    "keepass", "bitwarden", "1password", "lastpass",
    "password", "credential", "authenticator",
]


def _detect_sensitive_window() -> bool:
    """Check if the active window is a password/secure input field."""
    try:
        if sys.platform == "win32":
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd) + 1
            buf = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buf, length)
            title = buf.value.lower()
            for kw in SENSITIVE_WINDOW_KEYWORDS:
                if kw in title:
                    logger.warning("Sensitive window detected: %s", title[:60])
                    return True
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            try:
                process = kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
                if process:
                    exe_buf = ctypes.create_unicode_buffer(260)
                    kernel32.GetModuleBaseNameW(process, None, exe_buf, 260)
                    kernel32.CloseHandle(process)
                    exe_name = exe_buf.value.lower()
                    for kw in SENSITIVE_PROCESS_NAMES:
                        if kw in exe_name:
                            logger.warning("Sensitive process detected: %s", exe_name)
                            return True
            except Exception:
                pass
    except Exception as exc:
        logger.debug("Window detection error (non-fatal): %s", exc)
    return False


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the Windows clipboard."""
    if not text:
        return False
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        pass
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        pass
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Set-Clipboard -Value {repr(text)}"],
            capture_output=True, timeout=5, check=False,
        )
        return proc.returncode == 0
    except Exception as exc:
        logger.error("Clipboard copy failed: %s", exc)
        return False


def send_ctrl_v() -> bool:
    """Send Ctrl+V keystroke to paste at cursor."""
    try:
        import pyautogui
        pyautogui.hotkey("ctrl", "v")
        return True
    except ImportError:
        pass
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            ctypes.windll.user32.SendMessageW(hwnd, 0x0100, 0x11, 0)  # WM_KEYDOWN Ctrl
            ctypes.windll.user32.SendMessageW(hwnd, 0x0100, 0x56, 0)  # WM_KEYDOWN V
            ctypes.windll.user32.SendMessageW(hwnd, 0x0101, 0x56, 0)  # WM_KEYUP V
            ctypes.windll.user32.SendMessageW(hwnd, 0x0101, 0x11, 0)  # WM_KEYUP Ctrl
            return True
    except Exception as exc:
        logger.error("Send Ctrl+V failed: %s", exc)
    return False


def paste_text_at_cursor(text: str, confirm_before_paste: bool = True) -> dict:
    """
    Copy text to clipboard and paste at active cursor.
    
    Returns dict with status and details.
    """
    if not text:
        return {"ok": False, "error": "Empty text - nothing to paste"}

    if _detect_sensitive_window():
        return {
            "ok": False,
            "error": "Active window appears to be a password/secure field. Paste blocked for safety.",
            "blocked": True,
        }

    if not copy_to_clipboard(text):
        return {"ok": False, "error": "Failed to copy text to clipboard"}

    if confirm_before_paste:
        return {
            "ok": True,
            "status": "confirm_required",
            "message": "Text copied to clipboard. Click confirm to paste at cursor.",
            "text": text[:200],
        }

    if not send_ctrl_v():
        return {"ok": False, "error": "Failed to send paste keystroke"}

    return {"ok": True, "status": "pasted", "message": "Text pasted at cursor."}


def restore_clipboard(previous: str | None = None) -> None:
    """Restore previous clipboard content if available."""
    if previous:
        try:
            import pyperclip
            pyperclip.copy(previous)
        except Exception:
            pass
