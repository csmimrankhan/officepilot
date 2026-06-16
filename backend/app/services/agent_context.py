from __future__ import annotations

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.user import User
from ..services.safety import is_kill_switch_active
from ..services.settings import get_setting
from ..services.agent_memory import list_workflow_memory


def build_agent_context(db: Session, current_user: User | None = None) -> dict:
    settings = get_settings()
    kill_switch_active = is_kill_switch_active()

    recent_workflows = []
    try:
        wf_memories = list_workflow_memory(db, user_id=current_user.id if current_user else None, limit=5)
        recent_workflows = [{"id": w.id, "name": w.workflow_name} for w in wf_memories]
    except Exception:
        pass

    safety_policy = {}
    try:
        from ..services.safety import get_or_create_safety_policy
        policy = get_or_create_safety_policy(db)
        safety_policy = {
            "browser_automation_enabled": policy.browser_automation_enabled,
            "screen_control_enabled": policy.screen_control_enabled,
            "workflow_recording_enabled": policy.workflow_recording_enabled,
            "accounting_sync_enabled": policy.accounting_sync_enabled,
        }
    except Exception:
        pass

    context = {
        "app_name": "OfficePilot AI",
        "app_version": "0.36.1",
        "phase": 23,
        "demo_mode": settings.demo_mode,
        "agent_provider": settings.agent_provider,
        "agent_allow_cloud": settings.agent_allow_cloud,
        "agent_dry_run_default": settings.agent_dry_run_default,
        "kill_switch_active": kill_switch_active,
        "user_role": current_user.role if current_user else "anonymous",
        "voice_approval_enabled": settings.voice_approval_enabled,
        "recent_workflows": recent_workflows,
        "safety_policy": safety_policy,
        "screen_control_enabled": settings.screen_control_enabled,
        "browser_enabled": settings.browser_enabled,
        "accounting_sync_enabled": settings.accounting_sync_enabled,
        "active_app": None,
        "active_window_title": None,
        "current_browser_url": None,
        "visible_text_excerpt": None,
    }

    try:
        active_window = _get_active_window()
        if active_window:
            context["active_app"] = active_window.get("app")
            context["active_window_title"] = active_window.get("title")
    except Exception:
        pass

    return context


def _get_active_window() -> dict | None:
    try:
        import sys as _sys
        if _sys.platform == "win32":
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            return {"app": title.split(" - ")[-1] if " - " in title else title, "title": title}
    except Exception:
        pass
    return None
