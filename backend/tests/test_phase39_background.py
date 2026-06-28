"""Phase 39, Task 1: Backend Background Daemon & Analytics Engine tests."""
from __future__ import annotations

import json
import os
import time

os.environ["AGENT_PROVIDER"] = "mock"
os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_phase39.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db, SessionLocal
from app.main import app
from app.models.background_task import BackgroundTask
from app.services.background_runner import BackgroundTaskRunner
from app.services.agent_tool_executor import execute_tool
from app.services.tool_registry import get_tool


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite:///./test_phase39.db", connect_args={"check_same_thread": False})
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
            os.remove("test_phase39.db")
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
    """Try register first, fall back to login (shared module-scoped DB)."""
    resp = client.post("/api/auth/register", json={
        "email": "bg_test@example.com",
        "password": "Password123!",
        "full_name": "BG Test",
        "confirm_password": "Password123!",
    })
    if resp.status_code == 200 or resp.status_code == 201:
        data = resp.json()
        tok = data.get("access_token") or data.get("token")
        if tok:
            return tok
    resp = client.post("/api/auth/login", json={
        "email": "bg_test@example.com",
        "password": "Password123!",
    })
    data = resp.json()
    return data.get("access_token") or data.get("token")


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ── Task CRUD & Status Transitions ──────────────────────────────────────────


