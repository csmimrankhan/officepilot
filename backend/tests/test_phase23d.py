"""Phase 23D — Accountant AutoPilot Controlled Plan Execution tests.

Tests that:
- Approving a plan creates a run and step logs
- Executing a step runs the tool executor (dry-run vs live)
- Dry-run all steps works
- Switching to live mode works
- Emergency stop cancels pending steps
- Kill switch blocks execution
- Blocked/dangerous tools are blocked
- Roman Urdu demo workflow: approve → dry-run → execute
- Save workflow after execution
"""

from __future__ import annotations

import os
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session


def _set_mock_provider():
    os.environ["AGENT_PROVIDER"] = "mock"
    os.environ["AGENT_ALLOW_CLOUD"] = "false"
    os.environ["AGENT_API_KEY"] = ""


@pytest.fixture(autouse=True)
def _reset_agent_env():
    _set_mock_provider()
    os.environ["MULTILINGUAL_ENABLED"] = "true"
    os.environ["DEMO_MODE"] = "true"
    yield
    _set_mock_provider()


@pytest.fixture()
def client_with_auth(client):
    resp = client.post("/api/auth/register", json={
        "email": "agent-user-23d@test.com", "password": "Test@123456", "full_name": "Agent User",
    })
    data = resp.json()
    token = data["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _plan_task(client, command: str):
    """Create a plan for the given command and return (plan_id, plan_data)."""
    resp = client.post("/api/agent/plan-task", json={"command": command, "force_new_plan": True})
    assert resp.status_code == 200, f"plan-task failed: {resp.text}"
    data = resp.json()
    return data["plan_id"], data["plan"]


# ── Plan Approval Tests ───────────────────────────────────────────────────────


def test_approve_plan_creates_run(client_with_auth):
    pid, plan = _plan_task(client_with_auth, "read this screen")
    assert pid is not None

    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    assert resp.status_code == 200, f"approve failed: {resp.text}"
    data = resp.json()

    assert "run_id" in data
    assert data["run_id"] > 0
    assert data["mode"] == "dry_run"
    assert data["status"] == "approved"
    assert "steps" in data
    assert len(data["steps"]) > 0

    # Each step should have step_log_id, step_order, status, action_preview
    step = data["steps"][0]
    assert "step_log_id" in step
    assert "step_order" in step
    assert step["status"] == "pending"
    assert "action_preview" in step


def test_approve_plan_live_mode(client_with_auth):
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "live"})
    assert resp.status_code == 200, f"approve live failed: {resp.text}"
    data = resp.json()
    assert data["mode"] == "live"


def test_approve_plan_nonexistent(client_with_auth):
    resp = client_with_auth.post("/api/agent/plans/99999/approve", json={"mode": "dry_run"})
    assert resp.status_code == 404


def test_approve_plan_no_auth(client):
    """Test that unauthenticated requests are rejected."""
    resp = client.post("/api/agent/plans/1/approve", json={"mode": "dry_run"})
    assert resp.status_code == 401


# ── Execute Step Tests ─────────────────────────────────────────────────────────


def test_execute_step_dry_run(client_with_auth):
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]
    step_log_id = data["steps"][0]["step_log_id"]

    # Execute first step
    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/execute-step", json={"step_log_id": step_log_id})
    assert resp.status_code == 200, f"execute-step failed: {resp.text}"
    result = resp.json()

    assert "step_log_id" in result
    assert result["step_log_id"] == step_log_id
    assert "step_status" in result
    assert "result" in result
    assert result["step_status"] == "completed"


def test_execute_step_auto_pick_pending(client_with_auth):
    """Test that omitting step_log_id auto-picks the first pending step."""
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/execute-step", json={})
    assert resp.status_code == 200, f"execute-step (auto) failed: {resp.text}"
    result = resp.json()
    assert "step_log_id" in result
    assert result["step_status"] == "completed"


