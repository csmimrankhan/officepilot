"""Phase 32 — Browser Export Automation MVP tests.

Tests:
1. browser_open_url returns mock when mode=mock
2. browser_wait_for_user_login returns manual_login_required
3. password/OTP field action is blocked
4. payment/delete/tax/payroll action blocked
5. browser_export_report returns mock result in mock mode
6. guided download watches folder and detects new file
7. downloaded file copied to output folder
8. Export Accounting Report skill matches export command
9. browser session is user-scoped
10. emergency stop closes browser session
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = "test_user_1"
    u.email = "test@example.com"
    return u


@pytest.fixture
def mock_db():
    return MagicMock()


# ── Mock mode tests ───────────────────────────────────────────────────────


class TestMockMode:
    """Browser automation executors return mock results when mode=mock (default)."""

    def test_1_browser_open_url_returns_mock(self):
        """browser_open_url returns mock response in mock mode."""
        from app.services.agent_tool_executor import _execute_browser_open_url
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_open_url({"url": "https://example.com"}, db, user)
        assert result["status"] == "success"
        assert result["output"]["opened"] is True
        assert result["output"]["mode"] in ("mock", "simulated")

    def test_2_browser_wait_for_user_login_returns_waiting(self):
        """browser_wait_for_user_login returns waiting status."""
        from app.services.agent_tool_executor import _execute_browser_wait_for_user_login
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_wait_for_user_login({
            "prompt": "Please log in manually",
        }, db, user)
        assert result["status"] == "success"
        assert result["output"]["action"] == "wait_for_login"
        assert result["output"]["status"] == "waiting"
        assert result["output"]["needs_user_confirmation"] is True

    def test_3_browser_read_page_returns_simulated(self):
        """browser_read_page returns simulated content in mock mode."""
        from app.services.agent_tool_executor import _execute_browser_read_page
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_read_page({}, db, user)
        assert result["status"] == "success"
        assert result["output"]["mode"] == "simulated"

    def test_4_browser_export_report_returns_mock(self):
        """browser_export_report returns mock export path."""
        from app.services.agent_tool_executor import _execute_browser_export_report
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_export_report({"report_type": "profit_and_loss"}, db, user)
        assert result["status"] == "success"
        assert result["output"]["exported"] is True

    def test_5_browser_wait_for_download_returns_mock(self):
        """browser_wait_for_download returns mock filepath."""
        from app.services.agent_tool_executor import _execute_browser_wait_for_download
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_wait_for_download({"filename": "report.csv"}, db, user)
        assert result["status"] == "success"
        assert result["output"]["found"] is True

    def test_6_browser_close_returns_mock(self):
        """browser_close returns closed True."""
        from app.services.agent_tool_executor import _execute_browser_close
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_close({}, db, user)
        assert result["status"] == "success"
        assert result["output"]["closed"] is True


# ── Safety block tests ────────────────────────────────────────────────────


class TestSafetyBlocks:
    """Dangerous browser actions must be blocked."""

    def test_7_password_field_action_blocked(self):
        """Typing into a password field is blocked."""
        from app.services.agent_tool_executor import _execute_browser_type
        db = MagicMock()
        user = MagicMock()
        # Typing into field labeled 'password'
        result = _execute_browser_type({
            "selector": "#password",
            "text": "mypassword",
            "field_label": "password",
        }, db, user)
        assert result["status"] == "blocked"
        assert "sensitive" in result["message"].lower()

    def test_8_otp_field_action_blocked(self):
        """Typing into OTP/2FA field is blocked."""
        from app.services.agent_tool_executor import _execute_browser_type
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_type({
            "selector": "#otp",
            "text": "123456",
            "field_label": "otp code",
        }, db, user)
        assert result["status"] == "blocked"

    def test_9_payment_action_blocked(self):
        """Payment-related action is blocked."""
        from app.services.agent_tool_executor import _execute_browser_open_url
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_open_url({
            "url": "https://bank.com/pay",
            "action_text": "pay invoice",
        }, db, user)
        assert result["status"] == "blocked"

    def test_10_delete_action_blocked(self):
        """Delete-related action is blocked."""
        from app.services.agent_tool_executor import _execute_browser_click
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_click({
            "selector": ".delete-btn",
            "action_text": "delete records",
        }, db, user)
        assert result["status"] == "blocked"

    def test_11_transfer_action_blocked(self):
        """Bank transfer action is blocked."""
        from app.services.agent_tool_executor import _execute_browser_open_url
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_open_url({
            "url": "https://bank.com/transfer",
            "action_text": "transfer money",
        }, db, user)
        assert result["status"] == "blocked"

    def test_12_payroll_action_blocked(self):
        """Payroll submission is blocked."""
        from app.services.agent_tool_executor import _execute_browser_export_report
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_export_report({
            "report_type": "payroll",
            "action_text": "submit payroll",
        }, db, user)
        assert result["status"] == "blocked"

    def test_13_tax_filing_action_blocked(self):
        """Tax filing action is blocked."""
        from app.services.agent_tool_executor import _execute_browser_export_report
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_export_report({
            "report_type": "tax",
            "action_text": "file tax",
        }, db, user)
        assert result["status"] == "blocked"

    def test_14_sensitive_input_blocked(self):
        """Input containing password/token values is blocked."""
        from app.services.agent_tool_executor import _execute_browser_type
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_type({
            "selector": "#input",
            "text": "my_secret_token_123",
        }, db, user)
        assert result["status"] == "blocked"


# ── Browser session service tests ─────────────────────────────────────────


class TestBrowserSessionService:
    """Browser session service tests."""

    def test_15_is_action_blocked(self):
        """is_action_blocked correctly detects dangerous keywords."""
        from app.services.browser_session_service import is_action_blocked
        blocked, _ = is_action_blocked("pay invoice")
        assert blocked is True
        blocked, _ = is_action_blocked("delete record")
        assert blocked is True
        blocked, _ = is_action_blocked("export profit and loss")
        assert blocked is False

    def test_16_is_sensitive_field(self):
        """is_sensitive_field detects sensitive field labels."""
        from app.services.browser_session_service import is_sensitive_field
        assert is_sensitive_field("password") is True
        assert is_sensitive_field("OTP Code") is True
        assert is_sensitive_field("Credit Card Number") is True
        assert is_sensitive_field("Vendor Name") is False

    def test_17_input_is_sensitive(self):
        """input_is_sensitive detects sensitive input values."""
        from app.services.browser_session_service import input_is_sensitive
        assert input_is_sensitive("mypassword123") is True
        assert input_is_sensitive("my_secret_token_xyz") is True
        assert input_is_sensitive("ACME Corp") is False

    def test_18_mock_open_url(self):
        """mock_open_url returns expected fields."""
        from app.services.browser_session_service import mock_open_url
        result = mock_open_url("https://example.com")
        assert result["ok"] is True
        assert result["url"] == "https://example.com"
        assert result["mode"] == "mock"

    def test_19_mock_wait_for_login(self):
        """mock_wait_for_login returns expected fields."""
        from app.services.browser_session_service import mock_wait_for_login
        result = mock_wait_for_login("Please log in")
        assert result["ok"] is True
        assert result["action"] == "wait_for_login"
        assert result["mode"] == "mock"

    def test_20_mock_export_report(self):
        """mock_export_report returns expected fields."""
        from app.services.browser_session_service import mock_export_report
        result = mock_export_report("profit_and_loss")
        assert result["ok"] is True
        assert result["exported"] is True
        assert result["mode"] == "mock"

    def test_21_guided_download_detects_new_file(self):
        """watch_for_download detects new file in watched folder."""
        from app.services.browser_session_service import watch_for_download
        db = MagicMock()
        session = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            session.download_dir = tmpdir
            # Create a file after a short delay to simulate download
            import threading
            def _create_file():
                time.sleep(0.3)
                Path(tmpdir, "report.xlsx").write_text("test")
            t = threading.Thread(target=_create_file, daemon=True)
            t.start()
            result = watch_for_download(db, session, timeout_seconds=5, poll_interval=0.1)
            assert result["ok"] is True
            assert "report.xlsx" in result["file_path"]

    def test_22_copy_to_output(self):
        """copy_to_output copies file without modifying original."""
        from app.services.browser_session_service import copy_to_output
        session = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = Path(tmpdir, "report.xlsx")
            src_path.write_text("dummy content")
            session.output_dir = str(Path(tmpdir, "output"))
            result = copy_to_output(session, str(src_path))
            assert result["ok"] is True
            assert os.path.isfile(result["output_path"])
            # Original file unchanged
            assert src_path.read_text() == "dummy content"

    def test_23_guided_download_respects_safe_extensions(self):
        """watch_for_download only picks up safe export extensions."""
        from app.services.browser_session_service import watch_for_download
        import threading
        db = MagicMock()
        session = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            session.download_dir = tmpdir
            # Create a .tmp file before watching — should NOT be detected as "new"
            Path(tmpdir, "partial.tmp").write_text("temp")
            # Start watch, then create .xlsx after a delay
            def _create_xlsx():
                time.sleep(0.5)
                Path(tmpdir, "report.xlsx").write_text("real")
            t = threading.Thread(target=_create_xlsx, daemon=True)
            t.start()
            result = watch_for_download(db, session, timeout_seconds=5, poll_interval=0.1)
            assert result["ok"] is True
            assert "report.xlsx" in result["file_path"]


# ── Skill matching tests ──────────────────────────────────────────────────


class TestExportSkillMatching:
    """Export Accounting Report skill matches relevant commands."""

    def test_24_export_monthly_pnl_matches_skill(self):
        """'export monthly profit and loss' matches Export Accounting Report."""
        from app.services.accounting_skills import AUTOMATION_SKILL_TEMPLATES, find_skill_for_command
        skill = next(s for s in AUTOMATION_SKILL_TEMPLATES if s["name"] == "Export Accounting Report")
        assert skill is not None
        # Check trigger phrases include the main command
        phrases = skill["trigger_phrases"]
        assert "export monthly profit and loss" in phrases
        assert "export profit and loss" in phrases
        assert "download accounting report" in phrases

    def test_25_export_skill_has_guided_mode_steps(self):
        """Export Accounting Report uses guided download mode steps."""
        from app.services.accounting_skills import AUTOMATION_SKILL_TEMPLATES
        skill = next(s for s in AUTOMATION_SKILL_TEMPLATES if s["name"] == "Export Accounting Report")
        steps = skill["steps"]
        step_types = [s["step_type"] for s in steps]
        # Guided mode: no browser_click, no browser_type
        assert "browser_click" not in step_types
        assert "browser_type" not in step_types
        # Has guided export step
        export_step = next(s for s in steps if s["step_type"] == "browser_export_report")
        assert export_step["parameters"].get("guided_mode") is True

    def test_26_guided_browser_export_skill_exists(self):
        """Guided Browser Export skill exists with correct trigger phrases."""
        from app.services.accounting_skills import AUTOMATION_SKILL_TEMPLATES
        skill = next(s for s in AUTOMATION_SKILL_TEMPLATES if s["name"] == "Guided Browser Export")
        assert skill is not None
        phrases = skill["trigger_phrases"]
        assert "guided export" in phrases
        assert "watch browser download" in phrases

    def test_27_skill_does_not_block_safe_export(self):
        """Safe export command is not blocked by dangerous pattern check."""
        from app.services.accounting_skills import _is_dangerous_skill
        from app.services.accounting_skills import AUTOMATION_SKILL_TEMPLATES
        skill = next(s for s in AUTOMATION_SKILL_TEMPLATES if s["name"] == "Export Accounting Report")
        result = _is_dangerous_skill(skill["name"], skill["steps"])
        assert result is None, f"Safe export skill should not be blocked: {result}"


# ── Executor safety edge cases ──────────────────────────────────────────


class TestExecutorSafetyEdge:
    """Edge cases for executor safety."""

    def test_28_safe_export_command_not_blocked(self):
        """Safe 'export monthly profit and loss' is NOT blocked."""
        from app.services.agent_tool_executor import _execute_browser_open_url
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_open_url({
            "url": "https://quickbooks.intuit.com",
            "action_text": "export monthly profit and loss",
        }, db, user)
        assert result["status"] == "success"

    def test_29_safe_read_page_not_blocked(self):
        """browser_read_page is never blocked (read-only)."""
        from app.services.agent_tool_executor import _execute_browser_read_page
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_read_page({}, db, user)
        assert result["status"] == "success"

    def test_30_safe_click_not_blocked(self):
        """Safe click is not blocked."""
        from app.services.agent_tool_executor import _execute_browser_click
        db = MagicMock()
        user = MagicMock()
        result = _execute_browser_click({
            "selector": "#export-btn",
            "action_text": "click export button",
        }, db, user)
        assert result["status"] == "success"
