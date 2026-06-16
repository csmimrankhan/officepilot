"""Phase 17 — Authentication, persistent kill switch, and security hardening tests."""

from __future__ import annotations

import os
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.automation_safety_state import AutomationSafetyState
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    login_user,
    register_user,
    verify_password,
)
from app.services.permissions import check_permission, seed_default_permissions
from app.services.safety import (
    activate_kill_switch,
    deactivate_kill_switch,
    get_kill_switch_state,
    init_kill_switch,
    is_kill_switch_active,
)


# ── Password hashing: unit tests ────────────────────────────────────


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "my_secret_password_123"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_invalid_hash_format(self):
        assert verify_password("any", "invalid_format") is False

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("x", hashed) is False


# ── JWT: unit tests ─────────────────────────────────────────────────


class TestJWT:
    def test_create_and_decode_access_token(self):
        token = create_access_token(1, "test@example.com", "owner")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "owner"
        assert payload["type"] == "access"

    def test_create_and_decode_refresh_token(self):
        token = create_refresh_token(1)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["type"] == "refresh"

    def test_expired_token_rejected(self):
        # Create token with short expiry
        old = os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "0"
        token = create_access_token(1, "test@example.com", "staff")
        os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = old
        time.sleep(0.01)  # ensure expiry
        payload = decode_token(token)
        assert payload is None

    def test_tampered_token_rejected(self):
        token = create_access_token(1, "test@example.com", "owner")
        modified = token[:-5] + "XXXXX"
        payload = decode_token(modified)
        assert payload is None

    def test_invalid_token_rejected(self):
        payload = decode_token("not.a.token")
        assert payload is None


# ── User registration / login / bootstrap: unit tests ───────────────


class TestUserAuth:
    def test_register_first_user_is_owner(self, db_session: Session):
        user = register_user(db_session, "owner@test.com", "Test@1234", "Owner User")
        assert user.role == "owner"
        assert user.status == "active"

    def test_second_user_is_staff(self, db_session: Session):
        register_user(db_session, "owner@test.com", "Test@1234")
        staff = register_user(db_session, "staff@test.com", "Test@1234")
        assert staff.role == "staff"

    def test_register_duplicate_email(self, db_session: Session):
        # Create first user directly to bypass registration-closed guard
        db_session.add(User(email="dup@test.com", role="owner", status="active", password_hash=hash_password("x")))
        db_session.commit()
        with pytest.raises(ValueError, match="already exists"):
            register_user(db_session, "dup@test.com", "Test@1234")

    def test_authenticate_valid_user(self, db_session: Session):
        register_user(db_session, "auth@test.com", "Myp@ss1", "Auth User")
        user = authenticate_user(db_session, "auth@test.com", "Myp@ss1")
        assert user is not None
        assert user.email == "auth@test.com"

    def test_authenticate_wrong_password(self, db_session: Session):
        register_user(db_session, "auth2@test.com", "C0rr3ct!")
        user = authenticate_user(db_session, "auth2@test.com", "wrongpw")
        assert user is None

    def test_authenticate_unknown_user(self, db_session: Session):
        user = authenticate_user(db_session, "nobody@test.com", "P@ss1234")
        assert user is None

    def test_disabled_user_rejected(self, db_session: Session):
        user = register_user(db_session, "disabled@test.com", "Test@1234")
        user.status = "disabled"
        db_session.flush()
        result = authenticate_user(db_session, "disabled@test.com", "Test@1234")
        assert result is None

    def test_login_returns_tokens(self, db_session: Session):
        register_user(db_session, "login@test.com", "Test@1234", "Login User")
        result = login_user(db_session, "login@test.com", "Test@1234")
        assert result is not None
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["user"]["email"] == "login@test.com"

    def test_login_wrong_password(self, db_session: Session):
        register_user(db_session, "login2@test.com", "C0rr3ct!")
        result = login_user(db_session, "login2@test.com", "wrongpw")
        assert result is None


# ── Role permission checks: integration ─────────────────────────────


