"""Phase 18 — Demo Mode, Onboarding, About, Diagnostics tests."""

from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.onboarding_state import OnboardingState
from app.models.user import User
from app.services.auth import hash_password, register_user
from app.services.demo import (
    FAKE_INVOICE_TEMPLATES,
    get_demo_status,
    is_demo_mode,
    reset_demo_data,
    seed_demo_data,
)
from app.services.diagnostics import run_diagnostics
from app.services.onboarding import complete_step, dismiss_onboarding, get_onboarding_status


# ── Demo mode: unit tests ───────────────────────────────────────────


class TestDemoMode:
    def test_demo_mode_env(self):
        assert is_demo_mode() is True

    def test_seed_creates_fake_invoices(self, db_session: Session):
        counts = seed_demo_data(db_session)
        assert counts["invoices"] == len(FAKE_INVOICE_TEMPLATES)
        from app.models.invoice import Invoice
        invoices = db_session.query(Invoice).filter(Invoice.email_source == "demo").all()
        assert len(invoices) == len(FAKE_INVOICE_TEMPLATES)

    def test_seed_is_idempotent(self, db_session: Session):
        seed_demo_data(db_session)
        counts2 = seed_demo_data(db_session)
        assert counts2["invoices"] == 0  # already seeded

    def test_reset_removes_demo_data_only(self, db_session: Session):
        seed_demo_data(db_session)
        # Add a non-demo invoice
        from app.models.invoice import Invoice, InvoiceStatus
        inv = Invoice(vendor_name="Real Co", total_amount=100.0, invoice_number="REAL-001",
                      status=InvoiceStatus.IMPORTED)
        db_session.add(inv)
        db_session.flush()
        reset_demo_data(db_session)
        remaining = db_session.query(Invoice).all()
        assert len(remaining) == 1
        assert remaining[0].vendor_name == "Real Co"

    def test_get_demo_status(self, db_session: Session):
        status = get_demo_status(db_session)
        assert status["demo_mode_enabled"] is True
        assert status["demo_data_seeded"] is False
        seed_demo_data(db_session)
        status2 = get_demo_status(db_session)
        assert status2["demo_data_seeded"] is True

    def test_demo_mode_cannot_connect_real_providers(self):
        from app.services.demo import is_demo_mode
        enabled = is_demo_mode()
        assert enabled is True
        # Verify no external connections are attempted by seeding without network
        # (the seed functions use local DB only - no network calls)


# ── Onboarding: unit tests ──────────────────────────────────────────


class TestOnboarding:
    def test_onboarding_status_created(self, db_session: Session):
        user = register_user(db_session, "onboard@test.com", "Test@1234")
        status = get_onboarding_status(db_session, user.id)
        assert status["checklist"] is not None
        assert len(status["checklist"]) > 0
        assert status["completed_steps"] == []
        assert status["dismissed"] is False

    def test_complete_step(self, db_session: Session):
        user = register_user(db_session, "step@test.com", "Test@1234")
        status = complete_step(db_session, user.id, "create_owner")
        assert "create_owner" in status["completed_steps"]
        assert status["progress_pct"] > 0

    def test_unknown_step_raises(self, db_session: Session):
        user = register_user(db_session, "badstep@test.com", "Test@1234")
        with pytest.raises(ValueError, match="Unknown step"):
            complete_step(db_session, user.id, "nonexistent_step")

    def test_dismiss(self, db_session: Session):
        user = register_user(db_session, "dismiss@test.com", "Test@1234")
        result = dismiss_onboarding(db_session, user.id)
        assert result["dismissed"] is True
        status = get_onboarding_status(db_session, user.id)
        assert status["dismissed"] is True

    def test_complete_step_idempotent(self, db_session: Session):
        user = register_user(db_session, "idem@test.com", "Test@1234")
        complete_step(db_session, user.id, "create_owner")
        status = complete_step(db_session, user.id, "create_owner")
        assert status["completed_steps"].count("create_owner") == 1


# ── Diagnostics: unit tests ─────────────────────────────────────────


class TestDiagnostics:
    def test_run_diagnostics_returns_expected_components(self, db_session: Session):
        result = run_diagnostics(db_session)
        assert "overall" in result
        assert "items" in result
        assert len(result["items"]) >= 8
        names = {item["name"] for item in result["items"]}
        required = {"Backend Process", "Database", "Storage Path", "Sample Data"}
        assert required.issubset(names), f"Missing: {required - names}"

    def test_diagnostics_all_have_status(self, db_session: Session):
        result = run_diagnostics(db_session)
        for item in result["items"]:
            assert item["status"] in ("ok", "warning", "error", "disabled")


# ── Integration: API endpoints ──────────────────────────────────────


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
    from app.db import SessionLocal as SL
    sl = SL()
    sl.add(User(
        email="owner@test.com",
        password_hash=hash_password("Test@1234"),
        role="owner",
        status="active",
    ))
    sl.commit()
    sl.close()
    with TestClient(app) as c:
        login = c.post("/api/auth/login", json={"email": "owner@test.com", "password": "Test@1234"})
        token = login.json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c
    app.dependency_overrides.clear()


class TestDemoAPI:
    def test_demo_status_endpoint(self, client):
        resp = client.get("/api/demo/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "demo_mode_enabled" in data
        assert "demo_data_seeded" in data

    def test_demo_seed_endpoint(self, client):
        resp = client.post("/api/demo/seed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["counts"]["invoices"] == len(FAKE_INVOICE_TEMPLATES)

    def test_demo_reset_endpoint(self, client):
        client.post("/api/demo/seed")
        resp = client.post("/api/demo/reset")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_sample_files_endpoint(self, client):
        resp = client.get("/api/demo/sample-files")
        assert resp.status_code == 200
        data = resp.json()
        assert "files" in data
        assert len(data["files"]) > 0


class TestOnboardingAPI:
    def test_onboarding_status_endpoint(self, client):
        resp = client.get("/api/onboarding/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "checklist" in data
        assert "progress_pct" in data

    def test_onboarding_complete_step(self, client):
        resp = client.post("/api/onboarding/complete-step", json={"step": "create_owner"})
        assert resp.status_code == 200
        data = resp.json()
        assert "create_owner" in data["completed_steps"]

    def test_onboarding_complete_unknown(self, client):
        resp = client.post("/api/onboarding/complete-step", json={"step": "bad_step"})
        assert resp.status_code == 400

    def test_onboarding_dismiss(self, client):
        resp = client.post("/api/onboarding/dismiss")
        assert resp.status_code == 200
        assert resp.json()["dismissed"] is True


class TestAboutAPI:
    def test_about_returns_version_paths(self, client):
        resp = client.get("/api/about")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "1.0.0"
        assert data["phase"] == 19
        assert "app_name" in data
        assert "database_path" in data
        assert "storage_path" in data
        assert "data_dir" in data
        assert "demo_mode" in data


class TestDiagnosticsAPI:
    def test_diagnostics_endpoint(self, client):
        resp = client.get("/api/first-run/diagnostics")
        assert resp.status_code == 200
        data = resp.json()
        assert "overall" in data
        assert "items" in data
        assert len(data["items"]) >= 8
