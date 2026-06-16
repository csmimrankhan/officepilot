from __future__ import annotations

import json
import os

import pytest

from app.services.multilingual_command import (
    detect_language,
    normalize_command,
    translate_to_internal_english,
    generate_voice_reply,
    get_supported_languages,
    build_clarification_question,
)
from app.services.tool_registry import (
    list_tools,
    get_tool,
    list_tools_by_risk,
    validate_tool_plan,
)
from app.services.voice_reply import (
    build_user_reply,
    speak_text_if_enabled,
    return_text_response,
)
from app.services.accountant_autopilot import (
    build_accountant_plan,
    SYSTEM_TODAY,
    get_system_today,
)
from app.models.agent_workflow_memory import AgentWorkflowMemory
from app.models.agent_workflow_run import AgentWorkflowRun


# ── Multilingual Command Tests ──────────────────────────────────────────────


def test_detect_english():
    assert detect_language("show pending invoices") == "en"


def test_detect_roman_urdu():
    assert detect_language("email sa aj ki invoice download karo") == "roman_urdu"


def test_detect_urdu():
    assert detect_language("آج کی رسیدیں ڈاؤن لوڈ کرو") == "urdu"


def test_detect_empty():
    assert detect_language("") == "unknown"


def test_normalize_command():
    assert normalize_command("  SHOW Invoices  ") == "show invoices"


def test_translate_roman_urdu_email_invoice():
    result = translate_to_internal_english("email sa aj ki invoice download karo")
    assert "from email" in result
    assert "today's" in result
    assert "download" in result


def test_translate_roman_urdu_yesterday():
    result = translate_to_internal_english("kal wala workflow repeat karo")
    assert "yesterday's" in result


def test_translate_roman_urdu_excel():
    result = translate_to_internal_english("excel ma save karo")
    assert "in Excel" in result


def test_translate_roman_urdu_complex():
    result = translate_to_internal_english("email sa aj ki invoice download kar ka PDF ka data extract karo aur single excel file ma save karo")
    assert "from email" in result
    assert "today's" in result
    assert "download" in result
    assert "pdf data" in result or "PDF data" in result
    assert "extract" in result
    assert "in a single excel file" in result.lower()


def test_english_passthrough():
    result = translate_to_internal_english("Read this screen")
    assert "read this screen" in result


def test_generate_voice_reply_roman_urdu():
    result = generate_voice_reply("invoice_count", "roman_urdu", count=5)
    assert "5" in result
    assert "Maine" in result


def test_generate_voice_reply_english():
    result = generate_voice_reply("total_amount", "en", total="142,500")
    assert "142,500" in result
    assert "total" in result


def test_generate_voice_reply_unknown_template():
    result = generate_voice_reply("nonexistent", "en")
    assert result == ""


def test_get_supported_languages():
    langs = get_supported_languages()
    codes = [l["code"] for l in langs]
    assert "en" in codes
    assert "roman_urdu" in codes
    assert "urdu" in codes


def test_build_clarification_question():
    q = build_clarification_question("roman_urdu")
    assert len(q) > 0
    assert "samajh" in q.lower() or "clarify" in q.lower()


# ── Tool Registry Tests ─────────────────────────────────────────────────────


def test_list_tools():
    tools = list_tools()
    assert len(tools) >= 15


def test_get_tool_exists():
    tool = get_tool("create_excel_workbook")
    assert tool is not None
    assert tool.risk_level == "medium"
    assert tool.approval_required is True


def test_get_tool_not_found():
    assert get_tool("nonexistent_tool") is None


def test_list_tools_by_risk_high():
    tools = list_tools_by_risk("high")
    high_names = [t.name for t in tools]
    assert "click_approved_target" in high_names
    assert "type_approved_text" in high_names


def test_list_tools_by_risk_low():
    tools = list_tools_by_risk("low")
    low_names = [t.name for t in tools]
    assert "read_current_screen" in low_names
    assert "open_file" in low_names


def test_validate_tool_plan_valid():
    valid, err = validate_tool_plan("create_excel_workbook", {})
    assert valid is True
    assert err is None


def test_validate_tool_plan_invalid():
    valid, err = validate_tool_plan("nonexistent", {})
    assert valid is False
    assert err is not None


def test_excel_total_calculated_by_code_not_llm():
    tool = get_tool("calculate_excel_total")
    assert tool is not None
    assert tool.risk_level == "low"
    assert tool.approval_required is False


def test_no_payment_tool():
    tool = get_tool("make_payment")
    assert tool is None


# ── Voice Reply Tests ───────────────────────────────────────────────────────


def test_build_user_reply_english():
    reply = build_user_reply("done", "en")
    assert "completed" in reply.lower()


def test_build_user_reply_roman_urdu():
    reply = build_user_reply("done", "roman_urdu")
    assert "ho gaya" in reply


def test_build_user_reply_urdu():
    reply = build_user_reply("invoice_count", "urdu", count=3)
    assert "3" in reply


def test_speak_text_if_enabled_false():
    result = speak_text_if_enabled("hello", "en")
    assert result["text"] == "hello"
    assert result["tts_enabled"] is False


def test_return_text_response():
    result = return_text_response("Task done", "en")
    assert result["reply"] == "Task done"
    assert result["language"] == "en"


# ── Safety Tests ────────────────────────────────────────────────────────────


def test_voice_approval_disabled_by_default():
    val = os.environ.get("VOICE_APPROVAL_ENABLED", "false")
    assert val.lower() in ("false", "0", "no")


def test_dangerous_tool_requires_approval():
    tool = get_tool("click_approved_target")
    assert tool is not None
    assert tool.approval_required is True
    assert tool.risk_level == "high"


# ── Feature Flag Tests ──────────────────────────────────────────────────────


def test_pilot_tools_disabled_by_default():
    val = os.environ.get("PILOT_TOOLS_ENABLED", "false")
    assert val.lower() in ("false", "0", "no")


def test_advanced_tools_enabled_by_default():
    val = os.environ.get("ADVANCED_TOOLS_ENABLED", "true")
    assert val.lower() in ("1", "true", "yes", "on")


def test_multilingual_enabled():
    val = os.environ.get("MULTILINGUAL_ENABLED", "false")
    assert val.lower() in ("1", "true", "yes", "on")


# ── Accountant AutoPilot (basic structure tests) ────────────────────────────


def test_system_today():
    from datetime import date
    assert get_system_today() == date.today()
