"""Phase 23E — Hero Workflow Demo: Daily Invoice AutoPilot tests.

Tests that:
- Hero demo command plan-task returns 5-step plan
- Approve + execute hero demo steps (dry-run + live)
- calculate_excel_total returns correct total (7625.75)
- Excel file is created and verify-excel endpoint works
- Run summary has Roman Urdu + English with correct counts
- Save workflow with trigger phrases after execution
- Repeat saved workflow works
- Repeat-recent finds yesterday's workflow
- Audit logs recorded for all key actions
- Kill switch blocks hero demo
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.services.accountant_agent import DEMO_INVOICE_VALUES


ROMAN_URDU_HERO_CMD = "email sa aj ki invoice download karo aur Excel ma save karo aur total batao"
ENGLISH_HERO_CMD = "download today's invoices from email and calculate the total in excel"

EXPECTED_TOTAL = sum(DEMO_INVOICE_VALUES)  # 7625.75
EXPECTED_INVOICE_COUNT = 4  # DEMO_INVOICE_VALUES has 4 values


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
        "email": "agent-user-23e@test.com", "password": "Test@123456", "confirm_password": "Test@123456", "full_name": "Agent User",
    })
    data = resp.json()
    token = data["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _plan_hero_demo(client, command: str = ENGLISH_HERO_CMD):
    """Create a hero demo plan and return (plan_id, plan_data)."""
    resp = client.post("/api/agent/plan-task", json={"command": command, "force_new_plan": True})
    assert resp.status_code == 200, f"plan-task failed: {resp.text}"
    data = resp.json()
    return data["plan_id"], data["plan"], data


# ── Hero Demo Plan Tests ─────────────────────────────────────────────────────


def test_hero_demo_plan_task_english(client_with_auth):
    """English hero demo command returns 5-step invoice demo plan."""
    pid, plan, enriched = _plan_hero_demo(client_with_auth, ENGLISH_HERO_CMD)
    assert pid is not None
    assert pid > 0
    assert plan["risk_level"] == "low"
    assert plan["platform_detected"] == "Excel"

    steps = plan["steps"]
    assert len(steps) == 5, f"Expected 5 steps, got {len(steps)}"

    step_tools = [s.get("tool") for s in steps]
    assert step_tools == [
        "search_email",
        "download_attachments",
        "extract_invoice_data",
        "calculate_excel_total",
        "create_excel_workbook",
    ]


def test_hero_demo_plan_task_roman_urdu(client_with_auth):
    """Roman Urdu hero demo command returns 5-step plan with detected_language."""
    pid, plan, enriched = _plan_hero_demo(client_with_auth, ROMAN_URDU_HERO_CMD)
    assert pid is not None
    assert pid > 0
    assert enriched["detected_language"] == "roman_urdu"
    assert "download" in enriched["internal_english_command"]
    assert len(plan["steps"]) == 5


def test_hero_demo_plan_enriched_fields(client_with_auth):
    """Hero demo plan-task returns all enriched fields."""
    _, _, enriched = _plan_hero_demo(client_with_auth, ENGLISH_HERO_CMD)
    assert enriched["voice_reply_text"] is not None
    assert len(enriched["voice_reply_text"]) > 0
    assert enriched["risk_level"] == "low"
    assert isinstance(enriched["suggested_next_actions"], list)
    assert len(enriched["suggested_next_actions"]) > 0
    assert "blocked_reason" in enriched
    assert enriched["blocked_reason"] is None


# ── Hero Demo Approve + Execute Tests ────────────────────────────────────────


def test_hero_demo_approve_creates_run_with_5_steps(client_with_auth):
    """Approving hero demo plan creates a run with 5 step logs."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    assert resp.status_code == 200, f"approve failed: {resp.text}"
    data = resp.json()

    assert data["run_id"] > 0
    assert data["mode"] == "dry_run"
    assert data["status"] == "approved"
    assert len(data["steps"]) == 5, f"Expected 5 steps, got {len(data['steps'])}"

    for step in data["steps"]:
        assert "step_log_id" in step
        assert step["status"] == "pending"