class TestBackgroundTaskCRUD:
    def test_create_background_task(self, client, user_token):
        resp = client.post(
            "/api/agent/run-background",
            json={
                "command": "analyze invoices",
                "plan_json": {"steps": []},
            },
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "queued"
        assert data["command"] == "analyze invoices"

    def test_list_background_tasks(self, client, user_token, db_session):
        task = BackgroundTask(
            user_id=1,
            command="test list",
            plan_json=json.dumps({"steps": []}),
            status="completed",
        )
        db_session.add(task)
        db_session.commit()

        resp = client.get(
            "/api/agent/background-tasks",
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tasks"]) >= 1
        commands = [t["command"] for t in data["tasks"]]
        assert "test list" in commands

    def test_get_background_task_detail(self, client, user_token, db_session):
        task = BackgroundTask(
            user_id=1,
            command="test detail",
            plan_json=json.dumps({"steps": [{"tool": "validate_result", "params": {}}]}),
            status="running",
            progress_percent=50,
            current_step_description="validating",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        resp = client.get(
            f"/api/agent/background-tasks/{task.id}",
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == task.id
        assert data["status"] == "running"
        assert data["progress_percent"] == 50
        assert data["current_step_description"] == "validating"

    def test_get_task_not_found(self, client, user_token):
        resp = client.get(
            "/api/agent/background-tasks/99999",
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 404

    def test_get_task_forbidden_other_user(self, client, user_token, db_session):
        task = BackgroundTask(
            user_id=999,
            command="other user task",
            plan_json=json.dumps({"steps": []}),
            status="queued",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        resp = client.get(
            f"/api/agent/background-tasks/{task.id}",
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 403

    def test_cancel_queued_task(self, client, user_token, db_session):
        task = BackgroundTask(
            user_id=1,
            command="cancel me",
            plan_json=json.dumps({"steps": []}),
            status="queued",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        resp = client.post(
            f"/api/agent/background-tasks/{task.id}/cancel",
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cancelled"

    def test_cancel_completed_task_fails(self, client, user_token, db_session):
        task = BackgroundTask(
            user_id=1,
            command="already done",
            plan_json=json.dumps({"steps": []}),
            status="completed",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        resp = client.post(
            f"/api/agent/background-tasks/{task.id}/cancel",
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 400

    def test_cancel_not_found(self, client, user_token):
        resp = client.post(
            "/api/agent/background-tasks/99999/cancel",
            headers=_auth_header(user_token),
        )
        assert resp.status_code == 404


# ── analyze_invoice_dataset Math Logic ─────────────────────────────────────


class TestAnalyzeInvoiceDataset:
    def test_basic_aggregation(self, db_session):
        invoices = [
            {"vendor": "Vendor A", "total_amount": 100, "date": "2026-01-01"},
            {"vendor": "Vendor B", "total_amount": 200, "date": "2026-01-02"},
            {"vendor": "Vendor C", "total_amount": 300, "date": "2026-01-03"},
        ]
        result = execute_tool("analyze_invoice_dataset", {"invoices_data": invoices}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        output = result["output"]
        assert output["total_sum"] == 600
        assert output["invoice_count"] == 3
        assert output["average_amount"] == 200.0
        assert output["largest_amount"] == 300
        assert output["largest_vendor"] == "Vendor C"
        assert output["smallest_amount"] == 100
        assert output["smallest_vendor"] == "Vendor A"

    def test_single_invoice(self, db_session):
        invoices = [
            {"vendor": "Sole Vendor", "total_amount": 450.50, "date": "2026-06-01"},
        ]
        result = execute_tool("analyze_invoice_dataset", {"invoices_data": invoices}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        output = result["output"]
        assert output["total_sum"] == 450.50
        assert output["invoice_count"] == 1
        assert output["average_amount"] == 450.50
        assert output["largest_vendor"] == "Sole Vendor"
        assert output["smallest_vendor"] == "Sole Vendor"

    def test_empty_dataset(self, db_session):
        result = execute_tool("analyze_invoice_dataset", {"invoices_data": []}, mode="live", db=db_session, user=None)
        assert result["status"] == "failed"

    def test_missing_amounts_default_zero(self, db_session):
        invoices = [
            {"vendor": "No Amount"},
            {"vendor": "Has Amount", "total_amount": 100},
        ]
        result = execute_tool("analyze_invoice_dataset", {"invoices_data": invoices}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        output = result["output"]
        assert output["total_sum"] == 100
        assert output["invoice_count"] == 2
        assert output["average_amount"] == 50.0

    def test_negative_amounts(self, db_session):
        invoices = [
            {"vendor": "Refund", "total_amount": -50.0},
            {"vendor": "Charge", "total_amount": 200.0},
        ]
        result = execute_tool("analyze_invoice_dataset", {"invoices_data": invoices}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        output = result["output"]
        assert output["total_sum"] == 150.0
        assert output["smallest_amount"] == -50.0
        assert output["smallest_vendor"] == "Refund"

    def test_legacy_param_name(self, db_session):
        invoices = [
            {"vendor_name": "Legacy Co", "amount": 500},
        ]
        result = execute_tool("analyze_invoice_dataset", {"invoices": invoices}, mode="live", db=db_session, user=None)
        assert result["status"] == "success"
        assert result["output"]["total_sum"] == 500
        assert result["output"]["largest_vendor"] == "Legacy Co"

    def test_tool_registered(self):
        tool = get_tool("analyze_invoice_dataset")
        assert tool is not None
        assert tool.risk_level == "low"
        assert tool.approval_required is False


# ── Background Runner Progress Updates (uses app's own DB) ─────────────────


class TestBackgroundRunner:
    def _wait_for_task(self, task_id: int, timeout: int = 15) -> BackgroundTask:
        """Poll the app's own DB until the task completes or fails."""
        elapsed = 0
        while elapsed < timeout:
            db = SessionLocal()
            try:
                t = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
                if t and t.status in ("completed", "failed"):
                    return t
            finally:
                db.close()
            time.sleep(0.5)
            elapsed += 0.5
        db = SessionLocal()
        try:
            return db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
        finally:
            db.close()

    def test_runner_processes_simple_plan(self):
        db = SessionLocal()
        task = BackgroundTask(
            user_id=1,
            command="simple analyze",
            plan_json=json.dumps({"steps": [
                {"tool": "analyze_invoice_dataset", "params": {"invoices_data": [
                    {"vendor": "A", "total_amount": 100},
                    {"vendor": "B", "total_amount": 200},
                ]}},
            ]}),
            status="queued",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        runner = BackgroundTaskRunner.get_instance()
        runner.start_task(task_id)

        t = self._wait_for_task(task_id)
        assert t is not None
        assert t.status == "completed", f"Expected completed, got {t.status}: {t.error_message}"
        assert t.progress_percent == 100
        assert t.current_step_description == "Completed"
        assert t.result_summary_json is not None
        summary = json.loads(t.result_summary_json)
        assert summary["total_steps"] == 1
        assert summary["completed_steps"] == 1

    def test_runner_marks_failed_on_step_error(self):
        db = SessionLocal()
        task = BackgroundTask(
            user_id=1,
            command="fail test",
            plan_json=json.dumps({"steps": [
                {"tool": "nonexistent_tool_xyz", "params": {}},
            ]}),
            status="queued",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        runner = BackgroundTaskRunner.get_instance()
        runner.start_task(task_id)

        t = self._wait_for_task(task_id)
        assert t is not None
        assert t.status == "failed"
        assert t.error_message is not None

    def test_runner_updates_progress(self):
        steps = []
        for i in range(5):
            steps.append({
                "tool": "analyze_invoice_dataset",
                "params": {"invoices_data": [{"vendor": f"V{i}", "total_amount": i * 100}]},
                "description": f"Analyzing vendor {i}",
            })

        db = SessionLocal()
        task = BackgroundTask(
            user_id=1,
            command="progress test",
            plan_json=json.dumps({"steps": steps}),
            status="queued",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        db.close()

        runner = BackgroundTaskRunner.get_instance()
        runner.start_task(task_id)

        t = self._wait_for_task(task_id, timeout=20)
        assert t is not None
        assert t.status == "completed", f"Expected completed, got {t.status}: {t.error_message}"
        assert t.progress_percent == 100
        summary = json.loads(t.result_summary_json)
        assert summary["total_steps"] == 5
        assert summary["completed_steps"] == 5
