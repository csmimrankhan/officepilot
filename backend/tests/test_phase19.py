"""Phase 19 — Pilot Readiness: Demo Walkthrough, Feedback, Bug Reports, Usage Tracking tests."""

from __future__ import annotations

import json
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.services.auth import hash_password, register_user
from app.services.demo_walkthrough import (
    WALKTHROUGH_STEPS,
    complete_step,
    dismiss_walkthrough,
    get_walkthrough_status,
    reset_walkthrough,
    skip_step,
    start_walkthrough,
)
from app.services.feedback import (
    create_feedback,
    get_feedback,
    list_feedback,
    update_feedback,
)
from app.services.bug_report import (
    create_bug_report,
    get_bug_report,
    list_bug_reports,
    redact_text,
)
from app.services.usage_tracking import (
    get_usage_summary,
    is_tracking_enabled,
    list_usage_events,
    record_event,
)
from app.services.pilot_readiness import (
    READINESS_CHECKLIST,
    complete_readiness_step,
    get_readiness_status,
    reset_readiness,
)


# ── Demo Walkthrough: unit tests ─────────────────────────────────────


class TestDemoWalkthrough:
    def test_get_status_creates_new(self, db_session: Session):
        user = register_user(db_session, "walk@test.com", "Test@1234")
        status = get_walkthrough_status(db_session, user.id)
        assert status["status"] == "not_started"
        assert status["current_step"] == 0
        assert status["completed_steps"] == []
        assert status["dismissed"] is False
        assert len(status["steps"]) == len(WALKTHROUGH_STEPS)

    def test_start_walkthrough(self, db_session: Session):
        user = register_user(db_session, "start@test.com", "Test@1234")
        status = start_walkthrough(db_session, user.id)
        assert status["status"] == "in_progress"
        assert status["started_at"] is not None

    def test_complete_step(self, db_session: Session):
        user = register_user(db_session, f"step{uuid.uuid4().hex[:8]}@test.com", "Test@1234")
        start_walkthrough(db_session, user.id)
        status = complete_step(db_session, user.id, "load_demo_data")
        assert "load_demo_data" in status["completed_steps"]
        assert status["progress_pct"] > 0

    def test_complete_all_steps(self, db_session: Session):
        user = register_user(db_session, "all@test.com", "Test@1234")
        start_walkthrough(db_session, user.id)
        for s in WALKTHROUGH_STEPS:
            status = complete_step(db_session, user.id, s["step"])
        assert status["status"] == "completed"
        assert len(status["completed_steps"]) == len(WALKTHROUGH_STEPS)
        assert status["progress_pct"] == 100
        assert status["completed_at"] is not None

    def test_skip_step(self, db_session: Session):
        user = register_user(db_session, "skip@test.com", "Test@1234")
        start_walkthrough(db_session, user.id)
        status = skip_step(db_session, user.id, "load_demo_data")
        assert status["current_step"] > 0
        assert "load_demo_data" not in status["completed_steps"]

    def test_reset(self, db_session: Session):
        user = register_user(db_session, "reset@test.com", "Test@1234")
        start_walkthrough(db_session, user.id)
        complete_step(db_session, user.id, "load_demo_data")
        status = reset_walkthrough(db_session, user.id)
        assert status["status"] == "not_started"
        assert status["current_step"] == 0
        assert status["completed_steps"] == []
        assert status["started_at"] is None

    def test_dismiss(self, db_session: Session):
        user = register_user(db_session, f"dismiss{uuid.uuid4().hex[:8]}@test.com", "Test@1234")
        result = dismiss_walkthrough(db_session, user.id)
        assert result["dismissed"] is True
        status = get_walkthrough_status(db_session, user.id)
        assert status["dismissed"] is True

    def test_complete_step_not_started_raises(self, db_session: Session):
        user = register_user(db_session, "notstarted@test.com", "Test@1234")
        with pytest.raises(ValueError, match="not in progress"):
            complete_step(db_session, user.id, "load_demo_data")

    def test_complete_unknown_step_raises(self, db_session: Session):
        user = register_user(db_session, "badstep@test.com", "Test@1234")
        start_walkthrough(db_session, user.id)
        with pytest.raises(ValueError, match="Unknown step"):
            complete_step(db_session, user.id, "nonexistent_step")


