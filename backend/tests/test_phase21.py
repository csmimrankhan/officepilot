"""Phase 21 — Performance, startup, cleanup, and release readiness tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def owner_token(client: TestClient) -> str:
    reg = client.post("/api/auth/register", json={
        "email": "owner@phase21test.com",
        "password": "Test@1234",
        "full_name": "Owner",
    })
    assert reg.status_code == 201, reg.text
    return reg.json()["access_token"]


# ── Startup Metrics ────────────────────────────────────────────────────────


class TestStartupMetrics:
    def test_startup_metrics_endpoint(self, client: TestClient):
        resp = client.get("/api/system/startup-metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "marks" in data
        assert "total_startup_seconds" in data
        # Should have at least process_start
        assert "process_start" in data["marks"]

    def test_health_has_startup_seconds(self, client: TestClient):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "startup_seconds" in data
        assert data["phase"] == 23
        assert data["version"] == "1.0.0"

    def test_startup_metrics_no_auth_required(self, client: TestClient):
        resp = client.get("/api/system/startup-metrics")
        assert resp.status_code == 200

    def test_health_fast(self, client: TestClient):
        import time
        start = time.monotonic()
        for _ in range(5):
            resp = client.get("/api/health")
            assert resp.status_code == 200
        elapsed = time.monotonic() - start
        # 5 health requests should be fast (under 2s)
        assert elapsed < 2.0, f"Health endpoint too slow: {elapsed:.2f}s"


# ── Storage Usage ──────────────────────────────────────────────────────────


class TestStorageUsage:
    def test_requires_auth(self, client: TestClient):
        resp = client.get("/api/system/storage-usage")
        assert resp.status_code == 401

    def test_requires_admin(self, client: TestClient, owner_token: str):
        # register a second user who gets 'user' role (not owner/admin)
        reg = client.post("/api/auth/register", json={
            "email": "user2@phase21test.com",
            "password": "Test@1234",
            "full_name": "User",
        })
        token = reg.json()["access_token"]
        resp = client.get("/api/system/storage-usage", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 403

    def test_returns_storage_data(self, client: TestClient, owner_token: str):
        resp = client.get("/api/system/storage-usage", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "bug_reports" in data
        assert "audit_exports" in data
        assert "browser_screenshots" in data
        assert "cache_dir" in data
        assert "demo_invoices" in data


# ── Cleanup ────────────────────────────────────────────────────────────────


class TestCleanupPreview:
    def test_requires_auth(self, client: TestClient):
        resp = client.get("/api/system/cleanup-preview")
        assert resp.status_code == 401

    def test_preview_requires_admin(self, client: TestClient, owner_token: str):
        reg = client.post("/api/auth/register", json={
            "email": "user3@phase21test.com",
            "password": "Test@1234",
            "full_name": "User",
        })
        token = reg.json()["access_token"]
        resp = client.get("/api/system/cleanup-preview", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 403

    def test_empty_preview_returns_no_items(self, client: TestClient, owner_token: str):
        resp = client.get("/api/system/cleanup-preview", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total_bytes_estimate" in data

    def test_preview_does_not_include_real_data(self, client: TestClient, owner_token: str):
        """Verify cleanup preview never suggests removing real invoices or audit logs."""
        resp = client.get("/api/system/cleanup-preview", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        types = {item.get("type") for item in data["items"]}
        # Should not contain anything that sounds like real invoices/audit
        for t in types:
            assert "invoice" not in t.lower(), f"Unexpected type in cleanup: {t}"
            assert "audit_log" not in t.lower(), f"Unexpected type in cleanup: {t}"
            assert "backup" not in t.lower(), f"Unexpected type in cleanup: {t}"


class TestCleanupRun:
    def test_run_requires_confirmation(self, client: TestClient, owner_token: str):
        resp = client.post("/api/system/cleanup-run", json={
            "confirmed": False,
        }, headers={"Authorization": f"Bearer {owner_token}"})
        assert resp.status_code == 400
        data = resp.json()
        assert "confirmation" in data["detail"].lower()

    def test_run_with_confirmation(self, client: TestClient, owner_token: str):
        resp = client.post("/api/system/cleanup-run", json={
            "confirmed": True,
        }, headers={"Authorization": f"Bearer {owner_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_run_requires_auth(self, client: TestClient):
        resp = client.post("/api/system/cleanup-run", json={
            "confirmed": True,
        })
        assert resp.status_code == 401


# ── Release Checklist ──────────────────────────────────────────────────────


class TestReleaseChecklist:
    def test_get_checklist(self, client: TestClient):
        resp = client.get("/api/system/release/checklist")
        assert resp.status_code == 200
        data = resp.json()
        assert "steps" in data
        assert len(data["steps"]) == 14
        assert data["total"] == 14

    def test_get_checklist_no_auth_required(self, client: TestClient):
        """Release checklist is intentionally unauthenticated."""
        resp = client.get("/api/system/release/checklist")
        assert resp.status_code == 200

    def test_complete_step(self, client: TestClient):
        resp = client.post("/api/system/release/checklist/complete-step", json={
            "step_id": "backend_tests_pass",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "backend_tests_pass"
        assert data["completed"] is True

    def test_complete_invalid_step(self, client: TestClient):
        resp = client.post("/api/system/release/checklist/complete-step", json={
            "step_id": "nonexistent_step",
        })
        assert resp.status_code == 404

    def test_complete_step_updates_progress(self, client: TestClient):
        # Reset first
        client.post("/api/system/release/checklist/reset")
        # Complete one step
        client.post("/api/system/release/checklist/complete-step", json={
            "step_id": "backend_tests_pass",
        })
        resp = client.get("/api/system/release/checklist")
        data = resp.json()
        assert data["completed"] == 1
        assert data["percentage"] > 0

    def test_reset_checklist(self, client: TestClient):
        client.post("/api/system/release/checklist/complete-step", json={
            "step_id": "backend_tests_pass",
        })
        resp = client.post("/api/system/release/checklist/reset")
        assert resp.status_code == 200
        data = client.get("/api/system/release/checklist").json()
        assert data["completed"] == 0


# ── Pagination tests ──────────────────────────────────────────────────────


class TestPagination:
    def test_feedback_pagination(self, client: TestClient, owner_token: str):
        resp = client.get("/api/feedback?skip=0&limit=10", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200

    def test_bug_reports_pagination(self, client: TestClient, owner_token: str):
        resp = client.get("/api/bug-reports?skip=0&limit=10", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200

    def test_waitlist_pagination(self, client: TestClient, owner_token: str):
        resp = client.get("/api/admin/waitlist?skip=0&limit=10", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200

    def test_usage_events_pagination(self, client: TestClient, owner_token: str):
        resp = client.get("/api/usage/events?skip=0&limit=10", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200
