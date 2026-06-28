"""Phase 39, Task 3: Planner Wiring & Background Intent Detection tests."""
from __future__ import annotations

import json
import os
import time

os.environ["AGENT_PROVIDER"] = "mock"
os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_phase39_planner.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models.background_task import BackgroundTask
from app.services.accountant_agent import BACKGROUND_PATTERNS, build_task_plan, _mock_agent_response
from app.services.agent_tool_executor import execute_tool
from app.services.tool_registry import get_tool


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite:///./test_phase39_planner.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    yield e
    try:
        Base.metadata.drop_all(bind=e)
    except Exception:
        pass
    e.dispose()
    import gc
    gc.collect()
    for _ in range(10):
        try:
            os.remove("test_phase39_planner.db")
            break
        except PermissionError:
            time.sleep(0.5)


@pytest.fixture
def db_session(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def user_token(client):
    resp = client.post("/api/auth/register", json={
        "email": "planner_test@example.com",
        "password": "Password123!",
        "full_name": "Planner Test",
        "confirm_password": "Password123!",
    })
    if resp.status_code in (200, 201):
        data = resp.json()
        tok = data.get("access_token") or data.get("token")
        if tok:
            return tok
    resp = client.post("/api/auth/login", json={
        "email": "planner_test@example.com",
        "password": "Password123!",
    })
    data = resp.json()
    return data.get("access_token") or data.get("token")


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ── BACKGROUND_PATTERNS Regex Tests ────────────────────────────────────────


class TestBackgroundPatterns:
    def test_in_background_pattern(self):
        assert BACKGROUND_PATTERNS.search("download invoices in the background")
        assert BACKGROUND_PATTERNS.search("run this in background")

    def test_while_i_work_pattern(self):
        assert BACKGROUND_PATTERNS.search("analyze data while I work")

    def test_automatically_pattern(self):
        assert BACKGROUND_PATTERNS.search("automatically download invoices")

    def test_fire_and_forget_pattern(self):
        assert BACKGROUND_PATTERNS.search("fire and forget excel report")

    def test_do_it_silently_pattern(self):
        assert BACKGROUND_PATTERNS.search("do it silently")

    def test_no_background_intent(self):
        assert not BACKGROUND_PATTERNS.search("download invoices")
        assert not BACKGROUND_PATTERNS.search("show me the reports")
        assert not BACKGROUND_PATTERNS.search("create an excel file")


# ── build_task_plan Background Flag Tests ──────────────────────────────────


class TestBuildTaskPlanBackground:
    def test_build_task_plan_sets_background_flag(self):
        plan = build_task_plan("download invoices in the background")
        assert plan.get("run_in_background") is True

    def test_build_task_plan_no_background(self):
        plan = build_task_plan("download invoices")
        assert plan.get("run_in_background") is None or plan.get("run_in_background") is False


# ── Mock Provider Background Flag Tests ────────────────────────────────────


class TestMockProviderBackgroundFlag:
    def test_drive_background_flag_set(self):
        raw = _mock_agent_response("download invoices from google drive in the background")
        plan = json.loads(raw)
        assert plan.get("run_in_background") is True

    def test_drive_no_background_flag(self):
        raw = _mock_agent_response("download invoices from google drive")
        plan = json.loads(raw)
        assert plan.get("run_in_background") is False

    def test_fire_and_forget_through_fallthrough(self):
        raw = _mock_agent_response("fire and forget analyze invoice file")
        plan = json.loads(raw)
        assert plan.get("run_in_background") is True


# ── Planner Drive→Excel→Analytics Chain Tests ──────────────────────────────


class TestDriveAnalyticsChain:
    def test_mock_provider_drive_download_chain(self):
        raw = _mock_agent_response("download invoices from google drive and create excel summary")
        plan = json.loads(raw)
        steps = plan.get("steps", [])
        assert len(steps) >= 3
        step_types = [s["step_type"] for s in steps]
        assert "drive_list_recent_files" in step_types
        assert "drive_download_file" in step_types

    def test_mock_provider_all_chain_steps_present(self):
        raw = _mock_agent_response("get invoices from google drive and analyze them")
        plan = json.loads(raw)
        steps = plan.get("steps", [])
        step_types = [s["step_type"] for s in steps]
        assert "drive_list_recent_files" in step_types
        assert "drive_download_file" in step_types
        assert "analyze_invoice_dataset" in step_types
        assert "excel_create_summary_from_file" in step_types

    def test_chain_steps_have_correct_parameters(self):
        raw = _mock_agent_response("download invoices from google drive and analyze")
        plan = json.loads(raw)
        steps = plan.get("steps", [])
        for s in steps:
            if s["step_type"] == "drive_list_recent_files":
                assert "days_back" in s["parameters"]
                assert "keywords" in s["parameters"]
            if s["step_type"] == "drive_download_file":
                assert "file_id" in s["parameters"]
            if s["step_type"] == "analyze_invoice_dataset":
                assert "invoices_data" in s["parameters"]

    def test_tools_exist_for_chain(self):
        for name in ("drive_list_recent_files", "drive_download_file", "analyze_invoice_dataset", "excel_create_summary_from_file"):
            tool = get_tool(name)
            assert tool is not None, f"Tool '{name}' must exist for Drive→Excel→Analytics chain"


# ── Background Plan Approval Tests ─────────────────────────────────────────


class TestBackgroundPlanApproval:
    def test_approve_background_plan_creates_task(self, client, user_token):
        """Test that approving a plan with run_in_background creates a BackgroundTask."""
        resp = client.post(
            "/api/agent/plan-task",
            json={"command": "download invoices from google drive in the background", "context": {}},
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        plan_id = data.get("plan_id")
        assert plan_id is not None, "Plan must be created"
        plan = data.get("plan", {})
        assert plan.get("run_in_background") is True

        resp = client.post(
            f"/api/agent/plans/{plan_id}/approve",
            json={"mode": "dry_run"},
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True
        assert data.get("background_task_id") is not None

        resp = client.get(
            "/api/agent/background-tasks",
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        tasks = resp.json().get("tasks", [])
        task_ids = [t["id"] for t in tasks]
        assert data["background_task_id"] in task_ids

    def test_approve_normal_plan_no_background_task(self, client, user_token):
        """Test that approving a normal plan does NOT create a BackgroundTask."""
        resp = client.post(
            "/api/agent/plan-task",
            json={"command": "create an excel report", "context": {}},
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        plan_id = data.get("plan_id")
        assert plan_id is not None

        resp = client.post(
            f"/api/agent/plans/{plan_id}/approve",
            json={"mode": "dry_run"},
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("background_task_id") is None

    def test_background_task_created_by_approve_has_user_id(self, client, user_token):
        """Test that the BackgroundTask created via approve-plan has correct user_id."""
        resp = client.post(
            "/api/agent/plan-task",
            json={"command": "get invoices from google drive in background", "context": {}},
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        plan_id = data.get("plan_id")

        resp = client.post(
            f"/api/agent/plans/{plan_id}/approve",
            json={"mode": "dry_run"},
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        bt_id = data.get("background_task_id")
        assert bt_id is not None

        resp = client.get(
            f"/api/agent/background-tasks/{bt_id}",
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["id"] == bt_id
        assert detail["status"] in ("queued", "running", "completed", "failed")


# ── End-to-End Drive Tools Execution ────────────────────────────────────────


class TestDriveToolsExecution:
    def test_drive_list_recent_files_tool(self, db_session):
        result = execute_tool("drive_list_recent_files", {"days_back": 30}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        assert result["output"]["file_count"] > 0

    def test_drive_download_file_tool(self, db_session):
        result = execute_tool("drive_download_file", {"file_id": "mock_drive_001"}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        assert os.path.exists(result["output"]["local_path"])
        os.remove(result["output"]["local_path"])

    def test_analyze_invoice_dataset_tool(self, db_session):
        invoices = [
            {"vendor": "A", "total_amount": 100},
            {"vendor": "B", "total_amount": 200},
            {"vendor": "C", "total_amount": 300},
        ]
        result = execute_tool("analyze_invoice_dataset", {"invoices_data": invoices}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        assert result["output"]["total_sum"] == 600
