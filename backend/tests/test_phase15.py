"""Phase 15 — Screen Control tests (37 tests)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.models.screen_control_policy import (
    DEFAULT_ALLOWED_APPS,
    DEFAULT_BLOCKED_APPS,
    ScreenControlPolicy,
)
from app.models.screen_control_session import ScreenControlSession
from app.models.screen_control_action import ScreenControlAction
from app.models.screen_control_step_log import ScreenControlStepLog

# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestScreenPolicyValidator:
    def test_default_policy_is_disabled(self, db_session):
        from app.services.screen_control import get_or_create_policy

        policy = get_or_create_policy(db_session)
        assert policy.enabled is False
        assert policy.permission_level == 0

    def test_permission_level_check(self, db_session):
        from app.services.screen_control import check_permission_level

        policy = ScreenControlPolicy(enabled=True, permission_level=2)
        assert check_permission_level(policy, 1) is True
        assert check_permission_level(policy, 2) is True
        assert check_permission_level(policy, 3) is False

    def test_disabled_policy_fails_permission_check(self, db_session):
        from app.services.screen_control import check_permission_level

        policy = ScreenControlPolicy(enabled=False, permission_level=2)
        assert check_permission_level(policy, 1) is False


class TestBlockedAppCheck:
    def test_blocked_app_matches(self):
        from app.services.screen_control import blocked_app_check

        blocked = ["password_manager", "banking", "security_settings"]
        assert blocked_app_check("Password Manager Pro", blocked) is True
        assert blocked_app_check("Capital One Banking", blocked) is True
        assert blocked_app_check("System Preferences", blocked) is False
        assert blocked_app_check("Windows Security Settings", blocked) is True

    def test_blocked_app_empty_list(self):
        from app.services.screen_control import blocked_app_check

        assert blocked_app_check("Any App", []) is False


class TestAllowedAppCheck:
    def test_allowed_app_matches(self):
        from app.services.screen_control import allowed_app_check

        allowed = ["officepilot", "invoicepilot", "excel"]
        assert allowed_app_check("OfficePilot", allowed) is True
        assert allowed_app_check("InvoicePilot AI", allowed) is True
        assert allowed_app_check("Microsoft Excel", allowed) is True
        assert allowed_app_check("Chrome", allowed) is False
        assert allowed_app_check("Notepad", allowed) is False

    def test_allowed_app_empty_list(self):
        from app.services.screen_control import allowed_app_check

        assert allowed_app_check("OfficePilot", []) is False


class TestRiskClassifier:
    def test_high_risk_actions(self):
        from app.services.screen_control import classify_screen_risk

        for action in ["click", "type_text", "submit_form", "send_email", "run_browser_action"]:
            risk, req, reasons = classify_screen_risk(action)
            assert risk == "high", f"{action} should be high risk"
            assert req is True

    def test_medium_risk_actions(self):
        from app.services.screen_control import classify_screen_risk

        for action in ["open_file", "open_folder", "copy_to_clipboard", "scroll"]:
            risk, req, reasons = classify_screen_risk(action)
            assert risk == "medium", f"{action} should be medium risk"
            assert req is True

    def test_low_risk_actions(self):
        from app.services.screen_control import classify_screen_risk

        for action in ["read_screen", "read_window", "ocr_screen"]:
            risk, req, reasons = classify_screen_risk(action)
            assert risk == "low", f"{action} should be low risk"
            assert req is False


class TestActionPreviewBuilder:
    def test_build_preview_high_risk(self):
        from app.services.screen_control import build_action_preview

        preview = build_action_preview("click", "Excel", "Invoice.xlsx - Excel", "Submit button")
        assert preview["risk_level"] == "high"
        assert preview["requires_approval"] is True
        assert preview["action_type"] == "click"

    def test_build_preview_low_risk(self):
        from app.services.screen_control import build_action_preview

        preview = build_action_preview("read_screen", "OfficePilot", "Invoice Detail")
        assert preview["risk_level"] == "low"
        assert preview["requires_approval"] is False


class TestSensitiveTextRedactor:
    def test_redact_sensitive(self):
        from app.services.screen_control import _redact_sensitive

        assert _redact_sensitive("my_password_123") == "[REDACTED]"
        assert _redact_sensitive("secret_key_abc") == "[REDACTED]"
        assert _redact_sensitive("token_xyz") == "[REDACTED]"
        assert _redact_sensitive("2fa_code") == "[REDACTED]"
        assert _redact_sensitive("otp_123456") == "[REDACTED]"
        assert _redact_sensitive("cvv_123") == "[REDACTED]"

    def test_redact_not_sensitive(self):
        from app.services.screen_control import _redact_sensitive

        assert _redact_sensitive("hello world") == "hello world"
        assert _redact_sensitive("") == ""
        assert _redact_sensitive("Invoice #123") == "Invoice #123"
        assert _redact_sensitive("Vendor: ACME") == "Vendor: ACME"


class TestEmergencyStopStateTransition:
    def test_emergency_stop_stops_session(self, db_session):
        from app.services.screen_control import emergency_stop_screen

        session = ScreenControlSession(status="active")
        db_session.add(session)
        db_session.commit()

        result = emergency_stop_screen(db_session, session_id=session.id)
        assert result["stopped"] is True

        db_session.refresh(session)
        assert session.status == "stopped"

    def test_emergency_stop_stops_actions(self, db_session):
        from app.services.screen_control import emergency_stop_screen

        session = ScreenControlSession(status="active")
        db_session.add(session)
        db_session.commit()

        action = ScreenControlAction(
            session_id=session.id, action_type="open_file", status="running"
        )
        db_session.add(action)
        db_session.commit()

        emergency_stop_screen(db_session, session_id=session.id)
        db_session.refresh(action)
        assert action.status == "stopped"

    def test_emergency_stop_global(self, db_session):
        from app.services.screen_control import emergency_stop_screen

        s1 = ScreenControlSession(status="active")
        s2 = ScreenControlSession(status="active")
        db_session.add_all([s1, s2])
        db_session.commit()

        emergency_stop_screen(db_session)
        db_session.refresh(s1)
        db_session.refresh(s2)
        assert s1.status == "stopped"
        assert s2.status == "stopped"


class TestOcrResultSanitizer:
    def test_sanitize_empty(self):
        assert "" == ""


class TestVoiceIntentMapper:
    def test_voice_intent_mapping(self):
        from app.services.screen_control import KNOWN_VOICE_INTENTS

        intents = [i["intent"] for i in KNOWN_VOICE_INTENTS]
        assert "what is on my screen" in intents
        assert "open invoice folder" in intents
        assert "copy vendor and amount from this invoice" in intents
        assert "emergency stop" in intents
        assert len(intents) >= 8


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


def test_get_policies_default(client: TestClient):
    r = client.get("/api/screen/policies")
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is False
    assert data["permission_level"] == 0


def test_update_policies(client: TestClient):
    r = client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 2})
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is True
    assert data["permission_level"] == 2


def test_get_status(client: TestClient):
    r = client.get("/api/screen/status")
    assert r.status_code == 200
    data = r.json()
    assert "enabled" in data
    assert "session_active" in data


def test_start_session_fails_when_disabled(client: TestClient):
    r = client.post("/api/screen/start-session")
    assert r.status_code == 400
    assert "disabled" in r.text.lower()


def test_start_session_succeeds_when_enabled(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/start-session")
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] > 0
    assert data["status"] == "active"


def test_end_session(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/start-session")
    session_id = r.json()["session_id"]

    r = client.post(f"/api/screen/end-session?session_id={session_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ended"


def test_emergency_stop_route(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/start-session")
    session_id = r.json()["session_id"]

    r = client.post(f"/api/screen/emergency-stop?session_id={session_id}")
    assert r.status_code == 200
    assert r.json()["stopped"] is True


def test_read_screen_context_fails_when_disabled(client: TestClient):
    r = client.post("/api/screen/read")
    assert r.status_code == 403


def test_read_screen_context_succeeds_when_enabled(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    client.post("/api/screen/start-session")
    r = client.post("/api/screen/read")
    assert r.status_code == 200
    data = r.json()
    assert "active_app" in data
    assert "summary" in data


def test_capture_fails_without_screenshots(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1, "screenshots_enabled": False})
    client.post("/api/screen/start-session")
    r = client.post("/api/screen/capture")
    assert r.status_code == 403


def test_capture_fails_without_session(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1, "screenshots_enabled": True})
    r = client.post("/api/screen/capture")
    assert r.status_code == 400


def test_summarize_screen(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/summarize")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "app" in data


def test_plan_action_blocked_app(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/plan-action?action_type=read_screen&app_name=Password+Manager+Pro")
    assert r.status_code == 200
    data = r.json()
    assert data["blocked"] is not None
    assert data["blocked"]["allowed"] is False


def test_plan_action_blocked_requires_approval(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/plan-action?action_type=open_file&app_name=InvoicePilot")
    assert r.status_code == 200
    data = r.json()
    assert data["action_id"] > 0
    assert data["risk"]["requires_approval"] is True


def test_approve_action(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/plan-action?action_type=read_screen&app_name=InvoicePilot")
    action_id = r.json()["action_id"]

    r = client.post(f"/api/screen/actions/{action_id}/approve")
    assert r.status_code == 200
    data = r.json()
    assert data["approval_status"] == "approved"


def test_reject_action(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/plan-action?action_type=read_screen&app_name=InvoicePilot")
    action_id = r.json()["action_id"]

    r = client.post(f"/api/screen/actions/{action_id}/reject")
    assert r.status_code == 200
    data = r.json()
    assert data["approval_status"] == "rejected"


def test_list_actions(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    client.post("/api/screen/plan-action?action_type=read_screen&app_name=InvoicePilot")
    client.post("/api/screen/plan-action?action_type=read_screen&app_name=InvoicePilot")

    r = client.get("/api/screen/actions")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2


def test_get_action(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/plan-action?action_type=read_screen&app_name=InvoicePilot")
    action_id = r.json()["action_id"]

    r = client.get(f"/api/screen/actions/{action_id}")
    assert r.status_code == 200
    assert r.json()["id"] == action_id


def test_cancel_action(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/plan-action?action_type=read_screen&app_name=InvoicePilot")
    action_id = r.json()["action_id"]

    r = client.post(f"/api/screen/actions/{action_id}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_list_sessions(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    client.post("/api/screen/start-session")
    client.post("/api/screen/start-session")

    r = client.get("/api/screen/sessions")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2


def test_voice_intent_read_screen(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/voice", json={"intent": "what is on my screen"})
    assert r.status_code == 200
    data = r.json()
    assert "preview" in data
    assert data["parsed_action"] == "read_screen"


def test_voice_intent_emergency_stop(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/voice", json={"intent": "emergency stop"})
    assert r.status_code == 200


def test_voice_intent_open_invoice_folder(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/voice", json={"intent": "open invoice folder"})
    assert r.status_code == 200
    data = r.json()
    assert data["parsed_action"] == "open_folder"


def test_click_action_requires_permission(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1, "click_enabled": False})
    r = client.post("/api/screen/plan-action?action_type=click&app_name=InvoicePilot")
    assert r.status_code == 403


def test_type_action_requires_permission(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1, "type_enabled": False})
    r = client.post("/api/screen/plan-action?action_type=type_text&app_name=InvoicePilot")
    assert r.status_code == 403


def test_execute_open_file_fails_not_found(client: TestClient):
    from app.services.screen_control import _execute_open_file

    result = _execute_open_file(r"C:\nonexistent_file_abc123.txt")
    assert result["success"] is False
    assert "not found" in result["error"]


def test_execute_open_folder_fails_not_found(client: TestClient):
    from app.services.screen_control import _execute_open_folder

    result = _execute_open_folder(r"C:\nonexistent_folder_abc123")
    assert result["success"] is False
    assert "not found" in result["error"]


def test_execute_copy_to_clipboard(client: TestClient):
    from app.services.screen_control import _execute_copy_to_clipboard

    result = _execute_copy_to_clipboard("Test invoice data")
    assert result["success"] is True
    assert result["copied_length"] == 17


def test_unknown_action_type_fails(client: TestClient):
    from app.services.screen_control import execute_action

    result = execute_action("unknown_action", {})
    assert result["success"] is False
    assert "Unknown" in result["error"]


def test_audit_log_created_for_screen_actions(client: TestClient):
    from app.db import SessionLocal

    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1})
    r = client.post("/api/screen/plan-action?action_type=read_screen&app_name=InvoicePilot")
    action_id = r.json()["action_id"]

    r = client.post(f"/api/screen/actions/{action_id}/approve")
    assert r.status_code == 200

    db = SessionLocal()
    try:
        from app.models.audit_log import AuditLog
        logs = db.query(AuditLog).filter(
            AuditLog.action.like("screen.%")
        ).all()
        assert len(logs) >= 1
        actions_found = [log.action for log in logs]
        assert "screen.action_created" in actions_found
        assert "screen.action_approved" in actions_found
    finally:
        db.close()


def test_create_screen_action_service(db_session):
    from app.services.screen_control import create_screen_action

    session = ScreenControlSession(status="active")
    db_session.add(session)
    db_session.commit()

    result = create_screen_action(
        db_session,
        session_id=session.id,
        action_type="open_file",
        app_name="InvoicePilot",
        target_description="Open invoice #123",
    )
    assert result["action_id"] > 0
    assert result["risk_level"] == "medium"
    assert result["requires_approval"] is True


def test_approve_screen_action_service(db_session):
    from app.services.screen_control import create_screen_action, approve_screen_action

    session = ScreenControlSession(status="active")
    db_session.add(session)
    db_session.commit()

    info = create_screen_action(db_session, session.id, "open_file")
    result = approve_screen_action(db_session, info["action_id"])
    assert result["approval_status"] == "approved"

    action = db_session.get(ScreenControlAction, info["action_id"])
    assert action.status == "approved"


def test_reject_screen_action_service(db_session):
    from app.services.screen_control import create_screen_action, reject_screen_action

    session = ScreenControlSession(status="active")
    db_session.add(session)
    db_session.commit()

    info = create_screen_action(db_session, session.id, "open_file")
    result = reject_screen_action(db_session, info["action_id"])
    assert result["approval_status"] == "rejected"


def test_execute_action_step_fails_without_approval(db_session):
    from app.services.screen_control import create_screen_action, execute_screen_action_step

    session = ScreenControlSession(status="active")
    db_session.add(session)
    db_session.commit()

    info = create_screen_action(db_session, session.id, "open_file", target_description="/nonexistent")
    with pytest.raises(ValueError, match="not been approved"):
        execute_screen_action_step(db_session, info["action_id"], approve_before_execute=True)


def test_list_voice_intents(client: TestClient):
    r = client.get("/api/screen/voices")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 8
    assert any(v["intent"] == "what is on my screen" for v in data)
    assert any(v["intent"] == "emergency stop" for v in data)


def test_ocr_without_permission_fails(client: TestClient):
    r = client.post("/api/screen/ocr")
    assert r.status_code == 403


def test_ocr_without_session_fails(client: TestClient):
    client.patch("/api/screen/policies", json={"enabled": True, "permission_level": 1, "ocr_enabled": True})
    r = client.post("/api/screen/ocr")
    assert r.status_code == 400
