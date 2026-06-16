"""Tests for the Hermes-style Accounting Skills system."""

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


def _register_and_login(client):
    resp = client.post("/api/auth/register", json={
        "email": "skilltest@example.com",
        "password": "Secret123!",
        "full_name": "Skill Test User",
    })
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _create_demo_plan(client):
    resp = client.post("/api/agent/plan-task", json={
        "command": "create daily invoice summary for today",
        "context": {"language": "en"},
        "force_new_plan": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    pid = data.get("plan_id")
    if not pid:
        pid = data.get("plan", {}).get("plan_id")
    assert pid is not None, f"No plan_id in response: {data}"
    return pid


def test_create_skill_from_plan(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)

    resp = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid,
        "name": "Daily Invoice Summary",
        "description": "Auto-create daily invoice summary",
        "trigger_phrases": ["daily invoice", "invoice summary", "aaj ka invoice"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["skill_id"] > 0
    assert data["name"] == "Daily Invoice Summary"
    assert "risk_level" in data
    assert data["steps_count"] > 0


def test_create_skill_missing_source(client):
    _register_and_login(client)
    resp = client.post("/api/accounting-skills/from-workflow", json={})
    assert resp.status_code == 400
    assert "Either plan_id or workflow_memory_id" in resp.json()["detail"]


def test_list_skills(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid, "name": "Test Skill",
    })
    resp = client.get("/api/accounting-skills")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Test Skill"
    assert data[0]["steps_count"] > 0


def test_get_skill_detail(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    cr = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid, "name": "Detail Skill",
    }).json()
    sid = cr["skill_id"]

    resp = client.get(f"/api/accounting-skills/{sid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Detail Skill"
    assert "workflow_steps" in data
    assert len(data["workflow_steps"]) > 0
    assert "variables" in data
    assert "safety_rules" in data
    assert data["status"] == "active"
    assert data["version"] == 1


def test_get_skill_not_found(client):
    _register_and_login(client)
    resp = client.get("/api/accounting-skills/99999")
    assert resp.status_code == 404


def test_match_skill_by_phrase(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid,
        "name": "Match Test Skill",
        "trigger_phrases": ["daily invoice", "monthly summary", "invoice report"],
    })

    resp = client.get("/api/accounting-skills/match?phrase=daily invoice")
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] is True
    assert data["skill"]["confidence"] >= 0.5

    resp2 = client.get("/api/accounting-skills/match?phrase=nonexistent-task")
    assert resp2.status_code == 200
    assert resp2.json()["matched"] is False


def test_update_skill_increments_version(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    cr = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid, "name": "Version Test",
    }).json()
    sid = cr["skill_id"]

    resp = client.patch(f"/api/accounting-skills/{sid}", json={
        "name": "Version Test Updated",
    })
    assert resp.status_code == 200
    assert resp.json()["version"] == 2

    detail = client.get(f"/api/accounting-skills/{sid}").json()
    assert detail["version"] == 2
    assert detail["name"] == "Version Test Updated"


def test_skill_versions_list(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    cr = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid, "name": "VList Skill",
    }).json()
    sid = cr["skill_id"]

    client.patch(f"/api/accounting-skills/{sid}", json={"name": "VList v2"})
    client.patch(f"/api/accounting-skills/{sid}", json={"name": "VList v3"})

    resp = client.get(f"/api/accounting-skills/{sid}/versions")
    assert resp.status_code == 200
    versions = resp.json()
    assert len(versions) >= 3
    assert versions[0]["version"] == 3
    assert versions[2]["version"] == 1


def test_restore_skill_version(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    cr = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid, "name": "Restore Test",
    }).json()
    sid = cr["skill_id"]

    client.patch(f"/api/accounting-skills/{sid}", json={"name": "Restore v2"})
    client.patch(f"/api/accounting-skills/{sid}", json={"name": "Restore v3"})

    resp = client.post(f"/api/accounting-skills/{sid}/restore/1")
    assert resp.status_code == 200
    assert resp.json()["restored_from_version"] == 1

    detail = client.get(f"/api/accounting-skills/{sid}").json()
    assert detail["name"] == "Restore Test"
    assert detail["version"] == 4


def test_dry_run_skill(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    cr = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid, "name": "Dry-Run Test",
    }).json()
    sid = cr["skill_id"]

    resp = client.post(f"/api/accounting-skills/{sid}/dry-run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["run_id"] > 0
    assert data["result"]["dry_run"] is True
    assert "steps_preview" in data["result"]


def test_execute_skill_requires_approval(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    cr = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid, "name": "Exec Test",
    }).json()
    sid = cr["skill_id"]

    resp = client.post(f"/api/accounting-skills/{sid}/execute", json={})
    assert resp.status_code == 400
    assert "Approval required" in resp.json()["detail"]


def test_archive_skill(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    cr = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid, "name": "Archive Test",
    }).json()
    sid = cr["skill_id"]

    resp = client.post(f"/api/accounting-skills/{sid}/archive")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    detail = client.get(f"/api/accounting-skills/{sid}").json()
    assert detail["status"] == "archived"


def test_skill_runs_list(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    cr = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid, "name": "Runs Test",
    }).json()
    sid = cr["skill_id"]

    client.post(f"/api/accounting-skills/{sid}/dry-run")

    resp = client.get(f"/api/accounting-skills/{sid}/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["status"] == "dry_run"


def test_complete_skill_run(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    cr = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid, "name": "Complete Test",
    }).json()
    sid = cr["skill_id"]
    dr = client.post(f"/api/accounting-skills/{sid}/dry-run").json()
    run_id = dr["run_id"]

    resp = client.post(f"/api/accounting-skills/runs/{run_id}/complete", json={
        "result_json": json.dumps({"status": "ok", "rows": 10}),
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    runs = client.get(f"/api/accounting-skills/{sid}/runs").json()
    completed = [r for r in runs if r["id"] == run_id]
    assert len(completed) == 1
    assert completed[0]["status"] == "completed"


def test_block_dangerous_skill_name(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    resp = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid,
        "name": "Process Payment",
    })
    assert resp.status_code == 400
    assert "blocked" in resp.json()["detail"].lower()


def test_block_dangerous_skill_step(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    resp = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid,
        "name": "Safe Skill",
    })
    assert resp.status_code == 200

    cr = resp.json()
    sid = cr["skill_id"]

    dangerous_steps = json.dumps([{"step_type": "bank_transfer", "target": "account", "instruction": "transfer payment to vendor", "risk_level": "high"}])
    resp2 = client.patch(f"/api/accounting-skills/{sid}", json={
        "workflow_steps_json": dangerous_steps,
    })
    assert resp2.status_code == 400
    assert "blocked" in resp2.json()["detail"].lower()


def test_unauthorized_user_cannot_access_other_skills(client):
    _register_and_login(client)
    pid = _create_demo_plan(client)
    cr = client.post("/api/accounting-skills/from-workflow", json={
        "plan_id": pid, "name": "Private Skill",
    }).json()
    sid = cr["skill_id"]
    client.headers.pop("Authorization")

    other = TestClient(client.app)
    other.post("/api/auth/register", json={
        "email": "other@example.com", "password": "Secret123!", "full_name": "Other",
    })
    other_resp = other.post("/api/auth/login", json={
        "email": "other@example.com", "password": "Secret123!",
    })
    other.headers.update({"Authorization": f"Bearer {other_resp.json()['access_token']}"})

    resp = other.get(f"/api/accounting-skills/{sid}")
    assert resp.status_code == 404
