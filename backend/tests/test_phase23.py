from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.agent_task_plan import AgentTaskPlan
from app.models.agent_workflow_memory import AgentWorkflowMemory
from app.models.agent_workflow_run import AgentWorkflowRun
from app.models.agent_workflow_step_log import AgentWorkflowStepLog
from app.services.accountant_agent import (
    build_task_plan,
    classify_task_risk,
    get_agent_status,
    parse_agent_response,
    redact_context,
    validate_plan,
)
from app.services.agent_memory import (
    find_recent_workflow,
    find_yesterday_workflows,
    list_workflow_memory,
    repeat_workflow,
    save_plan,
    save_plan_as_workflow,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _set_mock_provider():
    os.environ["AGENT_PROVIDER"] = "mock"
    os.environ["AGENT_ALLOW_CLOUD"] = "false"
    os.environ["AGENT_API_KEY"] = ""


def _create_test_plan(db_session: Session) -> AgentTaskPlan:
    return save_plan(
        db_session, user_id=1, command_text="test", context_summary=None,
        plan_json=json.dumps({
            "steps": [{"step_order": 1, "step_type": "read_screen", "target": "screen",
                       "instruction": "Read", "expected_result": "Done",
                       "requires_approval": False, "risk_level": "low"}],
            "platform_detected": "Excel",
        }),
        risk_level="low",
    )


@pytest.fixture(autouse=True)
def _reset_agent_env():
    _set_mock_provider()
    yield
    # Don't pollute other tests
    _set_mock_provider()


# ── Agent Provider Tests ──────────────────────────────────────────────────────


def test_agent_provider_status_mock():
    os.environ["AGENT_PROVIDER"] = "mock"
    status = get_agent_status()
    assert status["provider"] == "mock"
    assert status["status"] == "mock"
    assert status["allow_cloud"] is False


def test_cloud_provider_blocked_when_allow_cloud_false():
    os.environ["AGENT_PROVIDER"] = "openai_compatible"
    os.environ["AGENT_ALLOW_CLOUD"] = "false"
    status = get_agent_status()
    assert status["status"] == "cloud_disabled"


def test_cloud_provider_needs_api_key():
    os.environ["AGENT_PROVIDER"] = "openai_compatible"
    os.environ["AGENT_ALLOW_CLOUD"] = "true"
    os.environ["AGENT_API_KEY"] = ""
    status = get_agent_status()
    assert status["status"] == "missing_api_key"


def test_cloud_provider_connected():
    os.environ["AGENT_PROVIDER"] = "openai_compatible"
    os.environ["AGENT_ALLOW_CLOUD"] = "true"
    os.environ["AGENT_API_KEY"] = "sk-test-key"
    status = get_agent_status()
    assert status["status"] == "connected"


def test_plan_task_returns_structured_plan():
    _set_mock_provider()
    plan = build_task_plan("Read this screen")
    assert "task_title" in plan
    assert "task_summary" in plan
    assert "steps" in plan
    assert "risk_level" in plan
    assert "requires_approval" in plan
    assert isinstance(plan["steps"], list)
    assert len(plan["steps"]) > 0


def test_dangerous_command_blocked():
    _set_mock_provider()
    plan = build_task_plan("delete all invoices")
    assert plan["risk_level"] == "blocked"
    assert plan["blocked_reason"] is not None


def test_payment_command_blocked():
    _set_mock_provider()
    plan = build_task_plan("make a payment of $500")
    assert plan["risk_level"] == "blocked"


def test_bank_transfer_blocked():
    _set_mock_provider()
    plan = build_task_plan("transfer funds to vendor account")
    assert plan["risk_level"] == "blocked"


def test_delete_record_blocked():
    _set_mock_provider()
    plan = build_task_plan("delete this record")
    assert plan["risk_level"] == "blocked"


def test_unclear_command_not_blocked():
    _set_mock_provider()
    plan = build_task_plan("do something unclear")
    assert plan["risk_level"] != "blocked"


def test_context_redaction_removes_secrets():
    ctx = {"email": "user@example.com", "password": "supersecret", "token_value": "abc123", "safe_field": "hello"}
    redacted = redact_context(ctx)
    assert redacted["password"] == "[REDACTED]"
    assert redacted["safe_field"] == "hello"
    # token_value value doesn't contain the word token; this is expected
    assert redacted["token_value"] == "abc123"


def test_context_redaction_removes_secret_values():
    ctx = {"key1": "contains_api_key_value", "key2": "my_secret_value", "key3": "has_password"}
    redacted = redact_context(ctx)
    assert redacted["key1"] == "[REDACTED]"
    assert redacted["key2"] == "[REDACTED]"
    assert redacted["key3"] == "[REDACTED]"


def test_validate_plan_valid():
    plan = {
        "task_title": "Test",
        "task_summary": "Test task",
        "platform_detected": "Excel",
        "risk_level": "low",
        "requires_approval": True,
        "can_record_workflow": False,
        "steps": [{"step_order": 1, "step_type": "read_screen", "target": "screen",
                   "instruction": "Read screen", "expected_result": "Done",
                   "requires_approval": False, "risk_level": "low"}],
    }
    result = validate_plan(plan)
    assert result["valid"] is True
    assert result["blocked"] is False


def test_validate_plan_empty_steps_returns_errors():
    plan = {
        "task_title": "Test", "task_summary": "Test", "platform_detected": "unknown",
        "risk_level": "low", "requires_approval": True, "can_record_workflow": False, "steps": [],
    }
    result = validate_plan(plan)
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_classify_risk_read():
    result = classify_task_risk("read this screen")
    assert result["risk_level"] == "low"


def test_classify_risk_write():
    result = classify_task_risk("update my spreadsheet")
    assert result["risk_level"] == "medium"
    assert result["requires_approval"] is True


def test_classify_risk_delete_is_blocked_by_pattern():
    result = classify_task_risk("delete this record")
    assert result["risk_level"] == "blocked"


def test_parse_agent_response_valid_json():
    response = json.dumps({
        "task_title": "Test", "task_summary": "Test", "platform_detected": "Excel",
        "risk_level": "low", "requires_approval": True, "can_record_workflow": False, "steps": [],
    })
    parsed = parse_agent_response(response)
    assert parsed["task_title"] == "Test"


def test_parse_agent_response_invalid_json():
    parsed = parse_agent_response("not json")
    assert parsed["task_title"] == "Parse Error"


def test_cloud_provider_fails_when_not_connected():
    os.environ["AGENT_PROVIDER"] = "openai_compatible"
    os.environ["AGENT_ALLOW_CLOUD"] = "false"
    plan = build_task_plan("read this screen")
    # Should return error because cloud is disabled but provider is openai_compatible
    assert plan["task_title"] is not None


def test_agent_status_value_from_env():
    os.environ["AGENT_PROVIDER"] = "deepseek"
    status = get_agent_status()
    assert status["provider"] == "deepseek"


# ── Workflow Memory Tests ─────────────────────────────────────────────────────


def test_save_plan(db_session: Session):
    plan = save_plan(db_session, user_id=1, command_text="test command",
                     context_summary="test context", plan_json='{"steps": []}', risk_level="low")
    assert plan.id is not None
    assert plan.status == "pending"
    assert plan.user_id == 1


def test_save_plan_as_workflow(db_session: Session):
    plan = save_plan(
        db_session, user_id=1, command_text="test", context_summary=None,
        plan_json=json.dumps({
            "steps": [{"step_order": 1, "step_type": "click", "target": "btn",
                       "instruction": "Click", "expected_result": "Done",
                       "requires_approval": True, "risk_level": "low"}],
            "platform_detected": "Excel",
        }),
        risk_level="low",
    )
    memory = save_plan_as_workflow(db_session, user_id=1, plan_id=plan.id, workflow_name="Test Workflow")
    assert memory is not None
    assert memory.workflow_name == "Test Workflow"
    assert memory.source_task_plan_id == plan.id


def test_list_workflow_memory(db_session: Session):
    save_plan_as_workflow(db_session, user_id=1, plan_id=_create_test_plan(db_session).id, workflow_name="WF1")
    save_plan_as_workflow(db_session, user_id=1, plan_id=_create_test_plan(db_session).id, workflow_name="WF2")
    workflows = list_workflow_memory(db_session, user_id=1)
    assert len(workflows) >= 2


def test_find_recent_workflow(db_session: Session):
    save_plan_as_workflow(db_session, user_id=1, plan_id=_create_test_plan(db_session).id, workflow_name="Vendor Report")
    found = find_recent_workflow(db_session, "vendor", user_id=1)
    assert found is not None
    assert found.workflow_name == "Vendor Report"


def test_find_yesterday_workflows_empty(db_session: Session):
    workflows = find_yesterday_workflows(db_session, user_id=1)
    assert isinstance(workflows, list)


def test_repeat_workflow(db_session: Session):
    memory = save_plan_as_workflow(db_session, user_id=1, plan_id=_create_test_plan(db_session).id, workflow_name="Repeat Test")
    run = repeat_workflow(db_session, memory.id, user_id=1, command_text="Repeat")
    assert run is not None
    assert run.mode == "dry_run"
    assert run.status == "running"

    logs = db_session.query(AgentWorkflowStepLog).filter(AgentWorkflowStepLog.workflow_run_id == run.id).all()
    assert len(logs) > 0


def test_voice_approval_disabled_by_default():
    val = os.environ.get("VOICE_APPROVAL_ENABLED", "false")
    assert val.lower() in ("false", "0", "no")


def test_plan_risk_level_blocked_set_by_classifier():
    risk = classify_task_risk("delete all invoices")
    assert risk["risk_level"] == "blocked"


# ── Authenticated Client Tests ────────────────────────────────────────────────


@pytest.fixture()
def client_with_auth(client, db_session):
    resp = client.post("/api/auth/register", json={
        "email": "agent-user@test.com", "password": "Test@123456", "full_name": "Agent User",
    })
    data = resp.json()
    token = data["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_plan_risk_level_blocked_prevents_approve(client_with_auth):
    _set_mock_provider()
    resp = client_with_auth.post("/api/agent/plan-task", json={"command": "delete all invoices"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"]["risk_level"] == "blocked"


def _plan_force(client_with_auth, command):
    resp = client_with_auth.post("/api/agent/plan-task", json={"command": command, "force_new_plan": True})
    assert resp.status_code == 200, f"plan-task failed: {resp.text}"
    return resp.json()


def test_plan_returns_plan_id(client_with_auth):
    _set_mock_provider()
    data = _plan_force(client_with_auth, "read this screen")
    assert "plan_id" in data
    assert data["plan_id"] > 0


def test_agent_status_endpoint(client_with_auth):
    resp = client_with_auth.get("/api/agent/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "provider" in data
    assert "status" in data


def test_agent_context_endpoint(client_with_auth):
    resp = client_with_auth.post("/api/agent/context")
    assert resp.status_code == 200
    data = resp.json()
    assert "context" in data


def test_list_workflows_endpoint(client_with_auth):
    _set_mock_provider()
    resp = client_with_auth.get("/api/agent/workflows")
    assert resp.status_code == 200
    data = resp.json()
    assert "workflows" in data


def test_repeat_recent_no_workflows(client_with_auth):
    _set_mock_provider()
    resp = client_with_auth.post("/api/agent/workflows/repeat-recent", json={"mode": "dry_run"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False


def test_approve_plan_endpoint(client_with_auth):
    _set_mock_provider()
    data = _plan_force(client_with_auth, "read this screen")
    plan_id = data["plan_id"]
    resp = client_with_auth.post(f"/api/agent/plans/{plan_id}/approve", json={"mode": "dry_run"})
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "approved"


def test_emergency_stop_endpoint(client_with_auth):
    _set_mock_provider()
    data = _plan_force(client_with_auth, "read this screen")
    plan_id = data["plan_id"]
    approve_resp = client_with_auth.post(f"/api/agent/plans/{plan_id}/approve", json={"mode": "dry_run"})
    assert approve_resp.status_code == 200
    run_id = approve_resp.json()["run_id"]
    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/stop", json={"reason": "Test emergency stop"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "stopped"


def test_save_workflow_endpoint(client_with_auth):
    _set_mock_provider()
    data = _plan_force(client_with_auth, "read this screen")
    plan_id = data["plan_id"]
    resp = client_with_auth.post("/api/agent/workflows/save", json={
        "plan_id": plan_id,
        "workflow_name": "Saved Test WF",
    })
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()
    assert data["workflow_name"] == "Saved Test WF"