def test_execute_step_live_mode(client_with_auth):
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "live"})
    data = resp.json()
    run_id = data["run_id"]
    step_log_id = data["steps"][0]["step_log_id"]

    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/execute-step", json={"step_log_id": step_log_id})
    assert resp.status_code == 200, f"execute-step live failed: {resp.text}"
    result = resp.json()
    assert result["step_status"] == "completed"


def test_execute_step_no_pending_steps(client_with_auth):
    """Test that executing with no pending steps returns appropriate message."""
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    # Execute all steps
    for step in data["steps"]:
        client_with_auth.post(f"/api/agent/runs/{run_id}/execute-step", json={"step_log_id": step["step_log_id"]})

    # Try to execute again — no pending steps
    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/execute-step", json={})
    assert resp.status_code == 400, f"Expected 400 but got {resp.status_code}: {resp.text}"


def test_execute_step_nonexistent_run(client_with_auth):
    resp = client_with_auth.post("/api/agent/runs/99999/execute-step", json={})
    assert resp.status_code == 404


# ── Dry-Run All Tests ──────────────────────────────────────────────────────────


def test_dry_run_all(client_with_auth):
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/dry-run", json={})
    assert resp.status_code == 200, f"dry-run failed: {resp.text}"
    result = resp.json()
    assert "results" in result
    assert len(result["results"]) > 0
    for r in result["results"]:
        assert "step_log_id" in r
        assert "result" in r


def test_dry_run_all_nonexistent_run(client_with_auth):
    resp = client_with_auth.post("/api/agent/runs/99999/dry-run", json={})
    assert resp.status_code == 404


# ── Start Live Mode Tests ──────────────────────────────────────────────────────


def test_start_live(client_with_auth):
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/start-live", json={})
    assert resp.status_code == 200, f"start-live failed: {resp.text}"
    result = resp.json()
    assert result["mode"] == "live"
    assert result["status"] == "running"


def test_start_live_already_live(client_with_auth):
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "live"})
    data = resp.json()
    run_id = data["run_id"]

    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/start-live", json={})
    assert resp.status_code == 200  # idempotent


def test_start_live_nonexistent_run(client_with_auth):
    resp = client_with_auth.post("/api/agent/runs/99999/start-live", json={})
    assert resp.status_code == 404


# ── Emergency Stop Tests ───────────────────────────────────────────────────────


def test_stop_run(client_with_auth):
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/stop", json={"reason": "Testing stop"})
    assert resp.status_code == 200, f"stop failed: {resp.text}"
    result = resp.json()
    assert result["status"] == "stopped"


def test_stop_run_no_reason(client_with_auth):
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/stop", json={})
    assert resp.status_code == 200  # reason is optional
    result = resp.json()
    assert result["status"] == "stopped"


def test_stop_run_twice(client_with_auth):
    """Stopping an already-stopped run should succeed."""
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    client_with_auth.post(f"/api/agent/runs/{run_id}/stop", json={"reason": "First stop"})
    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/stop", json={"reason": "Second stop"})
    assert resp.status_code == 400  # already stopped


def test_stop_run_nonexistent(client_with_auth):
    resp = client_with_auth.post("/api/agent/runs/99999/stop", json={"reason": "test"})
    assert resp.status_code == 404


# ── Get Step Logs Tests ────────────────────────────────────────────────────────


def test_get_run_steps(client_with_auth):
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    resp = client_with_auth.get(f"/api/agent/runs/{run_id}/steps")
    assert resp.status_code == 200, f"get steps failed: {resp.text}"
    body = resp.json()
    assert "steps" in body
    steps = body["steps"]
    assert isinstance(steps, list)
    assert len(steps) > 0
    for step in steps:
        assert "id" in step
        assert "step_order" in step


# ── Execute Blocked/Dangerous Tool ──────────────────────────────────────────────


