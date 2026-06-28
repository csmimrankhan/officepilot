"""Phase 45B — Voice-Driven Live Excel Editing (Active Workbook COM) tests."""

from __future__ import annotations

import json
import os
import tempfile

os.environ["ALLOW_OPEN_REGISTRATION"] = "true"
os.environ["AGENT_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///./test_phase45b_live.db"
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
    LIVE_EDIT_SNAPSHOT_DIR,
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
    def test_live_excel_tool_registered(self):
        names = {t.name for t in __import__("app.services.tool_registry", fromlist=["TOOL_REGISTRY"]).TOOL_REGISTRY}
        assert "excel_live_edit_active_workbook" in names

    def test_live_excel_tool_high_risk(self):
        tool = get_tool("excel_live_edit_active_workbook")
        assert tool is not None
        assert tool.risk_level == "high"
        assert tool.approval_required is True
        assert tool.snapshot_required is True

    def test_live_excel_tool_has_input_schema(self):
        tool = get_tool("excel_live_edit_active_workbook")
        assert tool.input_schema is not None
        schema = tool.input_schema
        assert "command_type" in schema.get("properties", {})
        assert "params" in schema.get("properties", {})
        ct_props = schema["properties"]["command_type"]
        assert "enum" in ct_props
        assert "format_range" in ct_props["enum"]
        assert "write_values" in ct_props["enum"]
        assert "read_range" in ct_props["enum"]
        assert "list_sheets" in ct_props["enum"]
        assert schema.get("required") == ["command_type", "params"]


# ── VBA Safety Blocklist Tests (reused from Phase 44) ─────────────────────────


class TestVbaBlocklist:
    def test_blocklist_raises_permission_error_for_macro(self):
        with pytest.raises(PermissionError, match="VBA macro execution is blocked"):
            _check_vba_safety({"range": "A1", "formula": "RunMacro('evil')"})

    def test_blocklist_allows_safe_params(self):
        _check_vba_safety({"range": "A1:B10", "value": "hello", "font_color": "#FF0000"})

    def test_blocklist_empty_params(self):
        _check_vba_safety({})


# ── File Path Validation Tests ────────────────────────────────────────────────


class TestPathValidation:
    def test_windows_system_dir_blocked(self):
        assert _is_path_allowed("C:\\Windows\\System32\\evil.exe") is False

    def test_user_file_allowed(self):
        assert _is_path_allowed("C:\\Users\\test\\Documents\\invoices.xlsx") is True


# ── Adapter Availability Tests (without xlwings) ──────────────────────────────


class TestAdapterWithoutXlwings:
    def test_adapter_reports_not_available(self):
        adapter = ExcelComAdapter()
        assert adapter.available is False

    def test_connect_to_active_workbook_raises_without_xlwings(self):
        adapter = ExcelComAdapter()
        with adapter as com:
            assert com.available is False
            with pytest.raises(RuntimeError, match="xlwings is not available"):
                com.connect_to_active_workbook()

    def test_execute_live_command_raises_without_connection(self):
        adapter = ExcelComAdapter()
        with adapter as com:
            with pytest.raises(RuntimeError, match="Excel COM automation is not available"):
                com.execute_live_command("format_range", {"range": "A1"})


# ── Executor Tests (without xlwings) ──────────────────────────────────────────


class TestExecutorWithoutXlwings:
    def test_executor_returns_fallback_when_xlwings_unavailable(self, db):
        result = execute_tool(
            "excel_live_edit_active_workbook",
            {"command_type": "format_range", "params": {"range": "A1:B10", "font_bold": True}},
            "live",
            db,
            FAKE_USER,
        )
        assert result["status"] in ("failed", "error")
        message = result.get("message", "").lower()
        assert any(kw in message for kw in ["not available", "xlwings", "com", "no active excel"])

    def test_executor_fails_without_command_type(self, db):
        result = execute_tool(
            "excel_live_edit_active_workbook",
            {"params": {}},
            "live",
            db,
            FAKE_USER,
        )
        assert result["status"] in ("failed", "error")
        assert "command_type" in result.get("message", "").lower()

    def test_executor_blocks_in_dry_run_mode(self, db):
        result = execute_tool(
            "excel_live_edit_active_workbook",
            {"command_type": "format_range", "params": {"range": "A1"}},
            "dry_run",
            db,
            FAKE_USER,
        )
        assert result["status"] == "dry_run"


# ── Adapter Tests with Mocked xlwings ─────────────────────────────────────────


class TestAdapterWithMockXlwings:
    def test_connect_active_workbook_no_apps(self):
        adapter = ExcelComAdapter()
        adapter._available = True
        fake_xw = type("FakeXw", (), {})
        fake_xw.apps = type("FakeApps", (), {"active": None})()
        adapter._xw = fake_xw
        with pytest.raises(RuntimeError, match="No active Excel window"):
            adapter.connect_to_active_workbook()

    def test_connect_active_workbook_success(self):
        adapter = ExcelComAdapter()
        adapter._available = True
        mock_sheet = type("MockSheet", (), {"name": "Sheet1", "activate": lambda self: None})()
        mock_wb = type("MockWb", (), {"name": "Book1.xlsx", "sheets": type("Sheets", (), {"active": mock_sheet, "__getitem__": lambda self, k: mock_sheet, "__iter__": lambda self: iter([mock_sheet])})(), "save": lambda self, path: None})()
        mock_active_app = type("MockApp", (), {"screen_updating": True, "books": type("Books", (), {"active": mock_wb})()})
        fake_xw = type("FakeXw", (), {})
        fake_xw.apps = type("FakeApps", (), {"active": mock_active_app})()
        adapter._xw = fake_xw
        adapter._app = mock_active_app
        result = adapter.connect_to_active_workbook()
        assert result["status"] == "ok"
        assert result["workbook_name"] == "Book1.xlsx"
        assert result["sheet_name"] == "Sheet1"
        assert result["undo_available"] is True

    def test_connect_sets_screen_updating_false(self):
        adapter = ExcelComAdapter()
        adapter._available = True
        calls = []
        class MockActiveApp:
            pass
        app = MockActiveApp()
        type(app).screen_updating = property(lambda self_: calls.append("get") or True, lambda self_, val: calls.append(("set", val)))
        app.books = type("Books", (), {"active": type("MockWb", (), {"name": "Book1.xlsx", "sheets": type("Sheets", (), {"active": type("MockSheet", (), {"name": "Sheet1", "activate": lambda self_: None})(), "__getitem__": lambda self_, k: None, "__iter__": lambda self_: iter([])})(), "save": lambda self_, path: None})()})
        fake_xw = type("FakeXw", (), {})
        fake_xw.apps = type("FakeApps", (), {"active": app})()
        adapter._xw = fake_xw
        adapter._app = app
        result = adapter.connect_to_active_workbook()
        assert result["status"] == "ok"
        assert any(c == ("set", False) for c in calls), "screen_updating was not set to False"

    def test_execute_live_command_no_active_book(self):
        adapter = ExcelComAdapter()
        adapter._available = True
        adapter._app = type("MockApp", (), {"books": type("Books", (), {"active": None})(), "screen_updating": True})()
        with pytest.raises(RuntimeError, match="No active workbook"):
            adapter.execute_live_command("set_value", {"range": "A1", "value": "test"})

    def test_execute_live_command_format_range(self):
        adapter = ExcelComAdapter()
        adapter._available = True
        mock_cell_range = type("MockRange", (), {
            "api": type("MockApi", (), {
                "Font": type("MockFont", (), {"Bold": False, "Color": 0, "Size": 11})(),
                "Interior": type("MockInterior", (), {"Color": 0})(),
            })(),
            "value": None,
            "clear_contents": lambda self: None,
        })()
        mock_sheet = type("MockSheet", (), {
            "name": "Sheet1",
            "range": lambda self, addr: mock_cell_range,
            "activate": lambda self: None,
            "api": type("MockSheetApi", (), {"ActiveCell": type("MockCell", (), {"Address": "$A$1", "Value": "test"})()}),
            "charts": type("MockCharts", (), {"add": lambda self: type("MockChart", (), {"chart_type": None, "set_source_data": lambda self, rng: None, "name": ""})()}),
        })()
        mock_wb = type("MockWb", (), {
            "name": "Book1.xlsx",
            "sheets": type("Sheets", (), {
                "active": mock_sheet,
                "add": lambda self, after: mock_sheet,
                "__getitem__": lambda self, k: mock_sheet,
                "__iter__": lambda self: iter([mock_sheet]),
            })(),
            "save": lambda self, path=None: None,
        })()
        mock_active_app = type("MockApp", (), {"screen_updating": False, "books": type("Books", (), {"active": mock_wb})()})
        adapter._app = mock_active_app

        result = adapter.execute_live_command("format_range", {"range": "A1:B10", "font_bold": True, "font_color": "#FF0000", "font_size": 14})
        assert result["status"] == "ok"
        assert result["command_type"] == "format_range"

    def test_execute_live_command_set_value(self):
        adapter = ExcelComAdapter()
        adapter._available = True
        written_value = [None]
        class MockRange:
            def __init__(self):
                self.api = type("MockApi", (), {
                    "Font": type("MockFont", (), {"Bold": False, "Color": 0, "Size": 11})(),
                    "Interior": type("MockInterior", (), {"Color": 0})(),
                    "Formula": None,
                })
                self._value = None
            @property
            def value(self):
                return self._value
            @value.setter
            def value(self, v):
                self._value = v
                written_value[0] = v
            def clear_contents(self):
                pass
        mock_range = MockRange()
        mock_sheet = type("MockSheet", (), {
            "name": "Sheet1",
            "activate": lambda self_: None,
            "api": type("MockSheetApi", (), {"ActiveCell": type("MockCell", (), {"Address": "$A$1", "Value": "test"})()}),
            "charts": type("MockCharts", (), {"add": lambda self_: type("MockChart", (), {"chart_type": None, "set_source_data": lambda self_, rng: None, "name": ""})()}),
            "range": lambda self_, addr: mock_range,
        })()
        mock_wb = type("MockWb", (), {
            "name": "Book1.xlsx",
            "sheets": type("Sheets", (), {
                "active": mock_sheet,
                "add": lambda self_, after: mock_sheet,
                "__getitem__": lambda self_, k: mock_sheet,
                "__iter__": lambda self_: iter([mock_sheet]),
            })(),
            "save": lambda self_, path=None: None,
        })()
        mock_active_app = type("MockApp", (), {"screen_updating": False, "books": type("Books", (), {"active": mock_wb})()})
        adapter._app = mock_active_app

        result = adapter.execute_live_command("set_value", {"range": "C5", "value": "42"})
        assert result["status"] == "ok"
        assert result["command_type"] == "set_value"

    def test_execute_live_command_list_sheets(self):
        adapter = ExcelComAdapter()
        adapter._available = True
        mock_sheet1 = type("MockSheet", (), {"name": "Sheet1", "activate": lambda self: None, "api": type("MockSheetApi", (), {"ActiveCell": type("MockCell", (), {"Address": "$A$1", "Value": "test"})()}), "charts": type("MockCharts", (), {"add": lambda self: type("MockChart", (), {"chart_type": None, "set_source_data": lambda self, rng: None, "name": ""})()}), "range": lambda self, addr: type("MockRange", (), {"api": type("MockApi", (), {"Font": type("MockFont", (), {"Bold": False, "Color": 0, "Size": 11})(), "Interior": type("MockInterior", (), {"Color": 0})(), "FormatConditions": type("MockFC", (), {"Delete": lambda self: None, "Add": lambda self, Type, Formula1: type("MockFCItem", (), {"Interior": type("MockInterior", (), {"Color": 0})(), "Font": type("MockFont", (), {"Color": 0})()})()})()}), "value": None, "clear_contents": lambda self: None})()})()
        mock_sheet2 = type("MockSheet", (), {"name": "Data", "activate": lambda self: None, "api": type("MockSheetApi", (), {"ActiveCell": type("MockCell", (), {"Address": "$A$1", "Value": "test"})()}), "charts": type("MockCharts", (), {"add": lambda self: type("MockChart", (), {"chart_type": None, "set_source_data": lambda self, rng: None, "name": ""})()}), "range": lambda self, addr: type("MockRange", (), {"api": type("MockApi", (), {"Font": type("MockFont", (), {"Bold": False, "Color": 0, "Size": 11})(), "Interior": type("MockInterior", (), {"Color": 0})(), "FormatConditions": type("MockFC", (), {"Delete": lambda self: None, "Add": lambda self, Type, Formula1: type("MockFCItem", (), {"Interior": type("MockInterior", (), {"Color": 0})(), "Font": type("MockFont", (), {"Color": 0})()})()})()}), "value": None, "clear_contents": lambda self: None})()})()
        mock_wb = type("MockWb", (), {
            "name": "Book1.xlsx",
            "sheets": type("Sheets", (), {
                "active": mock_sheet1,
                "add": lambda self, after: mock_sheet1,
                "__getitem__": lambda self, k: mock_sheet1,
                "__iter__": lambda self: iter([mock_sheet1, mock_sheet2]),
            })(),
            "save": lambda self, path=None: None,
        })()
        mock_active_app = type("MockApp", (), {"screen_updating": False, "books": type("Books", (), {"active": mock_wb})()})
        adapter._app = mock_active_app

        result = adapter.execute_live_command("list_sheets", {})
        assert result["status"] == "ok"
        assert result["command_type"] == "list_sheets"
        assert "Sheet1" in result["sheets"]
        assert "Data" in result["sheets"]

    def test_execute_live_command_unsupported_type(self):
        adapter = ExcelComAdapter()
        adapter._available = True
        mock_sheet = type("MockSheet", (), {"name": "Sheet1", "activate": lambda self: None})()
        mock_wb = type("MockWb", (), {
            "name": "Book1.xlsx",
            "sheets": type("Sheets", (), {"active": mock_sheet, "__getitem__": lambda self, k: mock_sheet, "__iter__": lambda self: iter([mock_sheet])})(),
            "save": lambda self, path=None: None,
        })()
        mock_active_app = type("MockApp", (), {"screen_updating": False, "books": type("Books", (), {"active": mock_wb})()})
        adapter._app = mock_active_app

        result = adapter.execute_live_command("nonexistent_command", {})
        assert result["status"] == "failed"
        assert "Unsupported" in result["message"]

    def test_execute_live_command_clear_range(self):
        adapter = ExcelComAdapter()
        adapter._available = True
        cleared = [False]
        mock_range = type("MockRange", (), {
            "api": type("MockApi", (), {"Font": type("MockFont", (), {"Bold": False, "Color": 0, "Size": 11})(), "Interior": type("MockInterior", (), {"Color": 0})()}),
            "value": None,
            "clear_contents": lambda self: cleared.__setitem__(0, True),
        })()
        mock_sheet = type("MockSheet", (), {
            "name": "Sheet1",
            "range": lambda self, addr: mock_range,
            "activate": lambda self: None,
            "api": type("MockSheetApi", (), {"ActiveCell": type("MockCell", (), {"Address": "$A$1", "Value": "test"})()}),
            "charts": type("MockCharts", (), {"add": lambda self: type("MockChart", (), {"chart_type": None, "set_source_data": lambda self, rng: None, "name": ""})()}),
        })()
        mock_wb = type("MockWb", (), {
            "name": "Book1.xlsx",
            "sheets": type("Sheets", (), {"active": mock_sheet, "add": lambda self, after: mock_sheet, "__getitem__": lambda self, k: mock_sheet, "__iter__": lambda self: iter([mock_sheet])})(),
            "save": lambda self, path=None: None,
        })()
        mock_active_app = type("MockApp", (), {"screen_updating": False, "books": type("Books", (), {"active": mock_wb})()})
        adapter._app = mock_active_app

        result = adapter.execute_live_command("clear_range", {"range": "D1:D10"})
        assert result["status"] == "ok"
        assert result["command_type"] == "clear_range"
        assert cleared[0] is True

    def test_execute_live_command_activate_sheet(self):
        adapter = ExcelComAdapter()
        adapter._available = True
        activated = [False]
        mock_sheet = type("MockSheet", (), {
            "name": "Sheet1",
            "activate": lambda self: activated.__setitem__(0, True),
            "api": type("MockSheetApi", (), {"ActiveCell": type("MockCell", (), {"Address": "$A$1", "Value": "test"})()}),
            "charts": type("MockCharts", (), {"add": lambda self: type("MockChart", (), {"chart_type": None, "set_source_data": lambda self, rng: None, "name": ""})()}),
            "range": lambda self, addr: type("MockRange", (), {"api": type("MockApi", (), {"Font": type("MockFont", (), {"Bold": False, "Color": 0, "Size": 11})(), "Interior": type("MockInterior", (), {"Color": 0})()}), "value": None, "clear_contents": lambda self: None})(),
        })()
        mock_wb = type("MockWb", (), {
            "name": "Book1.xlsx",
            "sheets": type("Sheets", (), {"active": mock_sheet, "add": lambda self, after: mock_sheet, "__getitem__": lambda self, k: type("MockSheet", (), {"name": k, "activate": lambda self: None})(), "__iter__": lambda self: iter([mock_sheet])})(),
            "save": lambda self, path=None: None,
        })()
        mock_active_app = type("MockApp", (), {"screen_updating": False, "books": type("Books", (), {"active": mock_wb})()})
        adapter._app = mock_active_app

        result = adapter.execute_live_command("activate_sheet", {"sheet_name": "Sheet1"})
        assert result["status"] == "ok"

    def test_parse_color_hex_string(self):
        color = ExcelComAdapter._parse_color("#FF0000")
        assert color == 0x0000FF

    def test_parse_color_int(self):
        color = ExcelComAdapter._parse_color(0xFF0000)
        assert color == 0xFF0000

    def test_parse_color_invalid_string(self):
        color = ExcelComAdapter._parse_color("invalid")
        assert color == 0


# ── Voice Intent Detection Tests ──────────────────────────────────────────────


class TestVoiceIntentDetection:
    def test_intent_edit_this_excel(self):
        from app.services.accountant_autopilot import build_accountant_plan
        plan = build_accountant_plan(None, "edit this excel sheet and format column A", FAKE_USER, force_new_plan=True)
        assert plan["task_type"] == "live_excel_edit"
        assert plan["risk_level"] == "high"
        assert plan["requires_approval"] is True
        assert plan["live_excel_mode"] is True

    def test_intent_change_this_sheet(self):
        from app.services.accountant_autopilot import build_accountant_plan
        plan = build_accountant_plan(None, "change this sheet colors", FAKE_USER, force_new_plan=True)
        assert plan["task_type"] == "live_excel_edit"

    def test_intent_format_active_workbook(self):
        from app.services.accountant_autopilot import build_accountant_plan
        plan = build_accountant_plan(None, "format the active workbook header row", FAKE_USER, force_new_plan=True)
        assert plan["task_type"] == "live_excel_edit"

    def test_intent_active_excel_edit_karo(self):
        from app.services.accountant_autopilot import build_accountant_plan
        plan = build_accountant_plan(None, "active excel mein format karo", FAKE_USER, force_new_plan=True)
        assert plan["task_type"] == "live_excel_edit"

    def test_intent_is_excel_mein_edit(self):
        from app.services.accountant_autopilot import build_accountant_plan
        plan = build_accountant_plan(None, "is excel mein edit karo", FAKE_USER, force_new_plan=True)
        assert plan["task_type"] == "live_excel_edit"

    def test_intent_live_excel_edit(self):
        from app.services.accountant_autopilot import build_accountant_plan
        plan = build_accountant_plan(None, "live excel edit", FAKE_USER, force_new_plan=True)
        assert plan["task_type"] == "live_excel_edit"

    def test_intent_step_has_high_risk(self):
        from app.services.accountant_autopilot import build_accountant_plan
        plan = build_accountant_plan(None, "edit this excel", FAKE_USER, force_new_plan=True)
        steps = plan.get("steps", [])
        assert len(steps) >= 1
        for step in steps:
            if step.get("tool") == "excel_live_edit_active_workbook":
                assert step["risk_level"] == "high"
                assert step["requires_approval"] is True
                break
        else:
            pytest.fail("No excel_live_edit_active_workbook step found")

    def test_normal_excel_command_not_caught(self):
        from app.services.accountant_autopilot import build_accountant_plan
        plan = build_accountant_plan(None, "create an excel summary", FAKE_USER, force_new_plan=True)
        assert plan.get("task_type") != "live_excel_edit"


# ── High-Risk Dry-Run Safety Tests ────────────────────────────────────────────


class TestHighRiskDryRunSafety:
    def test_live_excel_tool_blocked_in_dry_run(self, db):
        result = execute_tool(
            "excel_live_edit_active_workbook",
            {"command_type": "format_range", "params": {"range": "A1"}},
            "dry_run",
            db,
            FAKE_USER,
        )
        assert result["status"] == "dry_run"

    def test_live_excel_tool_allowed_in_live(self, db):
        result = execute_tool(
            "excel_live_edit_active_workbook",
            {"command_type": "format_range", "params": {"range": "A1"}},
            "live",
            db,
            FAKE_USER,
        )
        assert result["status"] in ("failed", "error")
        assert "xlwings" in result.get("message", "").lower() or "COM" in result.get("message", "")



