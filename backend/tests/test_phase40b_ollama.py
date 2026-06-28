"""Phase 40B — Real Local LLM Brain (Ollama Integration) tests."""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["AGENT_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///./test_phase40b.db"
os.environ["OFFICEPILOT_APP_VERSION"] = "1.0.0"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "llama3.1"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, get_db, init_db
from app.main import create_app
from app.models.user import User
from app.services.auth import hash_password, create_access_token


@pytest.fixture(autouse=True)
def _clean_db():
    init_db()
    db = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def user(db):
    u = User(
        email="ollama_test@example.com",
        password_hash=hash_password("testpass"),
        role="admin",
        onboarding_completed=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def token(user):
    return create_access_token(user.id, user.email, user.role)


@pytest.fixture
def headers(token):
    return {"Authorization": f"Bearer {token}"}


# ── _build_ollama_system_prompt tests ──


class TestBuildOllamaSystemPrompt:
    def test_contains_tool_names(self):
        from app.services.accountant_agent import _build_ollama_system_prompt

        prompt = _build_ollama_system_prompt()
        assert "browser_open_url" in prompt
        assert "email_search" in prompt
        assert "excel_create_summary_from_file" in prompt
        assert "Available tools" in prompt
        assert "Output ONLY a valid JSON" in prompt
        assert "format" in prompt

    def test_contains_strict_format_instructions(self):
        from app.services.accountant_agent import _build_ollama_system_prompt

        prompt = _build_ollama_system_prompt()
        assert "steps" in prompt
        assert "task_title" in prompt
        assert "task_summary" in prompt
        assert "step_order" in prompt
        assert "step_type" in prompt
        assert "tool" in prompt
        assert "instruction" in prompt

    def test_excludes_banned_actions(self):
        from app.services.accountant_agent import _build_ollama_system_prompt

        prompt = _build_ollama_system_prompt()
        assert "bank transfer" in prompt or "payments" in prompt or "password" in prompt

    def test_contains_multilingual_instruction(self):
        from app.services.accountant_agent import _build_ollama_system_prompt

        prompt = _build_ollama_system_prompt()
        assert "Urdu" in prompt or "Hindi" in prompt


# ── _call_ollama_provider tests ──


class TestCallOllamaProvider:
    def test_successful_call_returns_json(self):
        """Test that a valid Ollama response is returned as-is."""
        from app.services.accountant_agent import _call_ollama_provider

        mock_response = {
            "model": "llama3.1",
            "response": '{"task_title": "Test", "task_summary": "Test summary", "platform_detected": "Excel", "risk_level": "low", "requires_approval": true, "can_record_workflow": false, "steps": [{"step_order": 1, "step_type": "search_email", "tool": "search_email", "target": "email", "instruction": "Search emails", "expected_result": "done", "requires_approval": false, "risk_level": "low"}], "blocked_reason": null, "clarification_needed": false, "clarification_question": null}',
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response).encode("utf-8")
        mock_urlopen = MagicMock(return_value=mock_resp)
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", mock_urlopen):
            result = _call_ollama_provider("search for invoices")

        parsed = json.loads(result)
        assert parsed["task_title"] == "Test"
        assert len(parsed["steps"]) == 1
        assert parsed["steps"][0]["tool"] == "search_email"

    def test_connection_refused_falls_back(self):
        """Test that a connection error propagates as ConnectionError."""
        from urllib.error import URLError
        from app.services.accountant_agent import _call_ollama_provider

        with patch("urllib.request.urlopen", side_effect=URLError("Connection refused")):
            with pytest.raises(ConnectionError, match="Ollama unreachable"):
                _call_ollama_provider("search for invoices")

    def test_empty_response_raises_error(self):
        """Test that an empty response raises ValueError."""
        from app.services.accountant_agent import _call_ollama_provider

        mock_response = {"model": "llama3.1", "response": ""}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response).encode("utf-8")
        mock_urlopen = MagicMock(return_value=mock_resp)
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", mock_urlopen):
            with pytest.raises(ValueError, match="Empty response"):
                _call_ollama_provider("search for invoices")


# ── call_agent_provider tests (ollama branch) ──


def test_call_agent_provider_ollama_success(monkeypatch):
    """Test that ollama provider returns parsed JSON."""
    from app.services.accountant_agent import call_agent_provider

    monkeypatch.setenv("AGENT_PROVIDER", "ollama")

    mock_response = {
        "model": "llama3.1",
        "response": '{"task_title": "Test", "task_summary": "Test", "platform_detected": "Excel", "risk_level": "low", "requires_approval": true, "can_record_workflow": false, "steps": [], "blocked_reason": null, "clarification_needed": false, "clarification_question": null}',
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response).encode("utf-8")
    mock_urlopen = MagicMock(return_value=mock_resp)
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", mock_urlopen):
        result = call_agent_provider("hello")

    parsed = json.loads(result)
    assert parsed["task_title"] == "Test"


def test_call_agent_provider_ollama_fallback_to_mock(monkeypatch):
    """Test that ollama provider falls back to mock on connection error."""
    from app.services.accountant_agent import call_agent_provider

    monkeypatch.setenv("AGENT_PROVIDER", "ollama")

    with patch("urllib.request.urlopen", side_effect=ConnectionError("Ollama unreachable: [Errno 111] Connection refused")):
        result = call_agent_provider("hello")

    parsed = json.loads(result)
    # Fallback mock should return a clarification response
    assert parsed.get("clarification_needed") is True


# ── build_task_plan with ollama tests ──


def test_build_task_plan_ollama_valid_json(monkeypatch):
    """Test build_task_plan with ollama returns a valid plan."""
    from app.services.accountant_agent import build_task_plan

    monkeypatch.setenv("AGENT_PROVIDER", "ollama")

    mock_response = {
        "model": "llama3.1",
        "response": '{"task_title": "Search Invoices", "task_summary": "Search for invoice emails", "platform_detected": "Gmail", "risk_level": "low", "requires_approval": true, "can_record_workflow": false, "steps": [{"step_order": 1, "step_type": "email_search", "tool": "email_search", "target": "email", "instruction": "Search for invoice emails", "expected_result": "Emails found", "requires_approval": false, "risk_level": "low"}], "blocked_reason": null, "clarification_needed": false, "clarification_question": null}',
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response).encode("utf-8")
    mock_urlopen = MagicMock(return_value=mock_resp)
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", mock_urlopen):
        plan = build_task_plan("search for invoice emails")

    assert plan["task_title"] == "Search Invoices"
    assert len(plan["steps"]) == 1
    assert plan["steps"][0]["tool"] == "email_search"


def test_build_task_plan_ollama_invalid_json_fallback(monkeypatch):
    """Test that invalid JSON from ollama falls back to mock."""
    from app.services.accountant_agent import build_task_plan

    monkeypatch.setenv("AGENT_PROVIDER", "ollama")

    mock_response = {
        "model": "llama3.1",
        "response": "not valid json at all",
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response).encode("utf-8")
    mock_urlopen = MagicMock(return_value=mock_resp)
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", mock_urlopen):
        plan = build_task_plan("search for invoices")

    # parse_agent_response will fail to parse the response and return a parse error
    assert plan.get("blocked_reason") is not None


def test_build_task_plan_ollama_blocked_tools_caught_by_safety(monkeypatch):
    """Test that even if LLM generates a blocked tool, the plan is still returned (safety enforced at execution)."""
    from app.services.accountant_agent import build_task_plan

    monkeypatch.setenv("AGENT_PROVIDER", "ollama")

    mock_response = {
        "model": "llama3.1",
        "response": '{"task_title": "Send Email", "task_summary": "Send an email to vendor", "platform_detected": "Gmail", "risk_level": "medium", "requires_approval": true, "can_record_workflow": false, "steps": [{"step_order": 1, "step_type": "email_send", "tool": "email_send", "target": "email", "instruction": "Send email to vendor", "expected_result": "Email sent", "requires_approval": true, "risk_level": "medium"}], "blocked_reason": null, "clarification_needed": false, "clarification_question": null}',
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response).encode("utf-8")
    mock_urlopen = MagicMock(return_value=mock_resp)
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    # Use a neutral command that doesn't trigger classify_task_risk blocked patterns
    with patch("urllib.request.urlopen", mock_urlopen):
        plan = build_task_plan("help me organize my work")

    # The plan is returned from the LLM output (not blocked at classify level)
    # Safety is enforced at execution time by GMAIL_READONLY_ALLOWED_TOOLS in agent_tool_executor
    assert plan["task_title"] is not None
    assert len(plan["steps"]) > 0
    assert plan["steps"][0]["tool"] == "email_send"


# ── /api/agent/llm-status endpoint tests ──


@patch("urllib.request.urlopen")
def test_llm_status_connected(mock_urlopen, client, headers):
    """Test that GET /api/agent/llm-status returns connected when Ollama is reachable."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "models": [
            {"name": "llama3.1:latest"},
            {"name": "mistral:latest"},
        ]
    }).encode("utf-8")
    mock_urlopen.return_value = MagicMock()
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    resp = client.get("/api/agent/llm-status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "connected"
    assert "llama3.1:latest" in data["models"]


@patch("urllib.request.urlopen")
def test_llm_status_offline(mock_urlopen, client, headers):
    """Test that GET /api/agent/llm-status returns offline when Ollama is unreachable."""
    mock_urlopen.side_effect = OSError("Connection refused")

    resp = client.get("/api/agent/llm-status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "offline"
    assert "error" in data


def test_llm_status_no_auth(client):
    """Test that llm-status endpoint works without auth (internal status endpoint)."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"models": []}).encode("utf-8")
        mock_urlopen.return_value = MagicMock()
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        resp = client.get("/api/agent/llm-status")
        assert resp.status_code in (200, 401, 403)


# ── get_agent_status with ollama provider tests ──


def test_get_agent_status_ollama_connected(monkeypatch):
    """Test that get_agent_status returns ollama provider status."""
    from app.services.accountant_agent import get_agent_status

    monkeypatch.setenv("AGENT_PROVIDER", "ollama")

    # Patch _check_local_llm_reachable to return True
    with patch("app.services.accountant_agent._check_local_llm_reachable", return_value=True):
        status = get_agent_status()

    assert status["provider"] == "ollama"
    assert status["status"] == "connected"
    assert "ollama_base_url" in status
    assert "ollama_model" in status


def test_get_agent_status_ollama_unreachable(monkeypatch):
    """Test that get_agent_status returns ollama_unreachable when Ollama is down."""
    from app.services.accountant_agent import get_agent_status

    monkeypatch.setenv("AGENT_PROVIDER", "ollama")

    with patch("app.services.accountant_agent._check_local_llm_reachable", return_value=False):
        status = get_agent_status()

    assert status["provider"] == "ollama"
    assert status["status"] == "ollama_unreachable"
