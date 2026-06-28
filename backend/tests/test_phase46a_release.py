"""Phase 46A — Grand Release v1.0.0 tests."""

from __future__ import annotations

import os
from datetime import date

os.environ["OFFICEPILOT_APP_VERSION"] = "1.0.0"

from fastapi.testclient import TestClient

from app import __version__ as app_version
from app.config import get_settings
from app.main import create_app

app = create_app()
client = TestClient(app)


def test_app_version():
    assert app_version == "1.0.0"


def test_config_version():
    assert get_settings().app_version == "1.0.0"


def test_release_notes_endpoint_structure():
    resp = client.get("/api/app/release-notes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == "1.0.0"
    assert body["release_date"] == date.today().isoformat()
    assert isinstance(body["highlights"], list)
    assert len(body["highlights"]) >= 5
    expected = [
        "Multi-Agent Swarm Architecture",
        "Semantic Bank Reconciliation",
        "Live Voice-Driven Excel Editing",
        "Autonomous Background Watchers",
        "Ollama Local LLM Brain",
    ]
    for item in expected:
        assert item in body["highlights"]


def test_release_notes_no_auth_required():
    resp = client.get("/api/app/release-notes")
    assert resp.status_code == 200


def test_health_endpoint_reports_v1():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["version"] == "1.0.0"
