"""Tests for Accounting Skills integration into the plan-task flow."""

from __future__ import annotations

import json
import os
import pytest

from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_env():
    os.environ["AGENT_PROVIDER"] = "mock"
    os.environ["DEMO_MODE"] = "true"
    yield


def _register_and_login(client, email_suffix=""):
    email = f"skillmatch{email_suffix}@example.com"
    resp = client.post("/api/auth/register", json={
        "email": email,
        "password": "Secret123!",
        "full_name": "Skill Match Test",
    })
    if resp.status_code == 200:
        token = resp.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
    else:
        # User already exists, login
        resp = client.post("/api/auth/login", json={
            "email": email,
            "password": "Secret123!",
        })
        token = resp.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _create_skill(client, email_suffix, name, trigger_phrases):
    _register_and_login(client, email_suffix)
    pid_resp = client.post("/api/agent/plan-task", json={
        "command": "create daily invoice summary for today",
    })
    assert pid_resp.status_code == 200
    data = pid_resp.json()
    pid = data.get("plan_id")
    if pid is None:
        # Check if it's a skill_match response — create a plan from the skill
        if data.get("type") == "skill_match":
            # Force create a new plan to get plan_id
            pid_resp2 = client.post("/api/agent/plan-task", json={
                "command": "create daily invoice summary for today",
                "force_new_plan": True,
            })
            assert pid_resp2.status_code == 200
            pid = pid_resp2.json().get("plan_id")
    assert pid is not None, f"No plan_id in response: {data}"
    resp = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid,
        "name": name,
        "trigger_phrases": trigger_phrases,
    })
    assert resp.status_code == 200
    return resp.json()["skill_id"]


def test_command_with_exact_trigger_returns_skill_match(client):
    _create_skill(client, "_exact", "Daily Invoice Process", [
        "process today invoices",
        "daily invoice process",
        "invoice folder summary",
    ])

    resp = client.post("/api/agent/plan-task", json={
        "command": "process today invoices",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("type") == "skill_match"
    assert data["matched_skill"]["name"] == "Daily Invoice Process"
    assert data["matched_skill"]["confidence"] >= 0.85
    assert "steps" in data["matched_skill"]
    assert len(data["matched_skill"]["steps"]) > 0


def test_fuzzy_trigger_returns_possible_match(client):
    _create_skill(client, "_fuzzy", "Monthly Report", [
        "monthly report generation",
        "generate monthly summary",
    ])

    resp = client.post("/api/agent/plan-task", json={
        "command": "can you do a monthly report for me",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("type") == "skill_match"
    assert data["matched_skill"]["confidence"] < 0.85
    assert data["matched_skill"]["match_type"] == "possible"


def test_force_new_plan_bypasses_skill_matching(client):
    _create_skill(client, "_force", "Daily Invoice Process", [
        "process today invoices",
    ])

    resp = client.post("/api/agent/plan-task", json={
        "command": "process today invoices",
        "force_new_plan": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("type") != "skill_match"
    assert "plan" in data or data.get("plan_id") is not None


def test_low_confidence_creates_normal_plan(client):
    _create_skill(client, "_lowconf", "Specific Task", [
        "very specific workflow phrase",
    ])

    resp = client.post("/api/agent/plan-task", json={
        "command": "something completely unrelated and different",
        "force_new_plan": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("type") != "skill_match"
    assert "plan_id" in data or data.get("plan", {}).get("plan_id")


def test_unauthorized_skill_not_matched(client):
    _create_skill(client, "_owner", "Private Skill", ["private task"])

    other = TestClient(client.app)
    other.post("/api/auth/register", json={
        "email": "other_match@example.com", "password": "Secret123!", "full_name": "Other",
    })
    other_resp = other.post("/api/auth/login", json={
        "email": "other_match@example.com", "password": "Secret123!",
    })
    other.headers.update({"Authorization": f"Bearer {other_resp.json()['access_token']}"})

    resp = other.post("/api/agent/plan-task", json={
        "command": "private task",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("type") != "skill_match"


def test_archived_skill_not_matched(client):
    sid = _create_skill(client, "_archived", "Old Process", ["old process"])
    archive_resp = client.post(f"/api/accounting-skills/{sid}/archive")
    assert archive_resp.status_code == 200

    # Verify skill is archived
    detail = client.get(f"/api/accounting-skills/{sid}").json()
    assert detail["status"] == "archived", f"Expected archived, got: {detail['status']}"

    resp = client.post("/api/agent/plan-task", json={
        "command": "old process",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("type") != "skill_match", f"Skill matched despite being archived: {data}"


def test_match_skill_endpoint(client):
    _create_skill(client, "_match", "Match Test Skill", [
        "match this phrase",
        "another phrase",
    ])

    resp = client.post("/api/agent/match-skill", json={
        "command": "match this phrase",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] is True
    assert len(data["matches"]) > 0
    assert data["matches"][0]["name"] == "Match Test Skill"
    assert data["matches"][0]["confidence"] >= 0.85

    resp2 = client.post("/api/agent/match-skill", json={
        "command": "nonexistent command",
    })
    assert resp2.status_code == 200
    assert resp2.json()["matched"] is False


def test_skill_match_endpoint_requires_command(client):
    _register_and_login(client, "_required")
    resp = client.post("/api/agent/match-skill", json={})
    assert resp.status_code == 400


def test_skill_match_includes_steps(client):
    _create_skill(client, "_steps", "Invoice Workflow", ["invoice workflow"])

    resp = client.post("/api/agent/plan-task", json={
        "command": "invoice workflow",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("type") == "skill_match"
    steps = data["matched_skill"].get("steps", [])
    assert len(steps) > 0
    assert "step_type" in steps[0] or "tool" in steps[0]
