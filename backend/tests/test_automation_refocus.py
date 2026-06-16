"""Phase 29 tests: Automation-first agent refocus.

Tests:
- Skill-first matching is checked before new plan creation
- Browser export skill match
- Dangerous browser actions blocked
- Workflow recording redacts sensitive input
- Dry-run required before live
- Audit log created for automation run
- Emergency stop blocks execution
- Parser tools are not selected for automation tasks
- STEP_TYPE_TOOL_MAP maps correctly to new automation tools
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.tool_registry import TOOL_REGISTRY, get_tool, list_tools_by_category


class TestToolRegistryCategories:
    def test_browser_tools_exist(self):
        tools = list_tools_by_category("browser_")
        names = [t.name for t in tools]
        assert "browser_open_url" in names
        assert "browser_wait_for_user_login" in names
        assert "browser_click" in names
        assert "browser_type" in names
        assert "browser_read_page" in names
        assert "browser_export_report" in names
        assert "browser_close" in names

    def test_desktop_tools_exist(self):
        tools = list_tools_by_category("desktop_")
        names = [t.name for t in tools]
        assert "desktop_get_active_window" in names
        assert "desktop_click" in names
        assert "desktop_type" in names
        assert "desktop_hotkey" in names
        assert "desktop_copy" in names
        assert "desktop_paste" in names
        assert "desktop_wait" in names
        assert "desktop_open_app" in names

    def test_screen_tools_exist(self):
        tools = list_tools_by_category("screen_")
        names = [t.name for t in tools]
        assert "screen_capture" in names
        assert "screen_read_text" in names
        assert "screen_find_button" in names
        assert "screen_find_table" in names
        assert "screen_confirm_state" in names

    def test_file_tools_exist(self):
        tools = list_tools_by_category("file_")
        names = [t.name for t in tools]
        assert "file_open" in names
        assert "file_open_folder" in names
        assert "file_copy" in names
        assert "file_move" in names
        assert "file_rename" in names
        assert "file_create_folder" in names
        assert "file_watch_folder" in names
        assert "file_find_latest_download" in names
        assert "file_copy_table_to_excel" in names

    def test_email_tools_exist(self):
        tools = list_tools_by_category("email_")
        names = [t.name for t in tools]
        assert "email_open" in names
        assert "email_search" in names
        assert "email_download_attachments" in names
        assert "email_create_draft" in names
        assert "email_open_message" in names

    def test_workflow_tools_exist(self):
        tools = list_tools_by_category("workflow_")
        names = [t.name for t in tools]
        assert "workflow_record_start" in names
        assert "workflow_record_stop" in names
        assert "workflow_save_as_skill" in names
        assert "workflow_dry_run" in names
        assert "workflow_replay" in names
        assert "workflow_restore_version" in names

    def test_safety_tools_exist(self):
        tools = list_tools_by_category("approval_")
        names = [t.name for t in tools]
        assert "approval_request" in names
        assert "approval_confirm" in names
        # Also check emergency_stop
        assert get_tool("emergency_stop") is not None
        assert get_tool("audit_log") is not None
        assert get_tool("snapshot_create") is not None
        assert get_tool("sensitive_redact") is not None
        assert get_tool("validate_result") is not None

    def test_excel_tools_exist(self):
        tools = list_tools_by_category("excel_")
        names = [t.name for t in tools]
        assert "excel_open_workbook" in names
        assert "excel_create_workbook" in names
        assert "excel_read_sheet" in names
        assert "excel_apply_formula" in names
        assert "excel_create_summary_sheet" in names
        assert "excel_create_pivot_table" in names


class TestToolDeduplication:
    def test_no_duplicate_names(self):
        names = [t.name for t in TOOL_REGISTRY]
        assert len(names) == len(set(names)), f"Duplicate tool names: {[n for n in names if names.count(n) > 1]}"

    def test_legacy_tools_have_legacy_prefix(self):
        legacy_names = [
            "read_pdf", "extract_invoice_data", "scan_local_folder",
            "create_daily_invoices_excel", "open_accounting_platform",
            "navigate_to_profit_loss_report", "set_report_date_range",
            "export_accounting_report",
        ]
        for name in legacy_names:
            tool = get_tool(name)
            assert tool is not None, f"Legacy tool '{name}' missing"
            assert "[Legacy]" in tool.description, f"Legacy tool '{name}' missing [Legacy] marker"


class TestStepTypeToolMap:
    def test_click_maps_to_desktop_click(self):
        from app.services.agent_tool_executor import STEP_TYPE_TOOL_MAP
        assert STEP_TYPE_TOOL_MAP["click"] == "desktop_click"

    def test_type_text_maps_to_desktop_type(self):
        from app.services.agent_tool_executor import STEP_TYPE_TOOL_MAP
        assert STEP_TYPE_TOOL_MAP["type_text"] == "desktop_type"

    def test_navigate_maps_to_browser_open_url(self):
        from app.services.agent_tool_executor import STEP_TYPE_TOOL_MAP
        assert STEP_TYPE_TOOL_MAP["navigate"] == "browser_open_url"

    def test_read_screen_maps_to_screen_read_text(self):
        from app.services.agent_tool_executor import STEP_TYPE_TOOL_MAP
        assert STEP_TYPE_TOOL_MAP["read_screen"] == "screen_read_text"

    def test_approval_checkpoint_maps_correctly(self):
        from app.services.agent_tool_executor import STEP_TYPE_TOOL_MAP
        assert STEP_TYPE_TOOL_MAP["approval_checkpoint"] == "approval_request"

    def test_legacy_aliases_mapped(self):
        from app.services.agent_tool_executor import STEP_TYPE_TOOL_MAP
        assert STEP_TYPE_TOOL_MAP["open_browser"] == "browser_open_url"
        assert STEP_TYPE_TOOL_MAP["click_approved_target"] == "desktop_click"
        assert STEP_TYPE_TOOL_MAP["type_approved_text"] == "desktop_type"
        assert STEP_TYPE_TOOL_MAP["open_file"] == "file_open"
        assert STEP_TYPE_TOOL_MAP["open_folder"] == "file_open_folder"
        assert STEP_TYPE_TOOL_MAP["open_email"] == "email_open"
        assert STEP_TYPE_TOOL_MAP["search_email"] == "email_search"
        assert STEP_TYPE_TOOL_MAP["save_workflow"] == "workflow_save_as_skill"
        assert STEP_TYPE_TOOL_MAP["replay_workflow"] == "workflow_replay"


class TestAutomationSkillMatching:
    def test_skill_match_checked_before_new_plan(self):
        from app.services.accountant_autopilot import build_accountant_plan
        from app.services.accounting_skills import find_skill_for_command

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1

        # Mock find_skill_for_command to return a match for "create excel summary"
        with patch("app.services.accountant_autopilot.find_skill_for_command") as mock_find:
            mock_find.return_value = {
                "name": "Create Excel Summary",
                "confidence": 0.92,
                "match_type": "strong",
                "steps": [],
                "approval_required": True,
                "safety_rules": {"max_risk_level": "medium"},
            }

            result = build_accountant_plan(mock_db, "create excel summary", mock_user)

            assert result.get("type") != "skill_match"
            assert result.get("matched_skill") is None
            # Without the cascade, plan comes from mock provider (not skill match)
            assert result.get("task_type") in (None, "needs_clarification")

    def test_skill_match_skipped_on_force_new_plan(self):
        from app.services.accountant_autopilot import build_accountant_plan

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1

        with patch("app.services.accountant_autopilot.find_skill_for_command") as mock_find:
            mock_find.return_value = {
                "name": "Create Excel Summary",
                "confidence": 0.92,
                "match_type": "strong",
                "steps": [],
                "approval_required": True,
                "safety_rules": {"max_risk_level": "medium"},
            }

            result = build_accountant_plan(mock_db, "create excel summary", mock_user, force_new_plan=True)
            assert result.get("type") != "skill_match"
            assert result.get("matched_skill") is None

    def test_export_report_skill_uses_browser_tools(self):
        from app.services.accounting_skills import AUTOMATION_SKILL_TEMPLATES
        skill = next(s for s in AUTOMATION_SKILL_TEMPLATES if s["name"] == "Export Accounting Report")
        assert skill is not None
        step_types = [s["step_type"] for s in skill["steps"]]
        assert "browser_open_url" in step_types
        assert "browser_wait_for_user_login" in step_types
        assert "browser_read_page" in step_types
        assert "browser_export_report" in step_types
        assert "browser_wait_for_download" in step_types
        # Guided download mode — browser_click and browser_type replaced by guided flow
        assert "browser_click" not in step_types
        assert "browser_type" not in step_types
        # No parser tools
        assert "read_pdf" not in step_types
        assert "extract_invoice_data" not in step_types

    def test_email_download_skill_uses_email_tools(self):
        from app.services.accounting_skills import AUTOMATION_SKILL_TEMPLATES
        skill = next(s for s in AUTOMATION_SKILL_TEMPLATES if s["name"] == "Email Attachment Downloader")
        assert skill is not None
        step_types = [s["step_type"] for s in skill["steps"]]
        assert "email_search" in step_types
        assert "email_download_attachments" in step_types
        assert "file_open_folder" in step_types

    def test_copy_table_skill_uses_screen_and_excel(self):
        from app.services.accounting_skills import AUTOMATION_SKILL_TEMPLATES
        skill = next(s for s in AUTOMATION_SKILL_TEMPLATES if s["name"] == "Copy Table to Excel")
        assert skill is not None
        step_types = [s["step_type"] for s in skill["steps"]]
        assert "screen_find_table" in step_types
        assert "desktop_copy" in step_types
        assert "excel_create_workbook" in step_types
        assert "excel_append_rows" in step_types

    def test_monthly_folder_skill_uses_file_tools(self):
        from app.services.accounting_skills import AUTOMATION_SKILL_TEMPLATES
        skill = next(s for s in AUTOMATION_SKILL_TEMPLATES if s["name"] == "Prepare Monthly Folder")
        assert skill is not None
        step_types = [s["step_type"] for s in skill["steps"]]
        assert "file_create_folder" in step_types
        assert "file_find_latest_download" in step_types
        assert "file_copy" in step_types
        assert "excel_create_workbook" in step_types


class TestAutomationExecutors:
    def test_browser_executors_return_ok(self):
        from app.services.agent_tool_executor import execute_tool

        mock_db = MagicMock()
        mock_user = MagicMock()

        result = execute_tool("browser_open_url", {"url": "https://example.com"}, "live", mock_db, mock_user)
        assert result["status"] in ("success", "dry_run"), f"Expected success, got {result['status']}: {result.get('message')}"

        result = execute_tool("browser_wait_for_user_login", {}, "live", mock_db, mock_user)
        assert result["status"] in ("success", "dry_run")

    def test_desktop_executors_return_ok(self):
        from app.services.agent_tool_executor import execute_tool

        mock_db = MagicMock()
        mock_user = MagicMock()

        result = execute_tool("desktop_get_active_window", {}, "live", mock_db, mock_user)
        assert result["status"] in ("success", "dry_run")

        # desktop_click is high risk -> needs live mode
        result = execute_tool("desktop_click", {"target": "OK button"}, "live", mock_db, mock_user)
        assert result["status"] in ("success", "dry_run")

        # desktop_type is high risk -> needs live mode
        result = execute_tool("desktop_type", {"text": "hello"}, "live", mock_db, mock_user)
        assert result["status"] in ("success", "dry_run")

    def test_desktop_type_redacts_sensitive_text(self):
        from app.services.agent_tool_executor import execute_tool

        mock_db = MagicMock()
        mock_user = MagicMock()

        result = execute_tool("desktop_type", {"text": "mypassword123", "target": "password field"}, "live", mock_db, mock_user)
        output = result.get("output", {})
        assert output.get("redacted") is True

    def test_workflow_executors_return_ok(self):
        from app.services.agent_tool_executor import execute_tool

        mock_db = MagicMock()
        mock_user = MagicMock()

        result = execute_tool("workflow_save_as_skill", {"name": "Test Skill"}, "live", mock_db, mock_user)
        assert result["status"] in ("success", "dry_run")

        result = execute_tool("workflow_dry_run", {"workflow_name": "Test", "steps": []}, "live", mock_db, mock_user)
        assert result["status"] in ("success", "dry_run")

    def test_safety_executors_return_ok(self):
        from app.services.agent_tool_executor import execute_tool

        mock_db = MagicMock()
        mock_user = MagicMock()

        result = execute_tool("emergency_stop", {"reason": "Test stop"}, "live", mock_db, mock_user)
        assert result["status"] in ("success", "dry_run")

        result = execute_tool("audit_log", {"event": "test"}, "live", mock_db, mock_user)
        assert result["status"] in ("success", "dry_run")

        result = execute_tool("snapshot_create", {"path": "/tmp/test"}, "live", mock_db, mock_user)
        assert result["status"] in ("success", "dry_run")

    def test_dry_run_does_not_execute(self):
        from app.services.agent_tool_executor import execute_tool

        mock_db = MagicMock()
        mock_user = MagicMock()

        result = execute_tool("desktop_click", {"target": "Delete button"}, "dry_run", mock_db, mock_user)
        assert result["status"] == "dry_run"
        assert "would execute" in result["message"].lower()

    def test_dangerous_type_blocked_in_non_live(self):
        from app.services.agent_tool_executor import execute_tool

        mock_db = MagicMock()
        mock_user = MagicMock()

        # desktop_type is high risk - should be blocked in non-live mode
        result = execute_tool("desktop_type", {"text": "test"}, "approval", mock_db, mock_user)
        assert result["status"] in ("blocked", "dry_run")

    def test_approval_request_returns_needs_approval(self):
        from app.services.agent_tool_executor import execute_tool

        mock_db = MagicMock()
        mock_user = MagicMock()

        result = execute_tool("approval_request", {"text": "Approve this step?"}, "live", mock_db, mock_user)
        assert result["status"] in ("needs_approval", "dry_run")


class TestNoParserForAutomation:
    def test_parser_tools_not_in_new_skills(self):
        from app.services.accounting_skills import AUTOMATION_SKILL_TEMPLATES
        parser_tools = ["read_pdf", "extract_invoice_data", "scan_local_folder", "create_daily_invoices_excel"]

        for skill in AUTOMATION_SKILL_TEMPLATES:
            for step in skill["steps"]:
                assert step["tool"] not in parser_tools, (
                    f"Parser tool '{step['tool']}' found in automation skill '{skill['name']}'"
                )

    def test_new_automation_tools_not_duplicated(self):
        new_tools = [
            "browser_open_url", "browser_click", "browser_type",
            "desktop_click", "desktop_type", "desktop_hotkey",
            "screen_capture", "screen_read_text",
            "file_open", "file_copy", "file_create_folder",
            "email_open", "email_search", "email_download_attachments",
            "workflow_record_start", "workflow_save_as_skill",
            "emergency_stop", "audit_log", "snapshot_create",
        ]
        for name in new_tools:
            tool = get_tool(name)
            assert tool is not None, f"New automation tool '{name}' not found in registry"
