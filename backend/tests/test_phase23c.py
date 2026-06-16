"""Phase 23C — Accountant AutoPilot wiring tests.

Tests that the plan-task and voice parse endpoints return enriched fields
(detected_language, voice_reply_text, suggested_next_actions, etc.)
"""

from __future__ import annotations

import json
import os
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.accountant_autopilot import build_accountant_plan
from app.services.multilingual_command import detect_language, translate_to_internal_english, generate_voice_reply
from app.services.voice_reply import build_user_reply


# ── Helpers ───────────────────────────────────────────────────────────────────

def _plan_task(client, command, **kwargs):
    payload = {"command": command, "force_new_plan": True, **kwargs}
    resp = client.post("/api/agent/plan-task", json=payload)
    assert resp.status_code == 200, f"plan-task failed: {resp.text}"
    return resp.json()


def _set_mock_provider():
    os.environ["AGENT_PROVIDER"] = "mock"
    os.environ["AGENT_ALLOW_CLOUD"] = "false"
    os.environ["AGENT_API_KEY"] = ""


@pytest.fixture(autouse=True)
def _reset_agent_env():
    _set_mock_provider()
    os.environ["MULTILINGUAL_ENABLED"] = "true"
    yield
    _set_mock_provider()


@pytest.fixture()
def client_with_auth(client):
    resp = client.post("/api/auth/register", json={
        "email": "agent-user-23c@test.com", "password": "Test@123456", "full_name": "Agent User",
    })
    data = resp.json()
    token = data["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture()
def mock_user():
    user = Mock()
    user.id = 1
    user.email = "agent-user@test.com"
    return user


# ── Enriched Plan-Task Endpoint Tests ─────────────────────────────────────────


def test_plan_task_returns_enriched_fields(client_with_auth):
    _set_mock_provider()
    data = _plan_task(client_with_auth, "read this screen")

    assert "plan_id" in data
    assert data["plan_id"] > 0
    assert "plan" in data
    assert data["plan"]["task_title"] is not None

    assert "original_command" in data
    assert data["original_command"] == "read this screen"

    assert "detected_language" in data
    assert data["detected_language"] == "en"

    assert "normalized_command" in data
    assert data["normalized_command"] == "read this screen"

    assert "internal_english_command" in data
    assert data["internal_english_command"] == "read this screen"

    assert "summary_for_user" in data
    assert len(data["summary_for_user"]) > 0

    assert "voice_reply_text" in data
    assert len(data["voice_reply_text"]) > 0

    assert "task_type" in data
    assert "risk_level" in data
    assert "requires_approval" in data

    assert "clarification_needed" in data
    assert "clarification_question" in data

    assert "blocked_reason" in data

    assert "suggested_next_actions" in data
    assert isinstance(data["suggested_next_actions"], list)

    assert "can_save_workflow" in data
    assert isinstance(data["can_save_workflow"], bool)

    assert "matched_workflow_id" in data
    assert "matched_workflow_name" in data


def test_plan_task_enriched_for_blocked_command(client_with_auth):
    _set_mock_provider()
    resp = client_with_auth.post("/api/agent/plan-task", json={"command": "delete all invoices"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["plan"]["risk_level"] == "blocked"
    assert data["blocked_reason"] is not None
    assert data["voice_reply_text"] is not None
    assert "block" in data["voice_reply_text"].lower()
    assert data["suggested_next_actions"] == []
    assert data["can_save_workflow"] is False
    assert data["plan_id"] is None


def test_plan_task_voice_reply_generated(client_with_auth):
    _set_mock_provider()
    data = _plan_task(client_with_auth, "read this screen")

    voice_reply = data["voice_reply_text"]
    assert isinstance(voice_reply, str)
    assert len(voice_reply) > 5


def test_plan_task_suggested_next_actions(client_with_auth):
    _set_mock_provider()
    data = _plan_task(client_with_auth, "read this screen")

    actions = data["suggested_next_actions"]
    assert isinstance(actions, list)
    assert len(actions) > 0
    assert any("Approve" in a for a in actions)


def test_plan_task_with_clarification(client_with_auth):
    _set_mock_provider()
    resp = client_with_auth.post("/api/agent/plan-task", json={"command": "?"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["clarification_needed"] is True
    assert data["clarification_question"] is not None
    assert data["voice_reply_text"] is not None
    assert "clarify" in data["voice_reply_text"].lower()


def test_plan_task_suggested_actions_for_clarification(client_with_auth):
    _set_mock_provider()
    resp = client_with_auth.post("/api/agent/plan-task", json={"command": "?"})
    assert resp.status_code == 200
    data = resp.json()

    actions = data["suggested_next_actions"]
    assert len(actions) > 0
    assert any("Read this screen" in a for a in actions)


# ── Multilingual Command Tests ────────────────────────────────────────────────


def test_plan_task_enriched_roman_urdu(client_with_auth):
    _set_mock_provider()
    data = _plan_task(client_with_auth, "email sa aj ki invoice download karo")

    assert data["detected_language"] == "roman_urdu"
    internal = data["internal_english_command"]
    assert "download" in internal


def test_plan_task_voice_reply_roman_urdu(client_with_auth):
    _set_mock_provider()
    data = _plan_task(client_with_auth, "email sa aj ki invoice download karo")

    voice_reply = data["voice_reply_text"]
    assert isinstance(voice_reply, str)
    assert len(voice_reply) > 5


# ── Voice Router Integration Tests ─────────────────────────────────────────────


def test_voice_parse_returns_plan_fields(client_with_auth):
    _set_mock_provider()
    resp = client_with_auth.post("/api/voice/parse-command", json={"raw_text": "read this screen"})
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()

    assert "command_id" in data
    assert data["raw_text"] == "read this screen"
    assert "domain" in data
    assert "intent" in data
    assert "params" in data
    assert "needs_approval" in data
    assert "preview_message" in data
    assert "risk_level" in data
    assert "confidence" in data
    assert "clarification_needed" in data
    assert "suggestions" in data

    params = data["params"]
    assert "detected_language" in params
    assert "normalized_command" in params
    assert "internal_english_command" in params
    assert "summary_for_user" in params


def test_voice_parse_blocked(client_with_auth):
    _set_mock_provider()
    resp = client_with_auth.post("/api/voice/parse-command", json={"raw_text": "delete all invoices"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["risk_level"] == "blocked" or data["risk_level"] == "high"
    assert data["params"].get("blocked_reason") is not None


def test_voice_parse_roman_urdu(client_with_auth):
    _set_mock_provider()
    resp = client_with_auth.post("/api/voice/parse-command", json={"raw_text": "email sa aj ki invoice download karo"})
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()

    params = data["params"]
    assert params["detected_language"] == "roman_urdu"
    assert "download" in params["internal_english_command"]


def test_voice_parse_clarification(client_with_auth):
    _set_mock_provider()
    resp = client_with_auth.post("/api/voice/parse-command", json={"raw_text": "?"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["clarification_needed"] is True
    assert data["clarification_question"] is not None


# ── build_accountant_plan Unit Tests ─────────────────────────────────────────


def test_build_accountant_plan_returns_enriched_dict(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(db_session, "read this screen", mock_user)

    assert "task_title" in plan
    assert "language" in plan
    assert "risk_level" in plan
    assert "requires_approval" in plan
    assert "can_save_workflow" in plan
    assert "steps" in plan
    assert plan.get("language") == "en"


def test_build_accountant_plan_blocked(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(db_session, "delete all invoices", mock_user)

    assert plan["risk_level"] == "blocked"
    assert plan["blocked_reason"] is not None
    assert plan["requires_approval"] is False


def test_build_accountant_plan_detects_roman_urdu(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(db_session, "email sa aj ki invoice download karo", mock_user)

    assert plan["language"] == "roman_urdu"
    assert "steps" in plan


def test_build_accountant_plan_clarification(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(db_session, "?", mock_user)

    assert plan.get("clarification_needed") is True
    assert plan.get("clarification_question") is not None


# ── Navigation command tests ──────────────────────────────────────────────────


def test_build_accountant_plan_voice_navigation(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(db_session, "Open voice command center", mock_user)

    assert plan.get("type") == "navigation"
    assert plan.get("target") == "voice"
    assert plan.get("route") == "/voice"


def test_build_accountant_plan_workflow_memory_navigation(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(db_session, "Show workflow memory", mock_user)

    assert plan.get("type") == "navigation"
    assert plan.get("target") == "workflow_memory"
    assert plan.get("route") == "/app/workflow-memory"


def test_build_accountant_plan_settings_navigation(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(db_session, "Open settings", mock_user)

    assert plan.get("type") == "navigation"
    assert plan.get("target") == "settings"
    assert plan.get("route") == "/app/settings"


def test_build_accountant_plan_navigation_no_save_workflow(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(db_session, "voice commands", mock_user)

    assert plan.get("type") == "navigation"
    assert plan.get("can_save_workflow") is False
    assert plan.get("requires_approval") is False
    assert len(plan.get("steps", [])) == 0


def test_build_accountant_plan_fallback_clarification(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(db_session, "zzzznothingzzzz", mock_user)

    assert plan.get("clarification_needed") is True
    assert plan.get("task_type") == "needs_clarification"
    assert plan.get("requires_approval") is False
    # Should not contain fake invoice counts (the word "invoice" may appear in allowed-context descriptions)
    summary = plan.get("summary_for_user", "").lower()
    assert "0 invoices" not in summary
    assert "process ki" not in summary


def test_build_accountant_plan_fallback_no_fake_invoice(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(db_session, "do something random", mock_user)

    assert plan.get("clarification_needed") is True
    assert plan.get("can_save_workflow") is False
    assert plan.get("requires_approval") is False
    # Ensure no fake invoice fabrication in summary
    summary = plan.get("summary_for_user", "")
    assert "0 invoices" not in summary
    assert "process ki" not in summary


# ── Phase 38 — Excel Downloads Intent Tests (LLM-first) ───────────────────

# The Roman Urdu regex cascade has been removed. The LLM (mock or cloud) is
# the primary intent engine. The mock provider detects English keyword patterns
# for Excel downloads. Roman Urdu-specific tests have been deprecated.


def test_excel_downloads_intent_english(db_session, mock_user):
    """English 'excel file in downloads summary' maps to excel_summary_from_downloads via mock provider."""
    _set_mock_provider()
    plan = build_accountant_plan(
        db_session,
        "create a summary of the excel file in downloads called parcel lab",
        mock_user,
    )
    assert plan.get("task_type") == "excel_summary_from_downloads"
    assert plan.get("task_title") == "Excel Summary from Downloads"
    assert plan.get("can_save_workflow") is True


def test_excel_downloads_plan_has_correct_steps(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(
        db_session,
        "find an excel file in downloads and create a summary",
        mock_user,
    )
    steps = plan.get("steps", [])
    assert len(steps) >= 2
    step_types = [s.get("step_type") for s in steps]
    assert "file_find_in_downloads" in step_types
    assert "excel_create_summary_from_file" in step_types
    assert "read_screen" not in step_types
    assert "desktop_click" not in step_types
    assert "excel_create_workbook" not in step_types


def test_excel_downloads_no_daily_invoice_process(db_session, mock_user):
    """Save workflow title should NOT be Daily Invoice Process for Excel summary from Downloads."""
    _set_mock_provider()
    plan = build_accountant_plan(
        db_session,
        "give me a summary of the excel spreadsheet in my downloads folder",
        mock_user,
    )
    title = plan.get("task_title", "")
    assert title == "Excel Summary from Downloads"
    assert "Daily Invoice" not in title
    assert "Invoice" not in title


def test_excel_downloads_extracted_query_parcel_lab(db_session, mock_user):
    """Extracted query should be 'parcel lab' from English command with filler words."""
    from app.services.accountant_autopilot import _extract_file_query
    query = _extract_file_query(
        "download folder mein parcel lab ki file ko read karo aur uski samri mujhe batao"
    )
    assert query == "parcel lab", f"Expected 'parcel lab', got '{query}'"


def test_excel_downloads_extracted_query_rana(db_session, mock_user):
    """Extracted query should be 'rana' from Roman Urdu command."""
    from app.services.accountant_autopilot import _extract_file_query
    query = _extract_file_query(
        "download mein se Rana ke naam ki PDF open karo"
    )
    assert query == "rana", f"Expected 'rana', got '{query}'"


def test_excel_downloads_extracted_query_sales_report(db_session, mock_user):
    """Extracted query should be 'sales report' — multi-word names preserved."""
    from app.services.accountant_autopilot import _extract_file_query
    query = _extract_file_query(
        "downloads folder se sales report wali excel file ki summary banao"
    )
    assert query == "sales report", f"Expected 'sales report', got '{query}'"


def test_excel_downloads_extracted_query_parcel_layer(db_session, mock_user):
    from app.services.accountant_autopilot import _extract_file_query
    query = _extract_file_query(
        "download folder mein parcel layer naam ki excel file hai uski summary create karo"
    )
    assert query == "parcel layer", f"Expected 'parcel layer', got '{query}'"


def test_excel_downloads_plan_message_clean_query(db_session, mock_user):
    """Plan summary should use cleaned 'parcel lab' from English command."""
    _set_mock_provider()
    plan = build_accountant_plan(
        db_session,
        "create a summary of the parcel lab excel file from downloads",
        mock_user,
    )
    summary = plan.get("summary_for_user", "")
    assert "parcel lab" in summary


def test_excel_downloads_step_one_has_clean_query(db_session, mock_user):
    """file_find_in_downloads step should receive the clean query, not noisy text."""
    _set_mock_provider()
    plan = build_accountant_plan(
        db_session,
        "create a summary of the parcel lab spreadsheet in downloads",
        mock_user,
    )
    steps = plan.get("steps", [])
    assert len(steps) >= 1
    first_params = steps[0].get("parameters", {})
    q = first_params.get("query", "")
    # Should contain 'parcel lab' (may have extra noise like 'a')
    assert "parcel" in q
    assert "lab" in q
    assert "create" not in q
    assert "summary" not in q


def test_excel_downloads_multiple_files_plan_has_file_selection(db_session, mock_user):
    _set_mock_provider()
    plan = build_accountant_plan(
        db_session,
        "find an excel file in downloads and make a summary",
        mock_user,
    )
    steps = plan.get("steps", [])
    assert len(steps) >= 2
    first_step = steps[0]
    assert first_step.get("step_type") == "file_find_in_downloads"
    # Should accept .xlsx .xls .csv
    exts = first_step.get("parameters", {}).get("extensions", [])
    assert ".xlsx" in exts
    assert ".csv" in exts


def test_english_excel_downloads_intent_still_works(db_session, mock_user):
    """English 'find Excel file in downloads and create summary' produces correct plan."""
    _set_mock_provider()
    plan = build_accountant_plan(
        db_session,
        "find an Excel file in downloads and create a summary",
        mock_user,
    )
    assert plan.get("task_type") in ("excel_summary_from_downloads",)
    steps = plan.get("steps", [])
    step_types = [s.get("step_type") for s in steps]
    assert "read_screen" not in step_types


# ── Phase 38.5 — Multilingual Excel Downloads Tests (Mock Provider) ─────


def test_french_excel_downloads_intent(db_session, mock_user):
    """French 'résumé fichier excel téléchargements' maps to excel_summary_from_downloads."""
    _set_mock_provider()
    plan = build_accountant_plan(
        db_session,
        "crée un résumé du fichier excel dans téléchargements",
        mock_user,
    )
    assert plan.get("task_type") == "excel_summary_from_downloads"
    assert plan.get("language") is not None


def test_spanish_excel_downloads_intent(db_session, mock_user):
    """Spanish 'resumen archivo excel descargas' maps to excel_summary_from_downloads."""
    _set_mock_provider()
    plan = build_accountant_plan(
        db_session,
        "crear un resumen del archivo de excel en descargas",
        mock_user,
    )
    assert plan.get("task_type") == "excel_summary_from_downloads"
    assert plan.get("language") is not None


def test_german_excel_downloads_intent(db_session, mock_user):
    """German 'Zusammenfassung Excel-Datei Downloads' maps to excel_summary_from_downloads."""
    _set_mock_provider()
    plan = build_accountant_plan(
        db_session,
        "erstellen sie eine zusammenfassung der excel-datei in downloads",
        mock_user,
    )
    assert plan.get("task_type") == "excel_summary_from_downloads"
    assert plan.get("language") is not None


def test_french_excel_downloads_has_correct_steps(db_session, mock_user):
    """French Excel downloads command produces correct step types."""
    _set_mock_provider()
    plan = build_accountant_plan(
        db_session,
        "fais un résumé du fichier excel dans téléchargements",
        mock_user,
    )
    steps = plan.get("steps", [])
    assert len(steps) >= 2
    step_types = [s.get("step_type") for s in steps]
    assert "file_find_in_downloads" in step_types
    assert "excel_create_summary_from_file" in step_types


# ── Language Detection Utility Tests ─────────────────────────────────────


def test_detect_language_simple_english():
    from app.services.language_utils import detect_language_simple
    assert detect_language_simple("find an excel file in downloads") == "en"
    assert detect_language_simple("create a summary of the parcel lab excel") == "en"


def test_detect_language_simple_french():
    from app.services.language_utils import detect_language_simple
    result = detect_language_simple("crée un résumé du fichier excel dans téléchargements")
    assert result == "french"


def test_detect_language_simple_spanish():
    from app.services.language_utils import detect_language_simple
    result = detect_language_simple("crear un resumen del archivo de excel en descargas")
    assert result == "spanish"


def test_detect_language_simple_german():
    from app.services.language_utils import detect_language_simple
    result = detect_language_simple("erstellen sie eine zusammenfassung der excel-datei in downloads")
    assert result == "german"


def test_detect_language_simple_empty():
    from app.services.language_utils import detect_language_simple
    assert detect_language_simple("") == "unknown"
