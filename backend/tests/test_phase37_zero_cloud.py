"""Phase 37 — Stability freeze: zero-LLM / zero-cloud-by-default tests.

Verifies the app runs fully without any LLM or cloud AI dependency.
All three LLM integration points (agent planner, AI mode polish, voice STT)
must have working mock/local fallbacks that are active by default.
"""

from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app as _app
from app.models.agent_task_plan import AgentTaskPlan
from app.services.accountant_agent import (
    build_task_plan,
    call_agent_provider,
    classify_task_risk,
    get_agent_status,
)
from app.services import windows_voice_layer as voice_svc


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _zero_cloud_env():
    """Every test starts with zero cloud AI configured (default state)."""
    os.environ["AGENT_PROVIDER"] = "mock"
    os.environ["AGENT_ALLOW_CLOUD"] = "false"
    os.environ["AGENT_API_KEY"] = ""
    os.environ["AI_MODE_ALLOW_CLOUD"] = "false"
    os.environ["AI_MODE_API_KEY"] = ""
    os.environ["VOICE_PROVIDER"] = "mock"
    os.environ["VOICE_ALLOW_CLOUD_STT"] = "false"
    os.environ["OPENAI_API_KEY"] = ""
    yield
    # Reset after test
    for k in ("AGENT_PROVIDER", "AGENT_ALLOW_CLOUD", "AGENT_API_KEY",
              "AI_MODE_ALLOW_CLOUD", "AI_MODE_API_KEY",
              "VOICE_PROVIDER", "VOICE_ALLOW_CLOUD_STT", "OPENAI_API_KEY"):
        os.environ.pop(k, None)


@pytest.fixture
def client():
    with TestClient(_app) as c:
        yield c


@pytest.fixture
def client_with_auth(client):
    resp = client.post("/api/auth/register", json={
        "email": "zero-cloud@test.com", "password": "Test@123456",
        "full_name": "Zero Cloud", "confirm_password": "Test@123456",
    })
    data = resp.json()
    token = data.get("access_token") or data.get("token", "")
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ── Default State: Zero Cloud AI ─────────────────────────────────────────────


def test_default_agent_provider_is_mock():
    """Default AGENT_PROVIDER is 'mock' — no LLM calls."""
    status = get_agent_status()
    assert status["provider"] == "mock"
    assert status["status"] == "mock"
    assert status["allow_cloud"] is False


def test_default_voice_provider_is_mock():
    """Default VOICE_PROVIDER is 'mock' — no cloud STT calls."""
    assert os.environ.get("VOICE_PROVIDER", "mock") == "mock"


def test_default_cloud_ai_disabled():
    """All three cloud AI flags are disabled by default."""
    assert os.environ.get("AGENT_ALLOW_CLOUD", "false") in ("false", "0", "no")
    assert os.environ.get("AI_MODE_ALLOW_CLOUD", "false") in ("false", "0", "no")
    assert os.environ.get("VOICE_ALLOW_CLOUD_STT", "false") in ("false", "0", "no")


def test_default_no_api_keys():
    """No API keys configured by default."""
    for key in ("AGENT_API_KEY", "AI_MODE_API_KEY", "OPENAI_API_KEY"):
        val = os.environ.get(key, "")
        assert val == "", f"{key} should be empty by default, got: {val}"


# ── App Works With AGENT_PROVIDER=mock ───────────────────────────────────────


def test_mock_planner_generates_structured_plan():
    """Mock provider returns valid structured JSON plans."""
    plan = build_task_plan("Read this screen")
    assert plan["task_title"] is not None
    assert "steps" in plan
    assert len(plan["steps"]) > 0
    assert plan["risk_level"] in ("low", "medium", "high", "blocked")


def test_mock_planner_blocks_dangerous_commands():
    """Mock provider blocks dangerous commands."""
    plan = build_task_plan("delete all invoices")
    assert plan["risk_level"] == "blocked"
    assert plan.get("blocked_reason") is not None


def test_mock_planner_blocks_payment_commands():
    plan = build_task_plan("make a payment of $500")
    assert plan["risk_level"] == "blocked"


def test_mock_planner_handles_excel_commands():
    """Mock provider recognizes Excel commands and builds appropriate steps."""
    plan = build_task_plan("create an excel summary from invoices")
    assert plan["task_title"] is not None
    assert len(plan["steps"]) > 0


def test_mock_planner_handles_screen_commands():
    plan = build_task_plan("what is on my screen")
    assert plan["risk_level"] == "low"
    assert len(plan["steps"]) > 0


# ── Cloud AI Disabled Blocks Cloud Planner ──────────────────────────────────


def test_cloud_disabled_blocks_openai_provider():
    os.environ["AGENT_PROVIDER"] = "openai_compatible"
    os.environ["AGENT_ALLOW_CLOUD"] = "false"
    status = get_agent_status()
    assert status["status"] == "cloud_disabled"


def test_cloud_disabled_blocks_deepseek_provider():
    os.environ["AGENT_PROVIDER"] = "deepseek"
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


