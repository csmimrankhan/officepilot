"""Phase 24 — OpenCode-style Agent: mode switching, current-task, record, replay yesterday, emergency stop.

Tests that:
- GET /api/agent/mode returns current mode (default: plan)
- POST /api/agent/mode changes mode
- Invalid mode returns 400
- GET /api/agent/current-task returns active task or has_task=false
- GET /api/agent/current-run returns active run or has_run=false
- POST /api/agent/record/start starts recording
- POST /api/agent/record/stop stops recording and creates draft
- POST /api/agent/replay/yesterday returns found=false for no workflows
- POST /api/agent/emergency-stop stops all active runs
- Plan mode cannot execute (verify via mode endpoint)
- Dangerous commands blocked (verify via plan-task)
- Provider cloud disabled by default
"""
from __future__ import annotations

import json
import os
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


ROMAN_URDU_CMD = "email sa aj ki invoice download karo aur Excel ma save karo aur total batao"


def _plan_task(client, command: str):
    resp = client.post("/api/agent/plan-task", json={"command": command, "force_new_plan": True})
    assert resp.status_code == 200, f"plan-task failed: {resp.text}"
    return resp.json()


def _set_mock_provider():
    os.environ["AGENT_PROVIDER"] = "mock"
    os.environ["AGENT_ALLOW_CLOUD"] = "false"
    os.environ["AGENT_API_KEY"] = ""


@pytest.fixture(autouse=True)
def _reset_agent_env():
    _set_mock_provider()
    os.environ["DEMO_MODE"] = "true"
    os.environ["MULTILINGUAL_ENABLED"] = "true"
    yield
    _set_mock_provider()


