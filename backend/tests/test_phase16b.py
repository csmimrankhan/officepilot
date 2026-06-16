"""Phase 16B — Enterprise Team Hardening + Production Safety tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import Base
from app.main import app
from app.models.role_permission import ROLES, PERMISSION_NAMES
from app.models.safety_policy import SafetyPolicy
from app.models.role_permission import RolePermission
from app.models.audit_export import AuditExport
from app.models.user import User
from app.services.auth import hash_password
from app.services.safety import (
    activate_kill_switch,
    deactivate_kill_switch,
    get_or_create_safety_policy,
    is_kill_switch_active,
    check_kill_switch_blocked,
    _kill_switch,
)
from app.services.permissions import (
    check_permission,
    get_role_permissions,
    seed_default_permissions,
    update_permissions,
)
from app.services.audit_exports import build_export, list_exports
from app.services.readiness import build_readiness_report
from app.services.backup import get_backup_status, run_local_backup, test_restore


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    from app.db import engine
    from sqlalchemy import text

    tables = [
        "safety_policies",
        "role_permissions",
        "audit_exports",
    ]
    with engine.begin() as conn:
        for tbl in tables:
            try:
                conn.execute(text(f"DELETE FROM {tbl}"))
            except Exception:
                pass


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
    # Register owner user and set default auth header
    from app.db import SessionLocal as SL
    db = SL()
    db.add(User(
        email="owner@test.com",
        password_hash=hash_password("Test@1234"),
        role="owner",
        status="active",
    ))
    db.commit()
    db.close()
    with TestClient(app) as c:
        login = c.post("/api/auth/login", json={"email": "owner@test.com", "password": "Test@1234"})
        token = login.json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c
    app.dependency_overrides.clear()


def _staff_token(client):
    """Create a staff user, login, return token."""
    from app.db import SessionLocal
    db = SessionLocal()
    db.add(User(email="staff@test.com", password_hash=hash_password("Test@1234"), role="staff", status="active"))
    db.commit()
    db.close()
    r = client.post("/api/auth/login", json={"email": "staff@test.com", "password": "Test@1234"})
    return r.json()["access_token"]


# ── Safety Policy: unit tests ───────────────────────────────────────


class TestSafetyPolicyDefaults:
    def test_default_policy_is_safe(self, db_session: Session):
        policy = get_or_create_safety_policy(db_session)
        assert policy.cloud_ai_allowed is False
        assert policy.browser_automation_enabled is False
        assert policy.screen_control_enabled is False
        assert policy.workflow_recording_enabled is False
        assert policy.accounting_sync_enabled is False
        assert policy.voice_enabled is False
        assert policy.screenshots_enabled is False
        assert policy.ocr_enabled is False
        assert policy.require_approval_for_write is True
        assert policy.require_snapshot_for_file_changes is True
        assert policy.block_unknown_apps is True
        assert policy.block_unknown_domains is True

    def test_update_policy(self, db_session: Session):
        policy = get_or_create_safety_policy(db_session)
        assert policy.browser_automation_enabled is False

        from app.services.safety import update_safety_policy
        updated = update_safety_policy(db_session, {"browser_automation_enabled": True})
        assert updated.browser_automation_enabled is True

        policy2 = get_or_create_safety_policy(db_session)
        assert policy2.browser_automation_enabled is True

    def test_singleton_policy(self, db_session: Session):
        p1 = get_or_create_safety_policy(db_session)
        p2 = get_or_create_safety_policy(db_session)
        assert p1.id == p2.id


# ── Role Permissions: unit tests ────────────────────────────────────


class TestRolePermissions:
    def test_seed_defaults(self, db_session: Session):
        seed_default_permissions(db_session)
        rows = db_session.query(RolePermission).all()
        # owner gets all permissions, admin gets a subset, etc.
        assert len(rows) > 0

    def test_check_permission_owner(self, db_session: Session):
        seed_default_permissions(db_session)
        assert check_permission(db_session, "owner", "manage_safety_policies") is True
        assert check_permission(db_session, "owner", "manage_permissions") is True

    def test_check_permission_staff(self, db_session: Session):
        seed_default_permissions(db_session)
        assert check_permission(db_session, "staff", "upload_invoices") is True
        assert check_permission(db_session, "staff", "manage_safety_policies") is False
        assert check_permission(db_session, "staff", "manage_permissions") is False

    def test_check_permission_viewer(self, db_session: Session):
        seed_default_permissions(db_session)
        assert check_permission(db_session, "viewer", "view_reports") is True
        assert check_permission(db_session, "viewer", "upload_invoices") is False
        assert check_permission(db_session, "viewer", "approve_invoices") is False

    def test_update_permissions(self, db_session: Session):
        seed_default_permissions(db_session)
        update_permissions(db_session, "staff", [
            {"permission_name": "manage_safety_policies", "enabled": True},
        ])
        assert check_permission(db_session, "staff", "manage_safety_policies") is True

    def test_get_role_permissions(self, db_session: Session):
        seed_default_permissions(db_session)
        perms = get_role_permissions(db_session, "viewer")
        assert "view_reports" in perms
        assert "upload_invoices" not in perms


# ── Kill Switch: unit tests ─────────────────────────────────────────


class TestKillSwitch:
    @pytest.fixture(autouse=True)
    def _reset_ks(self):
        _kill_switch.clear()
        yield

    def test_default_inactive(self):
        assert is_kill_switch_active() is False

    def test_activate(self, db_session: Session):
        disabled = activate_kill_switch(db_session, activated_by="test@test.com", reason="test")
        assert is_kill_switch_active() is True
        assert "browser_automation" in disabled
        assert "screen_control" in disabled

    def test_deactivate(self, db_session: Session):
        activate_kill_switch(db_session, activated_by="test@test.com", reason="test")
        assert is_kill_switch_active() is True
        deactivate_kill_switch(db_session, resumed_by="test@test.com")
        assert is_kill_switch_active() is False

    def test_blocked_services(self, db_session: Session):
        activate_kill_switch(db_session, activated_by="test@test.com", reason="test")
        assert check_kill_switch_blocked("browser_automation") is True
        assert check_kill_switch_blocked("screen_control") is True
        assert check_kill_switch_blocked("workflow_recording") is True
        assert check_kill_switch_blocked("accounting_sync") is True

    def test_unknown_service_not_blocked(self, db_session: Session):
        activate_kill_switch(db_session, activated_by="test@test.com", reason="test")
        assert check_kill_switch_blocked("unknown_service") is False

    def test_resume_restores_allowed(self, db_session: Session):
        activate_kill_switch(db_session, activated_by="test@test.com", reason="test")
        deactivate_kill_switch(db_session, resumed_by="test@test.com")
        assert check_kill_switch_blocked("browser_automation") is False


# ── Audit Export: unit tests ────────────────────────────────────────


class TestAuditExport:
    def test_build_empty_export_json(self, db_session: Session):
        export = build_export(
            db_session,
            export_type="json",
            date_from="",
            date_to="",
            log_types=[],
        )
        assert export.status == "completed"
        assert export.export_type == "json"
        fpath = Path(export.file_path)
        assert fpath.exists()
        data = json.loads(fpath.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_build_export_csv(self, db_session: Session):
        export = build_export(db_session, "csv", "", "", [])
        assert export.status == "completed"
        fpath = Path(export.file_path)
        assert fpath.exists()

    def test_build_export_zip(self, db_session: Session):
        export = build_export(db_session, "zip", "", "", [])
        assert export.status == "completed"
        fpath = Path(export.file_path)
        assert fpath.exists()
        import zipfile
        with zipfile.ZipFile(fpath, "r") as zf:
            names = zf.namelist()
            assert any(n.endswith(".json") for n in names)

    def test_list_exports(self, db_session: Session):
        build_export(db_session, "json", "", "", [])
        exports = list_exports(db_session)
        assert len(exports) == 1

    def test_export_with_date_filters(self, db_session: Session):
        export = build_export(
            db_session, "json", "2026-01-01", "2026-12-31", ["audit_logs"]
        )
        assert export.status == "completed"


# ── Readiness: unit tests ───────────────────────────────────────────


class TestReadiness:
    def test_build_report(self, db_session: Session):
        report = build_readiness_report(db_session)
        assert "overall" in report
        assert "items" in report
        assert len(report["items"]) > 0

    def test_report_has_required_checks(self, db_session: Session):
        report = build_readiness_report(db_session)
        names = {item["name"] for item in report["items"]}
        required = {"Backend Process", "Database", "Storage Path", "Safety Policy"}
        assert required.issubset(names), f"Missing: {required - names}"


# ── Backup: unit tests ──────────────────────────────────────────────


class TestBackup:
    def test_backup_status(self):
        status = get_backup_status()
        assert "database_path" in status
        assert "disk_free_gb" in status
        assert "last_restore_test_status" in status

    def test_run_local_backup(self):
        result = run_local_backup()
        assert result["status"] in ("completed", "failed")

    def test_test_restore(self):
        result = test_restore()
        assert "status" in result


# ── Integration: safety API endpoints ───────────────────────────────


class TestSafetyAPI:
    def test_get_policies(self, client):
        resp = client.get("/api/safety/policies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cloud_ai_allowed"] is False
        assert data["browser_automation_enabled"] is False

    def test_owner_can_update_policy(self, client):
        resp = client.patch(
            "/api/safety/policies",
            json={"browser_automation_enabled": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["browser_automation_enabled"] is True

    def test_staff_cannot_update_policy(self, client):
        token = _staff_token(client)
        resp = client.patch(
            "/api/safety/policies",
            json={"browser_automation_enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_kill_switch_endpoint(self, client):
        resp = client.post("/api/safety/kill-switch?reason=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] is True
        assert len(data["disabled_services"]) > 0

    def test_resume_automation(self, client):
        client.post("/api/safety/kill-switch?reason=test")
        resp = client.post("/api/safety/resume-automation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] is False

    def test_automation_status(self, client):
        resp = client.get("/api/safety/automation-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "kill_switch_active" in data
        assert "browser_automation_blocked" in data


# ── Integration: permissions API ────────────────────────────────────


class TestPermissionsAPI:
    def test_list_permissions(self, client):
        resp = client.get("/api/permissions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0

    def test_staff_cannot_list_permissions(self, client):
        token = _staff_token(client)
        resp = client.get("/api/permissions", headers={"Authorization": f"Bearer {token}"})
        # staff can view but not manage
        assert resp.status_code in (200, 403)

    def test_my_permissions(self, client):
        resp = client.get("/api/permissions/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "owner"
        assert "upload_invoices" in data["permissions"]

    def test_update_role_permissions(self, client):
        resp = client.patch(
            "/api/permissions/staff",
            json={"entries": [{"permission_name": "manage_safety_policies", "enabled": True}]},
        )
        assert resp.status_code == 200

    def test_staff_cannot_update_permissions(self, client):
        token = _staff_token(client)
        resp = client.patch(
            "/api/permissions/staff",
            json={"entries": [{"permission_name": "manage_safety_policies", "enabled": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ── Integration: audit export API ───────────────────────────────────


class TestAuditExportAPI:
    def test_create_export(self, client):
        resp = client.post(
            "/api/audit/export",
            json={"export_type": "json", "date_from": "", "date_to": "", "log_types": []},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["id"] > 0

    def test_list_exports(self, client):
        client.post(
            "/api/audit/export",
            json={"export_type": "json", "date_from": "", "date_to": "", "log_types": []},
        )
        resp = client.get("/api/audit/exports")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0

    def test_download_export(self, client):
        resp = client.post(
            "/api/audit/export",
            json={"export_type": "json", "date_from": "", "date_to": "", "log_types": []},
        )
        export_id = resp.json()["id"]

        resp2 = client.get(f"/api/audit/exports/{export_id}/download")
        assert resp2.status_code == 200
        assert resp2.headers["content-type"] == "application/json"


# ── Integration: readiness API ──────────────────────────────────────


class TestReadinessAPI:
    def test_readiness_endpoint(self, client):
        resp = client.get("/api/system/readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall"] in ("green", "yellow", "red")
        assert len(data["items"]) > 0


# ── Integration: backup API ─────────────────────────────────────────


class TestBackupAPI:
    def test_backup_status_endpoint(self, client):
        resp = client.get("/api/backup/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "database_path" in data

    def test_run_backup_endpoint(self, client):
        resp = client.post("/api/backup/run-local")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("completed", "failed")

    def test_test_restore_endpoint(self, client):
        resp = client.post("/api/backup/test-restore")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


# ── Integration: permission enforcement in actions ──────────────────


class TestPermissionEnforcement:
    def test_reviewer_can_approve(self, client):
        resp = client.get("/api/permissions/me")
        assert resp.status_code == 200
        data = resp.json()
        assert "approve_invoices" in data["permissions"]

    def test_staff_cannot_manage_screen_control(self, client):
        token = _staff_token(client)
        resp = client.patch(
            "/api/safety/policies",
            json={"screen_control_enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ── Integration: kill switch blocks automation ──────────────────────


class TestKillSwitchIntegration:
    def test_kill_switch_stops_automation_in_status(self, client):
        client.post("/api/safety/kill-switch?reason=test")
        resp = client.get("/api/safety/automation-status")
        data = resp.json()
        assert data["kill_switch_active"] is True
        assert data["browser_automation_blocked"] is True
        assert data["screen_control_blocked"] is True

    def test_resume_restores_enabled(self, client):
        client.post("/api/safety/kill-switch?reason=test")
        client.post("/api/safety/resume-automation")
        resp = client.get("/api/safety/automation-status")
        data = resp.json()
        assert data["kill_switch_active"] is False
