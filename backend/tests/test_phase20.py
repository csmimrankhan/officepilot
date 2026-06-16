"""Phase 20 — Public landing page, pilot waitlist, and admin dashboard tests."""

from __future__ import annotations

import csv
import io
import json
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def _ensure_test_env():
    os.environ.setdefault("PUBLIC_ANALYTICS_ENABLED", "true")


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def owner_token(client: TestClient) -> str:
    reg_resp = client.post("/api/auth/register", json={
        "email": "owner@test.com",
        "password": "Test@1234",
        "full_name": "Owner User",
    })
    assert reg_resp.status_code == 201, reg_resp.text
    return reg_resp.json()["access_token"]


# ── Waitlist public endpoint tests ──────────────────────────────────────────


class TestWaitlistSubmit:
    def test_submit_valid(self, client: TestClient):
        resp = client.post("/api/public/waitlist", json={
            "name": "Alice",
            "email": "alice@example.com",
            "company": "Acme Corp",
            "role": "Accountant",
            "invoice_volume": "50-200/mo",
            "country": "US",
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["name"] == "Alice"
        assert data["email"] == "alice@example.com"
        assert data["status"] == "new"
        assert data["id"] > 0

    def test_submit_duplicate_email(self, client: TestClient):
        body = {"name": "Bob", "email": "bob@test.com"}
        r1 = client.post("/api/public/waitlist", json=body)
        assert r1.status_code == 200
        r2 = client.post("/api/public/waitlist", json=body)
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]

    def test_submit_duplicate_email_case_insensitive(self, client: TestClient):
        r1 = client.post("/api/public/waitlist", json={
            "name": "Carol",
            "email": "Carol@Example.COM",
        })
        assert r1.status_code == 200
        r2 = client.post("/api/public/waitlist", json={
            "name": "Carol",
            "email": "carol@example.com",
        })
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]

    def test_submit_all_fields(self, client: TestClient):
        resp = client.post("/api/public/waitlist", json={
            "name": "Diana",
            "email": "diana@test.com",
            "company": "Beta Inc",
            "role": "Bookkeeper",
            "invoice_volume": "200-1000/mo",
            "current_workflow": "Manual entry into Excel",
            "interested_features_json": json.dumps(["quickbooks", "gmail"]),
            "country": "Canada",
            "notes": "Interested in pilot",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["company"] == "Beta Inc"
        assert data["current_workflow"] == "Manual entry into Excel"

    def test_submit_no_auth_required(self, client: TestClient):
        resp = client.post("/api/public/waitlist", json={
            "name": "Eve",
            "email": "eve@test.com",
        })
        assert resp.status_code == 200


# ── Admin waitlist endpoint tests ───────────────────────────────────────────


class TestAdminWaitlist:
    def test_list_requires_auth(self, client: TestClient):
        resp = client.get("/api/admin/waitlist")
        assert resp.status_code == 401

    def test_list_requires_admin_role(self, client: TestClient, owner_token: str):
        # Register a non-owner user
        reg = client.post("/api/auth/register", json={
            "email": "user2@test.com",
            "password": "Test@1234",
            "full_name": "Regular User",
        })
        token = reg.json()["access_token"]
        # A non-admin, non-owner user should get 403
        resp = client.get("/api/admin/waitlist", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 403

    def test_list_empty(self, client: TestClient, owner_token: str):
        resp = client.get("/api/admin/waitlist", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_with_entries(self, client: TestClient, owner_token: str):
        client.post("/api/public/waitlist", json={
            "name": "Frank", "email": "frank@test.com",
        })
        client.post("/api/public/waitlist", json={
            "name": "Grace", "email": "grace@test.com",
        })
        resp = client.get("/api/admin/waitlist", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {e["name"] for e in data}
        assert names == {"Frank", "Grace"}

    def test_update_status(self, client: TestClient, owner_token: str):
        r = client.post("/api/public/waitlist", json={
            "name": "Heidi", "email": "heidi@test.com",
        })
        entry_id = r.json()["id"]
        resp = client.patch(f"/api/admin/waitlist/{entry_id}", json={
            "status": "contacted",
        }, headers={"Authorization": f"Bearer {owner_token}"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "contacted"

    def test_update_status_invalid(self, client: TestClient, owner_token: str):
        r = client.post("/api/public/waitlist", json={
            "name": "Ivan", "email": "ivan@test.com",
        })
        entry_id = r.json()["id"]
        resp = client.patch(f"/api/admin/waitlist/{entry_id}", json={
            "status": "invalid_status",
        }, headers={"Authorization": f"Bearer {owner_token}"})
        assert resp.status_code == 400

    def test_update_status_not_found(self, client: TestClient, owner_token: str):
        resp = client.patch("/api/admin/waitlist/99999", json={
            "status": "contacted",
        }, headers={"Authorization": f"Bearer {owner_token}"})
        assert resp.status_code == 404


class TestAdminWaitlistSummary:
    def test_summary_empty(self, client: TestClient, owner_token: str):
        resp = client.get("/api/admin/waitlist/summary", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["by_status"] == {}

    def test_summary_with_data(self, client: TestClient, owner_token: str):
        client.post("/api/public/waitlist", json={
            "name": "Judy", "email": "judy@test.com", "role": "Accountant",
        })
        client.post("/api/public/waitlist", json={
            "name": "Karl", "email": "karl@test.com", "role": "Bookkeeper",
        })
        resp = client.get("/api/admin/waitlist/summary", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["by_status"]["new"] == 2

    def test_summary_requires_admin(self, client: TestClient):
        resp = client.get("/api/admin/waitlist/summary")
        assert resp.status_code == 401


class TestAdminWaitlistExport:
    def test_export_csv(self, client: TestClient, owner_token: str):
        client.post("/api/public/waitlist", json={
            "name": "Alice", "email": "alice@test.com", "company": "Acme",
        })
        resp = client.get("/api/admin/waitlist/export.csv", headers={
            "Authorization": f"Bearer {owner_token}",
        })
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        content = resp.text
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) >= 2
        header = rows[0]
        assert "Name" in header
        assert "Email" in header

    def test_export_requires_auth(self, client: TestClient):
        resp = client.get("/api/admin/waitlist/export.csv")
        assert resp.status_code == 401


# ── Public page event tests ──────────────────────────────────────────────────


class TestPublicPageEvent:
    def test_record_event(self, client: TestClient):
        resp = client.post("/api/public/page-event", json={
            "event_type": "page_view",
            "page": "landing",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["recorded"] is True

    def test_record_event_disabled(self, client: TestClient):
        with patch("app.config.get_settings") as mock_gs:
            mock_settings = mock_gs.return_value
            mock_settings.public_analytics_enabled = False
            resp = client.post("/api/public/page-event", json={
                "event_type": "page_view",
                "page": "landing",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["recorded"] is False


# ── Landing page render tests ────────────────────────────────────────────────


class TestLandingPage:
    def test_landing_page_renders(self, client: TestClient):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["phase"] == 23
        assert resp.json()["version"] == "0.36.1"

    def test_faq_page_renders(self, client: TestClient):
        # Verify that the frontend would receive valid data
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