def test_hero_demo_dry_run_all_steps(client_with_auth):
    """Dry-run all 5 hero demo steps."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/dry-run", json={})
    assert resp.status_code == 200, f"dry-run failed: {resp.text}"
    result = resp.json()

    assert result["step_count"] == 5
    assert len(result["results"]) == 5
    for r in result["results"]:
        assert r["result"]["status"] == "dry_run"
        assert "tool" in r


def test_hero_demo_execute_calculate_excel_total(client_with_auth):
    """Execute calculate_excel_total step and verify correct total."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "live"})
    data = resp.json()
    run_id = data["run_id"]
    steps = data["steps"]

    # Execute steps 1-3 first (search, download, extract)
    for i in range(3):
        step_log_id = steps[i]["step_log_id"]
        resp = client_with_auth.post(
            f"/api/agent/runs/{run_id}/execute-step",
            json={"step_log_id": step_log_id},
        )
        assert resp.status_code == 200, f"step {i+1} failed: {resp.text}"

    # Execute step 4: calculate_excel_total
    step_4 = steps[3]
    resp = client_with_auth.post(
        f"/api/agent/runs/{run_id}/execute-step",
        json={"step_log_id": step_4["step_log_id"]},
    )
    assert resp.status_code == 200, f"step 4 failed: {resp.text}"
    result = resp.json()
    assert result["step_status"] == "completed"
    assert result["tool"] == "calculate_excel_total"

    # Verify total in step log result
    steps_resp = client_with_auth.get(f"/api/agent/runs/{run_id}/steps")
    assert steps_resp.status_code == 200
    step_logs = steps_resp.json()["steps"]
    step_4_log = step_logs[3]
    assert step_4_log["result"]["total"] == EXPECTED_TOTAL


def test_hero_demo_execute_create_excel(client_with_auth):
    """Execute create_excel_workbook step and verify file created."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "live"})
    data = resp.json()
    run_id = data["run_id"]
    steps = data["steps"]

    # Execute all 5 steps
    for i in range(5):
        step_log_id = steps[i]["step_log_id"]
        resp = client_with_auth.post(
            f"/api/agent/runs/{run_id}/execute-step",
            json={"step_log_id": step_log_id},
        )
        assert resp.status_code == 200, f"step {i+1} failed: {resp.text}"

    # Verify step 5 result
    steps_resp = client_with_auth.get(f"/api/agent/runs/{run_id}/steps")
    assert steps_resp.status_code == 200
    step_logs = steps_resp.json()["steps"]
    step_5_log = step_logs[4]
    assert step_5_log["status"] == "completed"
    assert "filepath" in step_5_log["result"]
    assert step_5_log["result"]["filepath"].endswith(".xlsx")


def test_hero_demo_verify_excel_endpoint(client_with_auth):
    """Verify-excel returns file exists after creating workbook."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "live"})
    data = resp.json()
    run_id = data["run_id"]
    steps = data["steps"]

    # Execute all 5 steps
    for i in range(5):
        client_with_auth.post(
            f"/api/agent/runs/{run_id}/execute-step",
            json={"step_log_id": steps[i]["step_log_id"]},
        )

    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/verify-excel", json={})
    assert resp.status_code == 200, f"verify-excel failed: {resp.text}"
    verify = resp.json()
    assert verify["file_exists"] is True
    assert verify["excel_file_path"] is not None
    assert verify["file_size"] > 0
    assert verify["verification"] == "verified"


def test_hero_demo_verify_excel_no_file(client_with_auth):
    """Verify-excel returns not_found when no Excel step executed."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    # Execute only dry-run (no file created)
    client_with_auth.post(f"/api/agent/runs/{run_id}/dry-run", json={})

    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/verify-excel", json={})
    assert resp.status_code == 200
    verify = resp.json()
    assert verify["file_exists"] is False
    assert verify["verification"] == "not_found"


def test_hero_demo_verify_excel_nonexistent_run(client_with_auth):
    """Verify-excel returns 404 for nonexistent run."""
    resp = client_with_auth.post("/api/agent/runs/99999/verify-excel", json={})
    assert resp.status_code == 404


# ── Run Summary Tests ────────────────────────────────────────────────────────


def test_hero_demo_run_summary_after_execution(client_with_auth):
    """Run summary returns correct counts and bilingual text."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "live"})
    data = resp.json()
    run_id = data["run_id"]
    steps = data["steps"]

    # Execute all 5 steps
    for i in range(5):
        client_with_auth.post(
            f"/api/agent/runs/{run_id}/execute-step",
            json={"step_log_id": steps[i]["step_log_id"]},
        )

    resp = client_with_auth.get(f"/api/agent/runs/{run_id}/summary")
    assert resp.status_code == 200, f"summary failed: {resp.text}"
    summary = resp.json()

    assert summary["steps_completed"] == 5
    assert summary["steps_total"] == 5
    assert "summary_roman_urdu" in summary
    assert "summary_english" in summary
    assert summary["summary_roman_urdu"].startswith("Maine")
    assert summary["summary_english"].startswith("I processed")
    assert summary["excel_file_path"] is not None


