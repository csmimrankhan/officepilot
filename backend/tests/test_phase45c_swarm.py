"""Phase 45C — Multi-Agent Swarm Architecture tests."""

from __future__ import annotations

import json
import os

os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["AGENT_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///./test_phase45c_swarm.db"
os.environ["OFFICEPILOT_APP_VERSION"] = "1.0.0"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, init_db
from app.main import app
from app.services.accountant_agent import build_task_plan
from app.services.agent_swarm import (
    SPECIALIST_PROFILES,
    SwarmManager,
    list_agent_profiles,
)
from app.services.tool_registry import TOOL_REGISTRY

FAKE_USER = type("FakeUser", (), {"id": 1, "email": "test@test.com", "role": "admin"})()


@pytest.fixture(autouse=True)
def _clean_db():
    init_db()
    db = SessionLocal()
    try:
        db.execute(Base.metadata.tables["users"].delete())
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield


@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Specialist Profile Structure Tests ────────────────────────────────────────


class TestSpecialistProfiles:
    def test_auditor_profile_exists(self):
        assert "auditor" in SPECIALIST_PROFILES
        profile = SPECIALIST_PROFILES["auditor"]
        assert profile["display_name"] == "Auditor"
        assert "system_prompt_additions" in profile
        assert len(profile["allowed_tools"]) > 0

    def test_tax_profile_exists(self):
        assert "tax" in SPECIALIST_PROFILES
        profile = SPECIALIST_PROFILES["tax"]
        assert profile["display_name"] == "Tax Agent"
        assert len(profile["allowed_tools"]) > 0

    def test_data_entry_profile_exists(self):
        assert "data_entry" in SPECIALIST_PROFILES
        profile = SPECIALIST_PROFILES["data_entry"]
        assert profile["display_name"] == "Data Entry"
        assert len(profile["allowed_tools"]) > 0

    def test_auditor_has_no_write_tools(self):
        profile = SPECIALIST_PROFILES["auditor"]
        write_tools = {"quickbooks_create_bill", "xero_create_bill", "excel_live_edit_active_workbook"}
        for wt in write_tools:
            assert wt not in profile["allowed_tools"], f"Auditor should not have {wt}"

    def test_tax_has_no_write_back_tools(self):
        profile = SPECIALIST_PROFILES["tax"]
        write_back = {"quickbooks_create_bill", "xero_create_bill", "excel_live_edit_active_workbook"}
        for wt in write_back:
            assert wt not in profile["allowed_tools"], f"Tax should not have {wt}"

    def test_data_entry_includes_write_back_tools(self):
        profile = SPECIALIST_PROFILES["data_entry"]
        assert "quickbooks_create_bill" in profile["allowed_tools"]
        assert "xero_create_bill" in profile["allowed_tools"]
        assert "excel_live_edit_active_workbook" in profile["allowed_tools"]

    def test_all_registered_tools_in_registry(self):
        registry_names = {t.name for t in TOOL_REGISTRY}
        for key, profile in SPECIALIST_PROFILES.items():
            for tool_name in profile["allowed_tools"]:
                assert tool_name in registry_names, f"{tool_name} in {key} profile but not in TOOL_REGISTRY"

    def test_list_agent_profiles(self):
        profiles = list_agent_profiles()
        assert "auditor" in profiles
        assert "tax" in profiles
        assert "data_entry" in profiles
        for key, info in profiles.items():
            assert "display_name" in info
            assert "color" in info
            assert "icon" in info
            assert "tool_count" in info


# ── SwarmManager Classification Tests ──────────────────────────────────────────


class TestSwarmManagerClassification:
    def test_routes_audit_keywords(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        assert mgr.classify_and_route("audit my invoices") == "auditor"
        assert mgr.classify_and_route("check for duplicate payments") == "auditor"
        assert mgr.classify_and_route("verify invoice data") == "auditor"
        assert mgr.classify_and_route("find anomalies in the records") == "auditor"

    def test_routes_audit_roman_urdu(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        assert mgr.classify_and_route("audit karo") == "auditor"
        assert mgr.classify_and_route("verify karo") == "auditor"

    def test_routes_tax_keywords(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        assert mgr.classify_and_route("categorize my expenses") == "tax"
        assert mgr.classify_and_route("apply tax rules") == "tax"
        assert mgr.classify_and_route("vat classification needed") == "tax"

    def test_routes_tax_correction(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        assert mgr.classify_and_route("correct category for vendor") == "tax"

    def test_routes_data_entry_keywords(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        assert mgr.classify_and_route("push to quickbooks") == "data_entry"
        assert mgr.classify_and_route("create a bill in xero") == "data_entry"
        assert mgr.classify_and_route("live edit the active workbook") == "data_entry"

    def test_routes_general_fallback(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        assert mgr.classify_and_route("what is on my screen") == "general"
        assert mgr.classify_and_route("hello") == "general"

    def test_audit_over_data_entry(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        assert mgr.classify_and_route("audit the quickbooks data") == "auditor"

    def test_write_back_triggers_data_entry(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        assert mgr.classify_and_route("create a bill in quickbooks for tax") == "data_entry"


# ── Profile Tool Filtering Tests ──────────────────────────────────────────────


class TestProfileToolFiltering:
    def test_auditor_profile_filters_high_risk_tools(self):
        profile = SPECIALIST_PROFILES["auditor"]
        allowed = set(profile["allowed_tools"])
        high_risk_tools = {"quickbooks_create_bill", "xero_create_bill", "excel_live_edit_active_workbook"}
        blocked = high_risk_tools & allowed
        assert len(blocked) == 0, f"Auditor blocked tools should be empty, got {blocked}"

    def test_build_task_plan_accepts_agent_profile(self, db):
        profile = SPECIALIST_PROFILES["auditor"]
        plan = build_task_plan(
            "check for duplicate invoices",
            db=db,
            user=FAKE_USER,
            agent_profile={
                "allowed_tools": profile["allowed_tools"],
                "system_prompt_additions": profile["system_prompt_additions"],
            },
        )
        assert plan is not None
        assert isinstance(plan, dict)
        assert "task_title" in plan

    def test_data_entry_profile_includes_write_back(self):
        profile = SPECIALIST_PROFILES["data_entry"]
        assert "quickbooks_create_bill" in profile["allowed_tools"]
        assert "xero_create_bill" in profile["allowed_tools"]

    def test_data_entry_profile_no_duplicates(self):
        profile = SPECIALIST_PROFILES["data_entry"]
        assert len(profile["allowed_tools"]) == len(set(profile["allowed_tools"]))


# ── SwarmManager execute_swarm_task Tests ─────────────────────────────────────


class TestSwarmManagerExecute:
    def test_execute_swarm_task_auditor(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        plan = mgr.execute_swarm_task("audit my invoices for duplicates")
        assert plan["assigned_agent"] == "Auditor"

    def test_execute_swarm_task_tax(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        plan = mgr.execute_swarm_task("categorize my expenses for tax")
        assert plan["assigned_agent"] == "Tax Agent"

    def test_execute_swarm_task_data_entry(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        plan = mgr.execute_swarm_task("create a bill in quickbooks")
        assert plan["assigned_agent"] == "Data Entry"

    def test_execute_swarm_task_general(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        plan = mgr.execute_swarm_task("read my screen")
        assert plan["assigned_agent"] in ("General", "General Agent")

    def test_execute_swarm_task_override_profile(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        plan = mgr.execute_swarm_task("read my screen", agent_profile="auditor")
        assert plan["assigned_agent"] == "Auditor"

    def test_execute_swarm_task_returns_plan(self, db):
        mgr = SwarmManager(db, FAKE_USER)
        plan = mgr.execute_swarm_task("audit my invoices")
        assert "task_title" in plan
        assert "steps" in plan


# ── Router Integration Tests ──────────────────────────────────────────────────


class TestRouterIntegration:
    def test_plan_task_returns_assigned_agent(self, db):
        client = TestClient(app)
        from app.db import get_db

        app.dependency_overrides[get_db] = lambda: db

        from app.models.user import User

        user = User(email="swarm@test.com", password_hash="x", role="admin", onboarding_completed=True)
        db.add(user)
        db.commit()
        db.refresh(user)

        from app.services.auth import create_access_token

        token = create_access_token(user.id, user.email, user.role)
        resp = client.post(
            "/api/agent/plan-task",
            json={"command": "audit my invoices for duplicates"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "assigned_agent" in data
        app.dependency_overrides.clear()