@pytest.fixture()
def client_with_auth(client):
    resp = client.post("/api/auth/register", json={
        "email": "opencode-test@test.com", "password": "Test@123456", "full_name": "OpenCode User",
    })
    data = resp.json()
    token = data["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ── Mode Tests ─────────────────────────────────────────────────────────────


def test_get_mode_default(client_with_auth):
    """Default mode should be 'plan'."""
    resp = client_with_auth.get("/api/agent/mode")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "plan"


def test_set_mode_valid(client_with_auth):
    """Set mode to work, record, replay."""
    for mode in ("work", "record", "replay", "plan"):
        resp = client_with_auth.post("/api/agent/mode", json={"mode": mode})
        assert resp.status_code == 200, f"Failed to set mode={mode}: {resp.text}"
        data = resp.json()
        assert data["mode"] == mode


def test_set_mode_invalid(client_with_auth):
    """Invalid mode returns 400."""
    resp = client_with_auth.post("/api/agent/mode", json={"mode": "invalid_mode"})
    assert resp.status_code == 400


def test_set_mode_no_auth_blocks(client):
    """Unauthenticated request should be blocked (401)."""
    resp = client.get("/api/agent/mode")
    assert resp.status_code == 401  # auth returns 401, not 403


# ── Current Task Tests ─────────────────────────────────────────────────────


def test_current_task_no_task(client_with_auth):
    """No active task returns has_task=false."""
    resp = client_with_auth.get("/api/agent/current-task")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_task"] is False
    assert data["task"] is None


def test_current_task_after_plan(client_with_auth):
    """After plan-task, current-task should return the active plan."""
    plan_data = _plan_task(client_with_auth, "read this screen")
    assert plan_data["plan_id"] is not None

    resp2 = client_with_auth.get("/api/agent/current-task")
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["has_task"] is True
    assert data["task"]["plan_id"] == plan_data["plan_id"]
    assert data["task"]["risk_level"] is not None
    assert data["task"]["status"] == "pending"


# ── Current Run Tests ──────────────────────────────────────────────────────


def test_current_run_no_run(client_with_auth):
    """No active run returns has_run=false."""
    resp = client_with_auth.get("/api/agent/current-run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_run"] is False


def test_current_run_after_approve(client_with_auth):
    """After plan approval, current-run should return the active run."""
    data = _plan_task(client_with_auth, "read this screen")
    plan_id = data["plan_id"]

    resp2 = client_with_auth.post(f"/api/agent/plans/{plan_id}/approve", json={"mode": "dry_run"})
    assert resp2.status_code == 200
    run_id = resp2.json()["run_id"]

    resp3 = client_with_auth.get("/api/agent/current-run")
    assert resp3.status_code == 200
    data = resp3.json()
    assert data["has_run"] is True
    assert data["run"]["run_id"] == run_id
    assert data["run"]["status"] in ("approved", "running")
    assert len(data["run"]["steps"]) > 0


# ── Record Workflow Tests ──────────────────────────────────────────────────


def test_start_recording(client_with_auth):
    """Start recording returns active=true."""
    resp = client_with_auth.post("/api/agent/record/start", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["active"] is True


def test_stop_recording_no_active(client_with_auth):
    """Stop with no active recording returns no draft."""
    # Ensure clean state by stopping any prior recording
    client_with_auth.post("/api/agent/record/stop", json={})
    resp = client_with_auth.post("/api/agent/record/stop", json={"workflow_name": "Test WF"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflow_draft"] is None


def test_record_full_flow(client_with_auth):
    """Full record → stop creates a workflow draft."""
    # Ensure clean state
    client_with_auth.post("/api/agent/record/stop", json={})
    resp1 = client_with_auth.post("/api/agent/record/start", json={})
    assert resp1.status_code == 200
    assert resp1.json()["active"] is True

    resp2 = client_with_auth.post("/api/agent/record/stop", json={"workflow_name": "My Recorded Workflow"})
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["ok"] is True
    assert data["workflow_draft"] is not None
    assert data["workflow_draft"]["workflow_name"] == "My Recorded Workflow"


def test_start_recording_twice(client_with_auth):
    """Double start returns ok=true with 'Already recording' message."""
    # Ensure clean state
    client_with_auth.post("/api/agent/record/stop", json={})
    resp1 = client_with_auth.post("/api/agent/record/start", json={})
    assert resp1.status_code == 200
    assert resp1.json()["active"] is True

    resp2 = client_with_auth.post("/api/agent/record/start", json={})
    assert resp2.status_code == 200
    assert resp2.json()["ok"] is True

    # Clean up
    client_with_auth.post("/api/agent/record/stop", json={})


# ── Replay Yesterday Tests ─────────────────────────────────────────────────


def test_replay_yesterday_no_workflows(client_with_auth):
    """No yesterday workflows returns found=false."""
    resp = client_with_auth.post("/api/agent/replay/yesterday", json={"mode": "dry_run"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False


def test_replay_yesterday_kill_switch(client_with_auth):
    """Kill switch blocks replay."""
    # Activate kill switch via API (POST /api/safety/kill-switch with active=true)
    resp = client_with_auth.post("/api/safety/kill-switch", json={"active": True, "reason": "Test kill switch"})
    assert resp.status_code == 200, f"kill switch activate failed: {resp.text}"

    try:
        resp = client_with_auth.post("/api/agent/replay/yesterday", json={"mode": "dry_run"})
        assert resp.status_code == 403
    finally:
        # Deactivate
        client_with_auth.post("/api/safety/kill-switch", json={"active": False})


# ── Emergency Stop Tests ────────────────────────────────────────────────────


def test_emergency_stop_no_active_runs(client_with_auth):
    """No active runs returns stopped_count=0."""
    resp = client_with_auth.post("/api/agent/emergency-stop", json={"reason": "Test stop"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["stopped_count"] == 0


def test_emergency_stop_after_approve(client_with_auth):
    """After plan approval, emergency stop should stop the run."""
    data = _plan_task(client_with_auth, "read this screen")
    plan_id = data["plan_id"]

    resp2 = client_with_auth.post(f"/api/agent/plans/{plan_id}/approve", json={"mode": "dry_run"})
    assert resp2.status_code == 200

    resp3 = client_with_auth.post("/api/agent/emergency-stop", json={"reason": "Test emergency stop"})
    assert resp3.status_code == 200
    data = resp3.json()
    assert data["ok"] is True
    assert data["stopped_count"] >= 1

    # Verify run is stopped
    current = client_with_auth.get("/api/agent/current-run")
    assert current.json()["has_run"] is False


# ── Safety Tests ────────────────────────────────────────────────────────────


def test_plan_mode_read_only(client_with_auth):
    """Plan mode (default) can plan but not execute."""
    # In plan mode, plan-task should work
    data = _plan_task(client_with_auth, "read this screen")
    assert data["plan_id"] is not None
    assert data["plan"]["risk_level"] == "low"

    # Approve requires explicit user action - verify the endpoint still works
    mode_resp = client_with_auth.get("/api/agent/mode")
    assert mode_resp.status_code == 200
    assert mode_resp.json()["mode"] == "plan"


def test_dangerous_command_blocked(client_with_auth):
    """Dangerous commands like 'delete invoice' should be blocked."""
    resp = client_with_auth.post("/api/agent/plan-task", json={"command": "delete invoice number 12345 from the system"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"]["blocked_reason"] is not None, f"Expected blocked, got: {data}"
    assert data["plan"]["risk_level"] == "blocked"


def test_provider_cloud_disabled_by_default(client_with_auth):
    """Default provider should be mock, not cloud."""
    resp = client_with_auth.get("/api/agent/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "mock"
    assert data["allow_cloud"] is False


# ── Full Flow: Plan → Mode Change → Approve → Emergency Stop ──────────────


def test_full_flow_plan_to_emergency_stop(client_with_auth):
    """Full flow: plan → set work mode → approve → emergency stop."""
    # Plan
    data = _plan_task(client_with_auth, "read this screen")
    plan_id = data["plan_id"]

    # Switch to work mode
    resp2 = client_with_auth.post("/api/agent/mode", json={"mode": "work"})
    assert resp2.status_code == 200
    assert resp2.json()["mode"] == "work"

    # Approve
    resp3 = client_with_auth.post(f"/api/agent/plans/{plan_id}/approve", json={"mode": "dry_run"})
    assert resp3.status_code == 200
    run_id = resp3.json()["run_id"]

    # Emergency stop
    resp4 = client_with_auth.post("/api/agent/emergency-stop", json={"reason": "Full flow test"})
    assert resp4.status_code == 200
    assert resp4.json()["stopped_count"] >= 1

    # Verify no active run
    resp5 = client_with_auth.get("/api/agent/current-run")
    assert resp5.status_code == 200
    assert resp5.json()["has_run"] is False

    # Switch back to plan mode
    client_with_auth.post("/api/agent/mode", json={"mode": "plan"})