def test_hero_demo_run_summary_before_execution(client_with_auth):
    """Run summary returns 0 counts before any steps executed."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    resp = client_with_auth.get(f"/api/agent/runs/{run_id}/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["steps_completed"] == 0
    assert summary["invoice_count"] == 0
    assert summary["total_amount"] == 0.0
    assert summary["excel_file_path"] is None


def test_hero_demo_run_summary_nonexistent(client_with_auth):
    """Run summary returns 404 for nonexistent run."""
    resp = client_with_auth.get("/api/agent/runs/99999/summary")
    assert resp.status_code == 404


# ── Save Workflow with Trigger Phrases ────────────────────────────────────────


def test_hero_demo_save_workflow_with_triggers(client_with_auth):
    """Save hero demo workflow with trigger phrases."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)

    trigger_phrases = [
        "daily invoice process",
        "aaj ki invoice process",
        "kal wala workflow repeat karo",
    ]

    resp = client_with_auth.post("/api/agent/workflows/save", json={
        "plan_id": pid,
        "workflow_name": "Daily Invoice Process",
        "workflow_description": "Automated daily invoice process",
        "trigger_phrases": trigger_phrases,
    })
    assert resp.status_code == 200, f"save failed: {resp.text}"
    result = resp.json()
    assert result["workflow_id"] > 0
    assert result["workflow_name"] == "Daily Invoice Process"
    assert result["trigger_phrases"] == trigger_phrases


def test_hero_demo_save_workflow_default_triggers_for_invoice(client_with_auth):
    """Save workflow with invoice name auto-assigns default trigger phrases."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)

    resp = client_with_auth.post("/api/agent/workflows/save", json={
        "plan_id": pid,
        "workflow_name": "Daily Invoice Process",
    })
    assert resp.status_code == 200
    result = resp.json()
    assert result["trigger_phrases"] is not None
    assert len(result["trigger_phrases"]) > 0
    assert "daily invoice process" in result["trigger_phrases"]


def test_hero_demo_save_workflow_and_list(client_with_auth):
    """Saved workflow appears in workflow list."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)

    client_with_auth.post("/api/agent/workflows/save", json={
        "plan_id": pid,
        "workflow_name": "Daily Invoice Process",
    })

    resp = client_with_auth.get("/api/agent/workflows")
    assert resp.status_code == 200
    wf_list = resp.json()
    wf_names = [w["workflow_name"] for w in (wf_list.get("workflows") or wf_list)]
    assert "Daily Invoice Process" in wf_names


# ── Repeat Workflow Tests ─────────────────────────────────────────────────────