class TestRolePermissionChecks:
    def test_owner_has_permissions(self, db_session: Session):
        seed_default_permissions(db_session)
        assert check_permission(db_session, "owner", "manage_safety_policies") is True
        assert check_permission(db_session, "owner", "manage_permissions") is True
        assert check_permission(db_session, "owner", "export_audit") is True

    def test_staff_limited_permissions(self, db_session: Session):
        seed_default_permissions(db_session)
        assert check_permission(db_session, "staff", "upload_invoices") is True
        assert check_permission(db_session, "staff", "manage_safety_policies") is False
        assert check_permission(db_session, "staff", "export_audit") is False

    def test_viewer_read_only(self, db_session: Session):
        seed_default_permissions(db_session)
        assert check_permission(db_session, "viewer", "view_reports") is True
        assert check_permission(db_session, "viewer", "view_logs") is True
        assert check_permission(db_session, "viewer", "upload_invoices") is False
        assert check_permission(db_session, "viewer", "approve_invoices") is False


# ── Persistent kill switch: unit tests ──────────────────────────────


class TestPersistentKillSwitch:
    def test_default_inactive(self):
        assert is_kill_switch_active() is False

    def test_activate_and_deactivate(self, db_session: Session):
        activate_kill_switch(db_session, activated_by="test@test.com", reason="Testing")
        assert is_kill_switch_active() is True

        state = get_kill_switch_state(db_session)
        assert state["kill_switch_active"] is True
        assert state["activated_by"] == "test@test.com"
        assert state["reason"] == "Testing"

        deactivate_kill_switch(db_session, resumed_by="test@test.com")
        assert is_kill_switch_active() is False

    def test_persists_across_sessions(self, db_session: Session):
        activate_kill_switch(db_session, activated_by="admin@test.com", reason="Test persist")
        db_session.commit()

        # Simulate restart by clearing the in-memory flag
        from app.services.safety import _kill_switch
        _kill_switch.clear()
        assert is_kill_switch_active() is False

        # Re-init from DB
        init_kill_switch(db_session)
        assert is_kill_switch_active() is True

    def test_kill_switch_blocks_services(self, db_session: Session):
        activate_kill_switch(db_session, activated_by="test@test.com")
        from app.services.safety import check_kill_switch_blocked
        assert check_kill_switch_blocked("browser_automation") is True
        assert check_kill_switch_blocked("screen_control") is True
        assert check_kill_switch_blocked("workflow_recording") is True
        assert check_kill_switch_blocked("accounting_sync") is True
        assert check_kill_switch_blocked("unknown_service") is False


# ── Integration: API auth endpoints ────────────────────────────────