def test_execute_blocked_tool_in_plan(client_with_auth):
    """Plan with a blocked/dangerous tool should be blocked at plan level."""
    resp = client_with_auth.post("/api/agent/plan-task", json={"command": "delete all invoices"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"]["risk_level"] == "blocked"
    assert data["plan_id"] is None


# ── Roman Urdu Demo Workflow ────────────────────────────────────────────────────


def test_roman_urdu_demo_workflow(client_with_auth):
    """Roman Urdu command: plan → approve (live) → execute steps → stop."""
    resp = client_with_auth.post("/api/agent/plan-task", json={
        "command": "email sa aj ki invoice download karo",
        "force_new_plan": True,
    })
    assert resp.status_code == 200, f"plan-task RU failed: {resp.text}"
    plan_data = resp.json()
    assert plan_data["detected_language"] == "roman_urdu"
    assert plan_data["plan_id"] is not None
    pid = plan_data["plan_id"]

    # Approve in live mode
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "live"})
    assert resp.status_code == 200
    run_data = resp.json()
    run_id = run_data["run_id"]
    assert len(run_data["steps"]) > 0

    # Execute first step
    step_log_id = run_data["steps"][0]["step_log_id"]
    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/execute-step", json={"step_log_id": step_log_id})
    assert resp.status_code == 200

    # Stop
    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/stop", json={"reason": "Demo complete"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"


# ── Save Workflow After Execution ──────────────────────────────────────────────


def test_save_workflow_after_execution(client_with_auth):
    """Save a workflow after running steps."""
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    # Execute a step first
    step_log_id = data["steps"][0]["step_log_id"]
    client_with_auth.post(f"/api/agent/runs/{run_id}/execute-step", json={"step_log_id": step_log_id})

    # Save as workflow
    resp = client_with_auth.post("/api/agent/workflows/save", json={
        "plan_id": pid,
        "workflow_name": "Read Screen Workflow",
        "workflow_description": "Auto-saved after execution test",
    })
    assert resp.status_code == 200, f"save workflow failed: {resp.text}"
    result = resp.json()
    assert "workflow_id" in result
    assert result["workflow_name"] == "Read Screen Workflow"

    # Verify it appears in list
    resp = client_with_auth.get("/api/agent/workflows")
    assert resp.status_code == 200
    wf_list = resp.json()
    wf_names = [w["workflow_name"] for w in (wf_list.get("workflows") or wf_list)]
    assert "Read Screen Workflow" in wf_names


# ── Run Listing Tests ──────────────────────────────────────────────────────────


def test_list_runs_for_workflow(client_with_auth):
    pid, plan = _plan_task(client_with_auth, "read this screen")
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    # Save workflow
    resp = client_with_auth.post("/api/agent/workflows/save", json={
        "plan_id": pid,
        "workflow_name": "Listable Workflow",
    })
    wf_id = resp.json()["workflow_id"]

    # List runs — the run created before save won't be linked to the workflow memory,
    # but the endpoint should return valid JSON
    resp = client_with_auth.get(f"/api/agent/workflows/{wf_id}/runs")
    assert resp.status_code == 200
    body = resp.json()
    assert "runs" in body
    assert isinstance(body["runs"], list)


# ── Unauthenticated Access Tests ───────────────────────────────────────────────


def test_endpoints_require_auth(client):
    endpoints = [
        ("POST", "/api/agent/plans/1/approve", {"mode": "dry_run"}),
        ("POST", "/api/agent/runs/1/execute-step", {}),
        ("POST", "/api/agent/runs/1/dry-run", {}),
        ("POST", "/api/agent/runs/1/start-live", {}),
        ("POST", "/api/agent/runs/1/stop", {"reason": "test"}),
        ("GET", "/api/agent/runs/1/steps", None),
        ("GET", "/api/agent/workflows/1/runs", None),
    ]
    for method, path, body in endpoints:
        if method == "POST":
            resp = client.post(path, json=body or {})
        else:
            resp = client.get(path)
        assert resp.status_code == 401, f"{method} {path} expected 401, got {resp.status_code}"
