"""Phase 38.5 — Multilingual Voice Pipeline Smoke Tests.

Tests that speech-transcribed text in multiple languages produces correct
plan structures via the mock provider's keyword detection.
"""

from __future__ import annotations

import os
from unittest.mock import Mock

import pytest

from app.services.accountant_autopilot import build_accountant_plan


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
def mock_user():
    user = Mock()
    user.id = 1
    user.email = "smoke-test@test.com"
    return user


def _assert_excel_downloads_plan(plan):
    """Assert plan has correct structure for Excel-downloads summary."""
    assert plan.get("task_type") == "excel_summary_from_downloads"
    assert plan.get("task_title") == "Excel Summary from Downloads"
    steps = plan.get("steps", [])
    assert len(steps) >= 2
    step_types = [s.get("step_type") for s in steps]
    assert "file_find_in_downloads" in step_types
    assert "excel_create_summary_from_file" in step_types
    assert plan.get("requires_approval") is True
    assert plan.get("can_save_workflow") is True


# ── Simulated transcribed text tests ─────────────────────────────────────


def test_transcribed_english_excel_command(db_session, mock_user):
    """Simulates spoken 'create excel summary parcel lab downloads'."""
    plan = build_accountant_plan(
        db_session,
        "create a summary of the parcel lab excel in downloads",
        mock_user,
    )
    _assert_excel_downloads_plan(plan)
    assert "parcel" in plan.get("summary_for_user", "")


def test_transcribed_french_excel_command(db_session, mock_user):
    """Simulates spoken 'crée un résumé fichier excel téléchargements'."""
    plan = build_accountant_plan(
        db_session,
        "crée un résumé du fichier excel dans téléchargements",
        mock_user,
    )
    _assert_excel_downloads_plan(plan)
    assert plan.get("language") is not None


def test_transcribed_spanish_excel_command(db_session, mock_user):
    """Simulates spoken 'crear resumen archivo excel descargas'."""
    plan = build_accountant_plan(
        db_session,
        "crear un resumen del archivo de excel en descargas",
        mock_user,
    )
    _assert_excel_downloads_plan(plan)


def test_transcribed_german_excel_command(db_session, mock_user):
    """Simulates spoken 'zusammenfassung excel datei downloads'."""
    plan = build_accountant_plan(
        db_session,
        "erstellen sie eine zusammenfassung der excel-datei in downloads",
        mock_user,
    )
    _assert_excel_downloads_plan(plan)


def test_transcribed_mixed_roman_urdu_command(db_session, mock_user):
    """Simulates spoken mixed Roman Urdu / English command."""
    plan = build_accountant_plan(
        db_session,
        "download folder mein parcel lab ki excel file ki summary banao",
        mock_user,
    )
    # Roman Urdu with English keywords falls through to LLM/mock
    # The mock provider detects 'download' + 'excel' + 'summary' → Excel downloads
    _assert_excel_downloads_plan(plan)
    # Language should be detected as roman_urdu
    assert plan.get("language") == "roman_urdu"


# ── Safety gate tests ────────────────────────────────────────────────────


def test_safety_gate_blocks_payment(db_session, mock_user):
    """Blocked command returns blocked regardless of language."""
    plan = build_accountant_plan(
        db_session,
        "transfer money to vendor",
        mock_user,
    )
    assert plan.get("risk_level") == "blocked"
    assert plan.get("blocked_reason") is not None
    assert len(plan.get("steps", [])) == 0


def test_safety_gate_english(db_session, mock_user):
    """English 'delete all invoices' is blocked."""
    plan = build_accountant_plan(
        db_session,
        "delete all invoices",
        mock_user,
    )
    assert plan.get("risk_level") == "blocked"


# ── Navigation tests ─────────────────────────────────────────────────────


def test_navigation_voice_command(db_session, mock_user):
    """Navigation command returns navigation plan."""
    plan = build_accountant_plan(
        db_session,
        "open voice command center",
        mock_user,
    )
    assert plan.get("type") == "navigation"
    assert plan.get("target") == "voice"


def test_navigation_settings(db_session, mock_user):
    """Navigation to settings works."""
    plan = build_accountant_plan(
        db_session,
        "open settings",
        mock_user,
    )
    assert plan.get("type") == "navigation"
    assert plan.get("target") == "settings"
