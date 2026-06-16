"""Phase 34C: Gmail read-only safety gate tests.

Tests that email write/modify/delete commands are blocked BEFORE
skill matching, and that allowed read-only email commands still work.
"""

from __future__ import annotations

import os

os.environ["AGENT_PROVIDER"] = "mock"
os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_phase34c.db"
os.environ["DEMO_MODE"] = "true"
os.environ["OFFICEPILOT_GMAIL_ALLOW_REAL"] = "false"

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite:///./test_phase34c.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    yield e
    try:
        Base.metadata.drop_all(bind=e)
    except Exception:
        pass
    e.dispose()
    import gc
    gc.collect()
    # Retry file removal with delay
    import time
    for _ in range(10):
        try:
            os.remove("test_phase34c.db")
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
        "email": "test@example.com",
        "password": "Password123!",
        "name": "Test User",
    })
    if resp.status_code == 200:
        data = resp.json()
        tok = data.get("access_token") or data.get("token")
        if tok:
            return tok
    resp = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "Password123!",
    })
    data = resp.json()
    return data.get("access_token") or data.get("token")


def _plan_task(client, token, command):
    resp = client.post(
        "/api/agent/plan-task",
        json={"command": command, "force_new_plan": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    plan = data.get("plan") or data
    return data, plan


# ── Blocked email commands ──────────────────────────────────────────────────


def test_send_email_blocked(client, user_token):
    data, plan = _plan_task(client, user_token, "send email to vendor")
    assert plan.get("risk_level") == "blocked", f"Expected blocked, got: {plan.get('risk_level')}"
    assert plan.get("blocked_reason") == "email_write_not_supported"
    assert "read-only" in plan.get("task_summary", "")
    assert data.get("type") != "skill_match"


def test_forward_invoice_blocked(client, user_token):
    data, plan = _plan_task(client, user_token, "forward invoice emails")
    assert plan.get("risk_level") == "blocked"
    assert plan.get("blocked_reason") == "email_write_not_supported"


def test_mark_read_blocked(client, user_token):
    data, plan = _plan_task(client, user_token, "mark all invoices as read")
    assert plan.get("risk_level") == "blocked"
    assert plan.get("blocked_reason") == "email_write_not_supported"


def test_move_trash_blocked(client, user_token):
    data, plan = _plan_task(client, user_token, "move all emails to trash")
    assert plan.get("risk_level") == "blocked"
    assert plan.get("blocked_reason") == "email_write_not_supported"


def test_delete_emails_blocked(client, user_token):
    data, plan = _plan_task(client, user_token, "delete all emails")
    assert plan.get("risk_level") == "blocked"


def test_reply_email_blocked(client, user_token):
    data, plan = _plan_task(client, user_token, "reply to invoice email")
    assert plan.get("risk_level") == "blocked"
    assert plan.get("blocked_reason") == "email_write_not_supported"


def test_archive_emails_blocked(client, user_token):
    data, plan = _plan_task(client, user_token, "archive invoice emails")
    assert plan.get("risk_level") == "blocked"
    assert plan.get("blocked_reason") == "email_write_not_supported"


def test_label_emails_blocked(client, user_token):
    data, plan = _plan_task(client, user_token, "label invoice emails")
    assert plan.get("risk_level") == "blocked"
    assert plan.get("blocked_reason") == "email_write_not_supported"


def test_compose_email_blocked(client, user_token):
    data, plan = _plan_task(client, user_token, "compose email to client")
    assert plan.get("risk_level") == "blocked"
    assert plan.get("blocked_reason") == "email_write_not_supported"


def test_unsubscribe_blocked(client, user_token):
    data, plan = _plan_task(client, user_token, "unsubscribe from emails")
    assert plan.get("risk_level") == "blocked"
    assert plan.get("blocked_reason") == "email_write_not_supported"


def test_report_spam_blocked(client, user_token):
    data, plan = _plan_task(client, user_token, "report spam emails")
    assert plan.get("risk_level") == "blocked"
    assert plan.get("blocked_reason") == "email_write_not_supported"


# ── Allowed email commands ───────────────────────────────────────────────────


def test_download_invoice_attachments_allowed(client, user_token):
    data, plan = _plan_task(client, user_token, "download invoice attachments")
    assert plan.get("risk_level") != "blocked"


def test_find_invoice_emails_allowed(client, user_token):
    data, plan = _plan_task(client, user_token, "find invoice emails")
    assert plan.get("risk_level") != "blocked"


def test_search_emails_allowed(client, user_token):
    data, plan = _plan_task(client, user_token, "search emails for invoices")
    assert plan.get("risk_level") != "blocked"


def test_get_today_attachments_allowed(client, user_token):
    data, plan = _plan_task(client, user_token, "get today attachments")
    assert plan.get("risk_level") != "blocked"


# ── Executor safety tests ──────────────────────────────────────────────────


def test_executor_blocks_email_send(client, db_session):
    from app.services.agent_tool_executor import execute_tool
    result = execute_tool("email_send", {"to": "test@test.com"}, "live", db_session, None)
    assert result["status"] == "blocked"
    assert "read-only" in result["message"]


def test_executor_blocks_email_forward(client, db_session):
    from app.services.agent_tool_executor import execute_tool
    result = execute_tool("email_forward", {}, "live", db_session, None)
    assert result["status"] == "blocked"
    assert "read-only" in result["message"]


def test_executor_blocks_email_delete(client, db_session):
    from app.services.agent_tool_executor import execute_tool
    result = execute_tool("email_delete", {}, "live", db_session, None)
    assert result["status"] == "blocked"


def test_executor_blocks_email_move(client, db_session):
    from app.services.agent_tool_executor import execute_tool
    result = execute_tool("email_move", {}, "live", db_session, None)
    assert result["status"] == "blocked"


def test_executor_blocks_email_mark_read(client, db_session):
    from app.services.agent_tool_executor import execute_tool
    result = execute_tool("email_mark_read", {}, "live", db_session, None)
    assert result["status"] == "blocked"


def test_executor_blocks_email_archive(client, db_session):
    from app.services.agent_tool_executor import execute_tool
    result = execute_tool("email_archive", {}, "live", db_session, None)
    assert result["status"] == "blocked"


def test_executor_blocks_email_label(client, db_session):
    from app.services.agent_tool_executor import execute_tool
    result = execute_tool("email_label", {}, "live", db_session, None)
    assert result["status"] == "blocked"


def test_executor_blocks_email_modify(client, db_session):
    from app.services.agent_tool_executor import execute_tool
    result = execute_tool("email_modify", {}, "live", db_session, None)
    assert result["status"] == "blocked"


def test_executor_allows_email_search(client, db_session):
    from app.services.agent_tool_executor import execute_tool
    result = execute_tool("email_search", {"query": "test"}, "dry_run", db_session, None)
    assert result["status"] == "dry_run"


def test_executor_allows_email_connect(client, db_session):
    from app.services.agent_tool_executor import execute_tool
    result = execute_tool("email_connect_gmail", {}, "dry_run", db_session, None)
    assert result["status"] == "dry_run"


# ── Tool registry assertions ────────────────────────────────────────────────


@pytest.mark.parametrize("tool_name", [
    "email_send", "email_forward", "email_delete", "email_move",
    "email_mark_read", "email_modify", "email_archive", "email_label",
])
def test_write_email_tools_not_in_registry(tool_name):
    from app.services.tool_registry import get_tool
    assert get_tool(tool_name) is None, f"Write email tool '{tool_name}' should not exist"


@pytest.mark.parametrize("tool_name", [
    "email_connect_gmail", "email_search", "email_preview_messages",
    "email_download_attachments", "email_save_attachment", "email_disconnect_account",
])
def test_readonly_email_tools_in_registry(tool_name):
    from app.services.tool_registry import get_tool
    assert get_tool(tool_name) is not None, f"Read-only email tool '{tool_name}' should exist"