# ── Feedback: unit tests ─────────────────────────────────────────────


class TestFeedback:
    def test_create_feedback(self, db_session: Session):
        user = register_user(db_session, "fb@test.com", "Test@1234")
        fb = create_feedback(
            db_session, user.id,
            feedback_type="missing_feature",
            title="Dark mode",
            message="Would love a dark theme",
            severity="low",
            page_url="/settings",
        )
        assert fb["feedback_type"] == "missing_feature"
        assert fb["title"] == "Dark mode"
        assert fb["severity"] == "low"
        assert fb["page_url"] == "/settings"
        assert fb["status"] == "open"

    def test_create_feedback_invalid_type(self, db_session: Session):
        user = register_user(db_session, "fbinv@test.com", "Test@1234")
        with pytest.raises(ValueError, match="Invalid feedback type"):
            create_feedback(
                db_session, user.id,
                feedback_type="not_a_real_type",
                title="Test",
                message="Test",
            )

    def test_get_feedback(self, db_session: Session):
        user = register_user(db_session, "fbget@test.com", "Test@1234")
        created = create_feedback(db_session, user.id, feedback_type="bug", title="Bug", message="Found a bug")
        fb = get_feedback(db_session, created["id"], user_id=user.id)
        assert fb is not None
        assert fb["id"] == created["id"]
        assert fb["title"] == "Bug"

    def test_get_feedback_not_found(self, db_session: Session):
        fb = get_feedback(db_session, 99999)
        assert fb is None

    def test_list_feedback(self, db_session: Session):
        user = register_user(db_session, "fblist@test.com", "Test@1234")
        create_feedback(db_session, user.id, feedback_type="bug", title="Bug 1", message="First")
        create_feedback(db_session, user.id, feedback_type="bug", title="Bug 2", message="Second")
        items = list_feedback(db_session, user_id=user.id)
        assert len(items) == 2

    def test_update_feedback(self, db_session: Session):
        user = register_user(db_session, "fbupd@test.com", "Test@1234")
        created = create_feedback(db_session, user.id, feedback_type="bug", title="Bug", message="Found a bug")
        updated = update_feedback(db_session, created["id"], user_id=user.id, status="resolved")
        assert updated is not None
        assert updated["status"] == "resolved"

    def test_update_feedback_invalid_status(self, db_session: Session):
        user = register_user(db_session, "fbupd2@test.com", "Test@1234")
        created = create_feedback(db_session, user.id, feedback_type="bug", title="Bug", message="Found a bug")
        with pytest.raises(ValueError, match="Invalid status"):
            update_feedback(db_session, created["id"], user_id=user.id, status="nonexistent")


# ── Bug Reports: unit tests ──────────────────────────────────────────


class TestBugReport:
    def test_create_bug_report(self, db_session: Session):
        user = register_user(db_session, "bug@test.com", "Test@1234")
        br = create_bug_report(
            db_session, user.id,
            title="Crash on startup",
            description="App crashes immediately",
            severity="critical",
            include_readiness=True,
        )
        assert br["title"] == "Crash on startup"
        assert br["severity"] == "critical"
        assert br["include_readiness"] is True
        assert br["status"] == "open"
        assert br["package_path"] is not None
        assert os.path.isdir(br["package_path"])

    def test_get_bug_report(self, db_session: Session):
        user = register_user(db_session, "bugget@test.com", "Test@1234")
        created = create_bug_report(db_session, user.id, title="Test bug", description="Testing")
        br = get_bug_report(db_session, created["id"])
        assert br is not None
        assert br["id"] == created["id"]

    def test_get_bug_report_not_found(self, db_session: Session):
        br = get_bug_report(db_session, 99999)
        assert br is None

    def test_list_bug_reports(self, db_session: Session):
        user = register_user(db_session, "buglist@test.com", "Test@1234")
        create_bug_report(db_session, user.id, title="Bug 1", description="First")
        create_bug_report(db_session, user.id, title="Bug 2", description="Second")
        items = list_bug_reports(db_session, user_id=user.id)
        assert len(items) == 2

    def test_redact_text(self):
        text = "My password=supersecret and email user@example.com and api_key=12345 and token=abcdef"
        redacted = redact_text(text)
        assert "supersecret" not in redacted
        assert "user@example.com" not in redacted
        assert "12345" not in redacted
        assert "abcdef" not in redacted
        assert "[REDACTED]" in redacted