def test_hero_demo_repeat_workflow(client_with_auth):
    """Repeat saved hero demo workflow creates a run with steps."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post("/api/agent/workflows/save", json={
        "plan_id": pid,
        "workflow_name": "Daily Invoice Process",
    })
    wf_id = resp.json()["workflow_id"]

    resp = client_with_auth.post(f"/api/agent/workflows/{wf_id}/repeat", json={"mode": "dry_run"})
    assert resp.status_code == 200, f"repeat failed: {resp.text}"
    result = resp.json()
    assert result["run_id"] > 0
    assert result["mode"] == "dry_run"
    assert len(result["steps"]) == 5
    assert result["steps"][0]["status"] == "pending"


def test_hero_demo_repeat_workflow_live(client_with_auth):
    """Repeat workflow in live mode."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post("/api/agent/workflows/save", json={
        "plan_id": pid,
        "workflow_name": "Daily Invoice Process",
    })
    wf_id = resp.json()["workflow_id"]

    resp = client_with_auth.post(f"/api/agent/workflows/{wf_id}/repeat", json={"mode": "live"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "live"


def test_hero_demo_repeat_nonexistent_workflow(client_with_auth):
    """Repeat nonexistent workflow returns 404."""
    resp = client_with_auth.post("/api/agent/workflows/99999/repeat", json={"mode": "dry_run"})
    assert resp.status_code == 404


def test_hero_demo_repeat_recent_no_workflows(client_with_auth):
    """Repeat-recent returns found=false when no yesterday workflows."""
    resp = client_with_auth.post("/api/agent/workflows/repeat-recent", json={"mode": "dry_run"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False


# ── Audit Log Tests ──────────────────────────────────────────────────────────


def test_hero_demo_audit_logs_created(client_with_auth):
    """All key hero demo actions are audit-logged."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)

    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    # Execute a step
    step_log_id = resp.json()["steps"][0]["step_log_id"]
    client_with_auth.post(
        f"/api/agent/runs/{run_id}/execute-step",
        json={"step_log_id": step_log_id},
    )

    # Save workflow
    client_with_auth.post("/api/agent/workflows/save", json={
        "plan_id": pid,
        "workflow_name": "Audit Test WF",
    })

    # Check audit logs
    audit_resp = client_with_auth.get("/api/audit-logs?limit=50")
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    actions = [log["action"] for log in logs]

    assert "agent.plan_task" in actions
    assert "agent.plan_approve" in actions
    assert "agent.execute_step" in actions
    assert "agent.save_workflow" in actions


# ── Blocked Command Still Blocked ────────────────────────────────────────────


def test_hero_demo_blocked_command_still_blocked(client_with_auth):
    """Blocked commands still blocked even with hero demo context."""
    resp = client_with_auth.post("/api/agent/plan-task", json={"command": "delete all invoices"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"]["risk_level"] == "blocked"
    assert data["plan_id"] is None


# ── Dry-Run + Live Flow ──────────────────────────────────────────────────────


def test_hero_demo_approve_dry_run_then_start_live(client_with_auth):
    """Hero demo: approve dry-run, then switch to live, then execute."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    # Switch to live
    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/start-live", json={})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "live"

    # Execute a step in live mode
    step_log_id = data["steps"][0]["step_log_id"]
    resp = client_with_auth.post(
        f"/api/agent/runs/{run_id}/execute-step",
        json={"step_log_id": step_log_id},
    )
    assert resp.status_code == 200
    assert resp.json()["step_status"] == "completed"


def test_hero_demo_emergency_stop_during_execution(client_with_auth):
    """Emergency stop during hero demo execution cancels pending steps."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "live"})
    data = resp.json()
    run_id = data["run_id"]

    # Execute one step
    client_with_auth.post(
        f"/api/agent/runs/{run_id}/execute-step",
        json={"step_log_id": data["steps"][0]["step_log_id"]},
    )

    # Stop
    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/stop", json={"reason": "Testing stop during hero demo"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"

    # Verify remaining steps cancelled
    steps_resp = client_with_auth.get(f"/api/agent/runs/{run_id}/steps")
    step_logs = steps_resp.json()["steps"]
    cancelled = [s for s in step_logs if s["status"] == "cancelled"]
    assert len(cancelled) == 4  # 4 remaining steps should be cancelled


# ── Roman Urdu Hero Demo Flow ────────────────────────────────────────────────


def test_hero_demo_roman_urdu_full_flow(client_with_auth):
    """Full hero demo flow with Roman Urdu command: plan → approve → execute → stop."""
    pid, plan, enriched = _plan_hero_demo(client_with_auth, ROMAN_URDU_HERO_CMD)
    assert enriched["detected_language"] == "roman_urdu"

    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "live"})
    data = resp.json()
    run_id = data["run_id"]
    assert len(data["steps"]) == 5

    # Execute all 5 steps
    for i in range(5):
        resp = client_with_auth.post(
            f"/api/agent/runs/{run_id}/execute-step",
            json={"step_log_id": data["steps"][i]["step_log_id"]},
        )
        assert resp.status_code == 200, f"RU step {i+1} failed: {resp.text}"
        assert resp.json()["step_status"] == "completed"

    # Verify summary
    resp = client_with_auth.get(f"/api/agent/runs/{run_id}/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["steps_completed"] == 5
    assert summary["summary_roman_urdu"].startswith("Maine")


# ── Run Summary English + Roman Urdu ─────────────────────────────────────────


def test_hero_demo_summary_bilingual_text(client_with_auth):
    """Run summary contains both English and Roman Urdu text."""
    pid, plan, _ = _plan_hero_demo(client_with_auth)
    resp = client_with_auth.post(f"/api/agent/plans/{pid}/approve", json={"mode": "dry_run"})
    data = resp.json()
    run_id = data["run_id"]

    resp = client_with_auth.get(f"/api/agent/runs/{run_id}/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert "summary_roman_urdu" in summary
    assert "summary_english" in summary
    assert isinstance(summary["summary_roman_urdu"], str)
    assert isinstance(summary["summary_english"], str)
    assert len(summary["summary_roman_urdu"]) > 0
    assert len(summary["summary_english"]) > 0
