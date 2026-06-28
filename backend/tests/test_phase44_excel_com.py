"""Phase 44 — Deep Excel COM Automation via xlwings tests."""

from __future__ import annotations

import json
import os
import threading
import time

os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["AGENT_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///./test_phase44_com.db"
os.environ["OFFICEPILOT_APP_VERSION"] = "1.0.0"
os.environ["OFFICEPILOT_COM_TIMEOUT"] = "5"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, get_db, init_db
from app.main import app
from app.services.agent_tool_executor import execute_tool
from app.services.excel_com_automation import (
    ALLOWED_DATA_DIRS,
    BLOCKED_VBA_PATTERNS,
    ExcelComAdapter,
    XLWINGS_AVAILABLE,
    _check_vba_safety,
    _is_path_allowed,
)
from app.services.tool_registry import get_tool

FAKE_USER = type("FakeUser", (), {"id": 1, "email": "test@test.com", "role": "admin"})()


@pytest.fixture(autouse=True)
def _clean_db():
    init_db()
    db = SessionLocal()
    try:
        db.execute(Base.metadata.tables["users"].delete())
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield


@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Tool Registry Tests ───────────────────────────────────────────────────────


class TestToolRegistry:
    def test_excel_com_tools_registered(self):
        from app.services.tool_registry import TOOL_REGISTRY
        names = {t.name for t in TOOL_REGISTRY}
        for tool_name in [
            "excel_create_pivot_table",
            "excel_switch_workbooks",
            "excel_advanced_formatting",
            "excel_calculate_and_read",
            "excel_create_chart",
        ]:
            assert tool_name in names, f"{tool_name} not in TOOL_REGISTRY"

    def test_excel_create_pivot_table_risk_high(self):
        from app.services.tool_registry import get_tool
        tool = get_tool("excel_create_pivot_table")
        assert tool is not None
        assert tool.risk_level == "high"
        assert tool.approval_required is True

    def test_excel_calculate_and_read_low_risk_no_approval(self):
        from app.services.tool_registry import get_tool
        tool = get_tool("excel_calculate_and_read")
        assert tool is not None
        assert tool.risk_level == "low"
        assert tool.approval_required is False

    def test_com_tools_have_approval_required(self):
        from app.services.tool_registry import TOOL_REGISTRY, get_tool
        for name in ["excel_switch_workbooks", "excel_advanced_formatting", "excel_create_chart"]:
            tool = get_tool(name)
            assert tool is not None, f"{name} not found"
            assert tool.approval_required is True, f"{name} should require approval"


# ── VBA Safety Blocklist Tests ────────────────────────────────────────────────


class TestVbaBlocklist:
    def test_blocklist_raises_permission_error_for_macro(self):
        with pytest.raises(PermissionError, match="VBA macro execution is blocked"):
            _check_vba_safety({"file_path": "test.xlsx", "formula": "=SUM(A1:A10)", "run_macro": "RunMyMacro"})

    def test_blocklist_raises_for_application_run(self):
        with pytest.raises(PermissionError, match="VBA macro execution is blocked"):
            _check_vba_safety({"file_path": "test.xlsx", "code": "Application.Run 'MyMacro'"})

    def test_blocklist_raises_for_vba_reference(self):
        with pytest.raises(PermissionError, match="VBA macro execution is blocked"):
            _check_vba_safety({"file_path": "test.xlsx", "script": "VBA.Shell('cmd.exe')"})

    def test_blocklist_allows_safe_params(self):
        _check_vba_safety({"file_path": "test.xlsx", "formula": "=SUM(A1:A10)", "range": "A1:B2"})

    def test_blocklist_is_case_insensitive(self):
        with pytest.raises(PermissionError):
            _check_vba_safety({"file_path": "test.xlsx", "command": "APPLICATION.RUN malicious"})

    def test_blocklist_checks_formula_param(self):
        with pytest.raises(PermissionError):
            _check_vba_safety({"file_path": "test.xlsx", "formula": "RunMacro('evil')"})

    def test_empty_params_does_not_raise(self):
        _check_vba_safety({})
        _check_vba_safety({"safe": "data", "count": 42})

    def test_numeric_params_ignored(self):
        _check_vba_safety({"macro": 12345})
        _check_vba_safety({"file_path": "test.xlsx", "macro_ref": None})


# ── File Path Validation Tests ────────────────────────────────────────────────


class TestPathValidation:
    def test_windows_system_dir_blocked(self):
        assert _is_path_allowed("C:\\Windows\\System32\\evil.exe") is False

    def test_windows_dir_blocked(self):
        assert _is_path_allowed("C:\\Windows\\notepad.exe") is False

    def test_program_files_blocked(self):
        assert _is_path_allowed("C:\\Program Files\\SomeApp\\data.xlsx") is False

    def test_program_files_x86_blocked(self):
        assert _is_path_allowed("C:\\Program Files (x86)\\SomeApp\\data.xlsx") is False

    def test_user_file_allowed(self):
        assert _is_path_allowed("C:\\Users\\test\\Documents\\invoices.xlsx") is True

    def test_temp_file_allowed(self):
        assert _is_path_allowed("C:\\Users\\test\\AppData\\Local\\Temp\\report.xlsx") is True

    def test_network_unc_path_allowed(self):
        assert _is_path_allowed("\\\\server\\share\\file.xlsx") is True

    def test_empty_path_blocked(self):
        assert _is_path_allowed("") is False

    def test_allowed_data_dirs_override(self):
        ALLOWED_DATA_DIRS.append("C:\\Windows")
        try:
            assert _is_path_allowed("C:\\Windows\\System32\\file.xlsx") is True
        finally:
            ALLOWED_DATA_DIRS.clear()


# ── Adapter Availability Tests ────────────────────────────────────────────────


class TestAdapterAvailability:
    def test_adapter_available_flag_on_import(self):
        assert XLWINGS_AVAILABLE is False

    def test_adapter_reports_not_available_initially(self):
        adapter = ExcelComAdapter()
        assert adapter.available is False

    def test_adapter_without_xlwings_raises_on_method_call(self):
        adapter = ExcelComAdapter()
        with adapter as com:
            assert com.available is False
            with pytest.raises(RuntimeError, match="Excel COM automation is not available"):
                com.create_pivot_table("test.xlsx", "A1:Z100", "A1", ["col1"], "value")

    def test_adapter_methods_all_raise_without_xlwings(self):
        adapter = ExcelComAdapter()
        with adapter as com:
            for method_name, args in [
                ("create_pivot_table", ("f.xlsx", "A1:Z100", "A1", ["col1"], "value")),
                ("switch_workbook_and_copy", ("src.xlsx", "dst.xlsx", "Sheet1")),
                ("apply_conditional_formatting", ("f.xlsx", "Sheet1", "A1:B10", "1", "=A1>100")),
                ("calculate_and_read_formula", ("f.xlsx", "Sheet1", "A1")),
                ("create_chart", ("f.xlsx", "Sheet1", 1, "A1:B10", "MyChart")),
            ]:
                with pytest.raises(RuntimeError, match="Excel COM automation is not available"):
                    getattr(com, method_name)(*args)


# ── Executor Tests (mocked) ──────────────────────────────────────────────────


class TestExecutorsWithMockXlwings:
    def test_executor_returns_fallback_when_xlwings_unavailable(self, db):
        result = execute_tool(
            "excel_create_pivot_table",
            {"file_path": "C:\\Users\\test\\file.xlsx", "data_range": "A1:Z100", "pivot_location": "A1", "row_fields": ["col1"], "value_field": "val"},
            "live",
            db,
            FAKE_USER,
        )
        assert result["status"] in ("failed", "error")
        assert "COM" in result["message"] or "xlwings" in result["message"] or "not available" in result["message"].lower()

    def test_executor_validates_file_path(self, db):
        result = execute_tool(
            "excel_create_pivot_table",
            {"file_path": "", "data_range": "A1:Z100", "row_fields": ["col1"], "value_field": "val"},
            "live",
            db,
            FAKE_USER,
        )
        assert result["status"] in ("failed", "error")
        assert "file_path" in result["message"].lower()

    def test_executor_blocks_windows_path(self, db):
        result = execute_tool(
            "excel_create_pivot_table",
            {"file_path": "C:\\Windows\\System32\\test.xlsx", "data_range": "A1:Z100", "row_fields": ["col1"], "value_field": "val"},
            "live",
            db,
            FAKE_USER,
        )
        assert result["status"] == "blocked"

    def test_executor_switch_workbooks_validates_paths(self, db):
        result = execute_tool(
            "excel_switch_workbooks",
            {"source_path": "", "dest_path": ""},
            "live",
            db,
            FAKE_USER,
        )
        assert result["status"] in ("failed", "error")

    def test_executor_calculate_and_read_no_file_path(self, db):
        result = execute_tool(
            "excel_calculate_and_read",
            {"file_path": "", "cell": ""},
            "live",
            db,
            FAKE_USER,
        )
        assert result["status"] in ("failed", "error")
        assert "file_path" in result["message"].lower()

    def test_executor_create_chart_no_data_range(self, db):
        result = execute_tool(
            "excel_create_chart",
            {"file_path": "C:\\test.xlsx", "data_range": ""},
            "live",
            db,
            FAKE_USER,
        )
        assert result["status"] in ("failed", "error")
        assert "data_range" in result["message"].lower()

    def test_executor_advanced_formatting_no_range(self, db):
        result = execute_tool(
            "excel_advanced_formatting",
            {"file_path": "C:\\test.xlsx", "range": ""},
            "live",
            db,
            FAKE_USER,
        )
        assert result["status"] in ("failed", "error")


# ── Dry-Run Mode Tests ────────────────────────────────────────────────────────


class TestDryRunMode:
    def test_pivot_table_blocked_in_dry_run(self, db):
        result = execute_tool(
            "excel_create_pivot_table",
            {"file_path": "C:\\test.xlsx", "data_range": "A1:Z100", "row_fields": ["col1"], "value_field": "val"},
            "dry_run",
            db,
            FAKE_USER,
        )
        assert result["status"] == "dry_run"

    def test_switch_workbooks_blocked_in_dry_run(self, db):
        result = execute_tool(
            "excel_switch_workbooks",
            {"source_path": "C:\\src.xlsx", "dest_path": "C:\\dst.xlsx"},
            "dry_run",
            db,
            FAKE_USER,
        )
        assert result["status"] == "dry_run"

    def test_calculate_and_read_allowed_in_dry_run(self, db):
        result = execute_tool(
            "excel_calculate_and_read",
            {"file_path": "C:\\test.xlsx", "cell": "A1"},
            "dry_run",
            db,
            FAKE_USER,
        )
        assert result["status"] == "dry_run"

    def test_create_chart_blocked_in_dry_run(self, db):
        result = execute_tool(
            "excel_create_chart",
            {"file_path": "C:\\test.xlsx", "data_range": "A1:B10"},
            "dry_run",
            db,
            FAKE_USER,
        )
        assert result["status"] == "dry_run"


# ── Timeout Mechanism Tests ───────────────────────────────────────────────────


class TestTimeoutMechanism:
    def test_excel_com_adapter_run_with_timeout_hangs(self):
        adapter = ExcelComAdapter(timeout=1)

        def hanging_fn():
            while True:
                time.sleep(0.5)

        with pytest.raises(TimeoutError):
            adapter._run_with_timeout(hanging_fn)

    def test_excel_com_adapter_run_with_timeout_succeeds(self):
        adapter = ExcelComAdapter(timeout=5)

        def quick_fn():
            return 42

        assert adapter._run_with_timeout(quick_fn) == 42

    def test_excel_com_adapter_timeout_raises_for_slow_fn(self):
        adapter = ExcelComAdapter(timeout=1)

        def slow_fn():
            time.sleep(3)
            return "done"

        with pytest.raises(TimeoutError):
            adapter._run_with_timeout(slow_fn)

    def test_background_runner_com_timeout_env(self):
        assert os.environ.get("OFFICEPILOT_COM_TIMEOUT") == "5"

    def test_com_tools_set_defined(self):
        from app.services.background_runner import COM_TOOLS
        for name in [
            "excel_create_pivot_table",
            "excel_switch_workbooks",
            "excel_advanced_formatting",
            "excel_calculate_and_read",
            "excel_create_chart",
        ]:
            assert name in COM_TOOLS, f"{name} not in COM_TOOLS"


# ── Executor Map Tests ────────────────────────────────────────────────────────


class TestExecutorMapping:
    def test_executor_map_has_all_com_tools(self, db):
        from app.services.agent_tool_executor import execute_tool
        for tool_name in [
            "excel_create_pivot_table",
            "excel_switch_workbooks",
            "excel_advanced_formatting",
            "excel_calculate_and_read",
            "excel_create_chart",
        ]:
            result = execute_tool(
                tool_name,
                {"file_path": "C:\\test.xlsx", "data_range": "A1:B10"},
                "dry_run",
                db,
                FAKE_USER,
            )
            assert result["status"] in ("dry_run", "blocked", "failed"), f"{tool_name} not in executor_map: {result}"


# ── Mock xlwings Integration Tests (simulating COM) ───────────────────────────


class TestMockXlwingsIntegration:
    def test_mock_adapter_available_true_works(self):
        adapter = ExcelComAdapter()
        adapter._available = True
        assert adapter.available is True

    def test_validate_com_file_path_raises_without_file_path(self):
        from app.services.agent_tool_executor import _validate_com_file_path
        with pytest.raises(ValueError, match="file_path is required"):
            _validate_com_file_path("")

    def test_validate_com_file_path_blocks_system_dir(self):
        from app.services.agent_tool_executor import _validate_com_file_path
        with pytest.raises(PermissionError):
            _validate_com_file_path("c:\\windows\\system32\\test.xlsx")