# ── Usage Tracking: unit tests ───────────────────────────────────────


class TestUsageTracking:
    def test_tracking_enabled(self):
        assert is_tracking_enabled() is True

    def test_record_event(self, db_session: Session):
        user = register_user(db_session, "usage@test.com", "Test@1234")
        result = record_event(
            db_session, user.id,
            event_type="invoice_view",
            entity_type="invoice",
            entity_id=1,
            metadata={"source": "demo"},
        )
        assert result is not None
        assert result["event_type"] == "invoice_view"
        assert result["user_id"] == user.id

    def test_get_usage_summary(self, db_session: Session):
        user = register_user(db_session, "usagesum@test.com", "Test@1234")
        record_event(db_session, user.id, event_type="invoice_view")
        record_event(db_session, user.id, event_type="invoice_view")
        record_event(db_session, user.id, event_type="export_excel")
        summary = get_usage_summary(db_session, user_id=user.id, days=30)
        assert summary["tracking_enabled"] is True
        assert summary["events_total"] == 3
        assert summary["by_type"]["invoice_view"] == 2
        assert summary["by_type"]["export_excel"] == 1

    def test_list_usage_events(self, db_session: Session):
        user = register_user(db_session, "usagelist@test.com", "Test@1234")
        record_event(db_session, user.id, event_type="invoice_view")
        record_event(db_session, user.id, event_type="export_excel")
        events = list_usage_events(db_session, user_id=user.id)
        assert len(events) == 2

    def test_record_event_with_metadata(self, db_session: Session):
        user = register_user(db_session, "usagemeta@test.com", "Test@1234")
        result = record_event(
            db_session, user.id,
            event_type="invoice_view",
            metadata={"invoice_id": 42, "source": "manual"},
        )
        assert result is not None
        events = list_usage_events(db_session, user_id=user.id)
        assert len(events) == 1
        assert events[0]["metadata"]["invoice_id"] == 42


# ── Pilot Readiness: unit tests ──────────────────────────────────────


class TestPilotReadiness:
    def test_get_readiness_status(self, db_session: Session):
        user = register_user(db_session, "ready@test.com", "Test@1234")
        status = get_readiness_status(db_session, user.id)
        assert "checklist" in status
        assert len(status["checklist"]) == len(READINESS_CHECKLIST)
        assert status["completed_steps"] == []
        assert status["progress_pct"] == 0
        assert status["ready_for_pilot"] is False

    def test_complete_readiness_step(self, db_session: Session):
        user = register_user(db_session, "ready_step@test.com", "Test@1234")
        status = complete_readiness_step(db_session, user.id, "owner_account_created")
        assert "owner_account_created" in status["completed_steps"]
        assert status["progress_pct"] > 0

    def test_complete_unknown_step_raises(self, db_session: Session):
        user = register_user(db_session, "ready_bad@test.com", "Test@1234")
        with pytest.raises(ValueError, match="Unknown readiness step"):
            complete_readiness_step(db_session, user.id, "nonexistent_step")

    def test_reset_readiness(self, db_session: Session):
        user = register_user(db_session, "ready_reset@test.com", "Test@1234")
        complete_readiness_step(db_session, user.id, "owner_account_created")
        status = reset_readiness(db_session, user.id)
        assert status["completed_steps"] == []
        assert status["progress_pct"] == 0

    def test_complete_step_idempotent(self, db_session: Session):
        user = register_user(db_session, "ready_idem@test.com", "Test@1234")
        complete_readiness_step(db_session, user.id, "owner_account_created")
        status = complete_readiness_step(db_session, user.id, "owner_account_created")
        assert status["completed_steps"].count("owner_account_created") == 1

    def test_ready_for_pilot_when_all_required_done(self, db_session: Session):
        user = register_user(db_session, "ready_done@test.com", "Test@1234")
        required_steps = [s["step"] for s in READINESS_CHECKLIST if not s["optional"]]
        for step in required_steps:
            complete_readiness_step(db_session, user.id, step)
        status = get_readiness_status(db_session, user.id)
        assert status["ready_for_pilot"] is True
        assert status["required_completed"] == status["required_total"]