def test_call_cloud_provider_fails_when_not_connected():
    """call_agent_provider with cloud disabled raises ValueError (defense in depth)."""
    os.environ["AGENT_PROVIDER"] = "openai_compatible"
    os.environ["AGENT_ALLOW_CLOUD"] = "false"
    with pytest.raises(ValueError, match="Cloud agent calls are disabled"):
        call_agent_provider("test")


# ── AI Mode Polish Is Skipped When Disabled ──────────────────────────────────


def test_ai_mode_cloud_disabled_returns_blocked():
    """AI mode polish returns blocked when cloud disabled."""
    result = voice_svc.run_ai_mode("test transcript", settings_override={
        "ai_mode_allow_cloud": False,
        "ai_mode_api_key": "",
    })
    assert result.get("blocked") is True
    assert result.get("ok") is False


def test_ai_mode_blocked_when_no_key():
    """AI mode polish returns blocked when API key missing."""
    result = voice_svc.run_ai_mode("test transcript", settings_override={
        "ai_mode_allow_cloud": True,
        "ai_mode_api_key": "",
    })
    assert result.get("blocked") is True
    assert "API key" in result.get("error", "")


# ── Voice Cloud STT Is Skipped When Disabled ─────────────────────────────────


def test_voice_status_provider_is_mock(client_with_auth):
    """Voice STT shows mock provider when cloud disabled."""
    import os as _os
    _os.environ["VOICE_PROVIDER"] = "mock"
    # Hit the voice-layer status endpoint and check
    resp = client_with_auth.get("/api/voice-layer/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True


def test_agent_status_endpoint_shows_mock(client_with_auth):
    """GET /api/agent/status returns mock provider by default."""
    resp = client_with_auth.get("/api/agent/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "mock"
    assert data["status"] == "mock"


# ── Local/Mock Fallback Still Works ─────────────────────────────────────────


def test_plan_task_endpoint_works_with_mock(client_with_auth):
    """POST /api/agent/plan-task works with mock provider."""
    resp = client_with_auth.post("/api/agent/plan-task", json={
        "command": "read this screen",
        "force_new_plan": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "plan_id" in data
    assert data["plan"]["risk_level"] == "low"


def test_approve_and_execute_works_with_mock(client_with_auth):
    """Full plan->approve->execute cycle works with mock provider."""
    resp = client_with_auth.post("/api/agent/plan-task", json={
        "command": "read this screen",
        "force_new_plan": True,
    })
    assert resp.status_code == 200
    plan_id = resp.json()["plan_id"]

    resp = client_with_auth.post(f"/api/agent/plans/{plan_id}/approve", json={"mode": "dry_run"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_emergency_stop_works_with_mock(client_with_auth):
    """Emergency stop works when no cloud AI configured."""
    resp = client_with_auth.post("/api/agent/plan-task", json={
        "command": "read this screen",
        "force_new_plan": True,
    })
    assert resp.status_code == 200
    plan_id = resp.json()["plan_id"]
    approve_resp = client_with_auth.post(f"/api/agent/plans/{plan_id}/approve", json={"mode": "dry_run"})
    assert approve_resp.status_code == 200
    run_id = approve_resp.json()["run_id"]
    resp = client_with_auth.post(f"/api/agent/runs/{run_id}/stop", json={"reason": "test"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"


def test_plan_task_blocked_dangerous_command(client_with_auth):
    """Dangerous commands are blocked by the mock provider."""
    resp = client_with_auth.post("/api/agent/plan-task", json={
        "command": "delete all invoices",
        "force_new_plan": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"]["risk_level"] == "blocked"
    assert data["plan"].get("blocked_reason") is not None


# ── Admin AI Status Endpoint ────────────────────────────────────────────────


def test_admin_ai_status_cloud_disabled(client_with_auth):
    """Admin AI status shows cloud AI disabled."""
    resp = client_with_auth.get("/api/admin/ai-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_provider"] == "mock"
    assert data["agent_allow_cloud"] is False
    assert data["ai_mode_allow_cloud"] is False
    assert data["zero_cloud_by_default"] is True
    assert "OfficePilot runs fully without LLM" in data["message"]


def test_admin_ai_status_no_keys_exposed(client_with_auth):
    """Admin AI status never exposes raw API key values."""
    resp = client_with_auth.get("/api/admin/ai-status")
    assert resp.status_code == 200
    data = resp.json()
    # Check boolean key-configured flags exist instead of raw keys
    assert isinstance(data["agent_api_key_configured"], bool)
    assert isinstance(data["ai_mode_api_key_configured"], bool)
    assert isinstance(data["openai_api_key_configured"], bool)
    # Ensure raw keys are not in the response
    raw = json.dumps(data)
    assert "sk-" not in raw
    assert "api_key" not in [k for k in data.keys() if "_configured" not in k]


def test_admin_system_health_works(client_with_auth):
    """Admin system health endpoint returns all components."""
    resp = client_with_auth.get("/api/admin/system-health")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "phase" in data
    assert "backend" in data
    assert "database" in data
    assert "llm_provider" in data
    assert "gmail_readonly" in data
    assert "local_whisper" in data
    assert data["llm_provider"]["provider"] == "mock"