@pytest.fixture()
def client():
    from app.db import SessionLocal, get_db

    def _override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestAuthAPI:
    def test_register_first_owner(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "owner@test.com",
            "password": "Test@1234",
            "full_name": "Owner User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["user"]["role"] == "owner"
        assert "access_token" in data
        assert "refresh_token" in data

    def test_register_second_user_becomes_staff(self, client):
        client.post("/api/auth/register", json={
            "email": "owner@test.com",
            "password": "Test@1234",
        })
        resp = client.post("/api/auth/register", json={
            "email": "staff@test.com",
            "password": "Test@1234",
        })
        assert resp.status_code == 201
        assert resp.json()["user"]["role"] == "staff"

    def test_login(self, client):
        client.post("/api/auth/register", json={
            "email": "login@test.com",
            "password": "Test@1234",
        })
        resp = client.post("/api/auth/login", json={
            "email": "login@test.com",
            "password": "Test@1234",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={
            "email": "badlogin@test.com",
            "password": "Test@1234",
        })
        resp = client.post("/api/auth/login", json={
            "email": "badlogin@test.com",
            "password": "wrong",
        })
        assert resp.status_code == 401

    def test_me_authenticated(self, client):
        client.post("/api/auth/register", json={
            "email": "me@test.com",
            "password": "Test@1234",
        })
        login = client.post("/api/auth/login", json={
            "email": "me@test.com",
            "password": "Test@1234",
        })
        token = login.json()["access_token"]
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["email"] == "me@test.com"

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_refresh_token(self, client):
        client.post("/api/auth/register", json={
            "email": "refresh@test.com",
            "password": "Test@1234",
        })
        login = client.post("/api/auth/login", json={
            "email": "refresh@test.com",
            "password": "Test@1234",
        })
        refresh_token = login.json()["refresh_token"]
        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_logout(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ── Integration: protected endpoints ───────────────────────────────


class TestProtectedEndpoints:
    def _register_and_login(self, client, email="owner@test.com", pw="Test@1234"):
        client.post("/api/auth/register", json={"email": email, "password": pw})
        r = client.post("/api/auth/login", json={"email": email, "password": pw})
        return r.json()["access_token"]

    def test_owner_can_update_safety_policy(self, client):
        token = self._register_and_login(client, "owner@test.com")
        resp = client.patch(
            "/api/safety/policies",
            json={"browser_automation_enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["browser_automation_enabled"] is True

    def test_staff_cannot_update_safety_policy(self, client):
        # Register first as owner
        self._register_and_login(client, "owner@test.com")
        # Register a staff user (will fail due to closed registration, so we create directly)
        from app.db import SessionLocal
        from app.services.auth import hash_password
        db = SessionLocal()
        db.add(User(email="staff@test.com", password_hash=hash_password("Test@1234"), role="staff", status="active"))
        db.commit()
        db.close()

        r = client.post("/api/auth/login", json={"email": "staff@test.com", "password": "Test@1234"})
        token = r.json()["access_token"]

        resp = client.patch(
            "/api/safety/policies",
            json={"browser_automation_enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_owner_can_activate_kill_switch(self, client):
        token = self._register_and_login(client, "ks@test.com")
        resp = client.post("/api/safety/kill-switch?reason=API test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["active"] is True

    def test_staff_cannot_activate_kill_switch(self, client):
        self._register_and_login(client, "owner_ks@test.com")
        from app.db import SessionLocal
        from app.services.auth import hash_password
        db = SessionLocal()
        db.add(User(email="staff_ks@test.com", password_hash=hash_password("Test@1234"), role="staff", status="active"))
        db.commit()
        db.close()

        r = client.post("/api/auth/login", json={"email": "staff_ks@test.com", "password": "Test@1234"})
        token = r.json()["access_token"]
        resp = client.post("/api/safety/kill-switch?reason=test", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_owner_can_export_audit(self, client):
        token = self._register_and_login(client, "audit@test.com")
        resp = client.post(
            "/api/audit/export",
            json={"export_type": "json", "date_from": "", "date_to": "", "log_types": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_staff_cannot_export_audit(self, client):
        self._register_and_login(client, "owner_audit@test.com")
        from app.db import SessionLocal
        from app.services.auth import hash_password
        db = SessionLocal()
        db.add(User(email="staff_audit@test.com", password_hash=hash_password("Test@1234"), role="staff", status="active"))
        db.commit()
        db.close()

        r = client.post("/api/auth/login", json={"email": "staff_audit@test.com", "password": "Test@1234"})
        token = r.json()["access_token"]
        resp = client.post(
            "/api/audit/export",
            json={"export_type": "json", "date_from": "", "date_to": "", "log_types": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_protected_endpoints_reject_no_auth(self, client):
        endpoints = [
            ("GET", "/api/safety/policies"),
            ("PATCH", "/api/safety/policies"),
            ("POST", "/api/safety/kill-switch"),
            ("GET", "/api/permissions"),
            ("GET", "/api/permissions/me"),
            ("GET", "/api/audit/exports"),
            ("POST", "/api/audit/export"),
            ("GET", "/api/system/readiness"),
            ("GET", "/api/backup/status"),
            ("POST", "/api/backup/run-local"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = client.get(path)
            elif method == "POST":
                resp = client.post(path, json={} if "export" in path else None)
            else:
                resp = client.patch(path, json={})
            assert resp.status_code == 401, f"{method} {path} expected 401, got {resp.status_code}"

    def test_kill_switch_persists_simulation(self, client):
        token = self._register_and_login(client, "persist@test.com")
        client.post("/api/safety/kill-switch?reason=persist", headers={"Authorization": f"Bearer {token}"})

        # Simulate restart - clear in-memory event
        from app.services.safety import _kill_switch
        _kill_switch.clear()

        # Re-init from DB (mimicking lifespan restart)
        from app.db import SessionLocal
        from app.services.safety import init_kill_switch
        db = SessionLocal()
        init_kill_switch(db)
        db.close()

        assert is_kill_switch_active() is True

    def test_resume_automation(self, client):
        token = self._register_and_login(client, "resume@test.com")
        client.post("/api/safety/kill-switch?reason=test", headers={"Authorization": f"Bearer {token}"})
        resp = client.post("/api/safety/resume-automation", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["active"] is False