# ── Integration: API endpoints ───────────────────────────────────────


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


class TestDemoWalkthroughAPI:
    def test_demo_walkthrough_api(self, client):
        resp = client.get("/api/demo/walkthrough")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_started"
        assert len(data["steps"]) == len(WALKTHROUGH_STEPS)

        resp = client.post("/api/demo/walkthrough/start")
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

        resp = client.post("/api/demo/walkthrough/complete-step", json={"step": "load_demo_data"})
        assert resp.status_code == 200
        assert "load_demo_data" in resp.json()["completed_steps"]

        resp = client.post("/api/demo/walkthrough/skip-step", json={"step": "open_sample_invoice"})
        assert resp.status_code == 200
        assert resp.json()["current_step"] >= 1

        resp = client.post("/api/demo/walkthrough/reset")
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_started"

        resp = client.post("/api/demo/walkthrough/dismiss")
        assert resp.status_code == 200
        assert resp.json()["dismissed"] is True


class TestFeedbackAPI:
    def test_feedback_api(self, client):
        resp = client.post("/api/feedback", json={
            "feedback_type": "missing_feature",
            "title": "Dark mode",
            "message": "Would love a dark theme",
            "severity": "low",
        })
        assert resp.status_code == 200
        fb = resp.json()
        assert fb["title"] == "Dark mode"
        fb_id = fb["id"]

        resp = client.get("/api/feedback")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1

        resp = client.get(f"/api/feedback/{fb_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == fb_id

        resp = client.patch(f"/api/feedback/{fb_id}", json={"status": "resolved"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"


class TestBugReportAPI:
    def test_bug_report_api(self, client):
        resp = client.post("/api/bug-reports", json={
            "title": "Crash on export",
            "description": "Export crashes when no invoices exist",
            "severity": "high",
            "include_readiness": True,
        })
        assert resp.status_code == 200
        br = resp.json()
        assert br["title"] == "Crash on export"
        br_id = br["id"]

        resp = client.get("/api/bug-reports")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1

        resp = client.get(f"/api/bug-reports/{br_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == br_id


class TestUsageAPI:
    def test_usage_api(self, client):
        resp = client.post("/api/usage/events", json={
            "event_type": "invoice_view",
            "entity_type": "invoice",
            "entity_id": 1,
            "metadata": {"source": "test"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["tracking_enabled"] is True
        assert data["recorded"] is True

        resp = client.get("/api/usage/summary")
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["tracking_enabled"] is True
        assert summary["events_total"] >= 1

        resp = client.get("/api/usage/events")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 1


class TestPilotReadinessAPI:
    def test_pilot_readiness_api(self, client):
        resp = client.get("/api/pilot/readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert "checklist" in data
        assert data["completed_steps"] == []

        resp = client.post("/api/pilot/readiness/complete-step", json={"step": "owner_account_created"})
        assert resp.status_code == 200
        assert "owner_account_created" in resp.json()["completed_steps"]

        resp = client.post("/api/pilot/readiness/reset")
        assert resp.status_code == 200
        assert resp.json()["completed_steps"] == []
