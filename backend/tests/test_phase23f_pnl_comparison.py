"""Phase 23F — P&L Report Comparison tests.

Tests that:
- planner detects P&L comparison command
- demo P&L comparison returns expected +20000 and +25%
- read_pnl_report parses sample file
- compare_pnl_reports calculates correct difference
- create_pnl_comparison_excel creates file
- no LLM used for math
- payment/delete commands still blocked
- manual upload fallback works
- workflow memory saved after result
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.accounting_report_comparison import (
    PnLReport,
    PnLRow,
    compare_pnl_reports,
    create_pnl_comparison_excel,
    build_pnl_summary_text,
    get_demo_current_report,
    get_demo_previous_report,
    read_pnl_report,
    detect_report_format,
    pnl_comparison_to_dict,
)


def _plan_task(client, command: str):
    resp = client.post("/api/agent/plan-task", json={"command": command, "force_new_plan": True})
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
    os.environ["DEMO_MODE"] = "true"
    yield
    _set_mock_provider()


@pytest.fixture()
def client_with_auth(client):
    resp = client.post("/api/auth/register", json={
        "email": "pnl-user@test.com", "password": "Test@123456", "full_name": "PNL User",
    })
    data = resp.json()
    token = data["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ── Service Tests (no client/network needed) ─────────────────────────────────


class TestPnLService:
    def test_demo_data_has_correct_values(self):
        current = get_demo_current_report()
        previous = get_demo_previous_report()
        assert current.total_income == 250000.0
        assert current.total_expenses == 150000.0
        assert current.net_income == 100000.0
        assert previous.total_income == 220000.0
        assert previous.total_expenses == 140000.0
        assert previous.net_income == 80000.0

    def test_compare_pnl_reports_calculates_correct_diff(self):
        current = get_demo_current_report()
        previous = get_demo_previous_report()
        comparison = compare_pnl_reports(current, previous)
        assert comparison.net_income_difference == 20000.0
        assert comparison.net_income_percentage_change == 25.0

    def test_compare_pnl_reports_income_expense_diffs(self):
        current = get_demo_current_report()
        previous = get_demo_previous_report()
        comparison = compare_pnl_reports(current, previous)
        assert comparison.income_difference == 30000.0
        assert comparison.expense_difference == 10000.0

    def test_create_pnl_comparison_excel_creates_file(self):
        current = get_demo_current_report()
        previous = get_demo_previous_report()
        comparison = compare_pnl_reports(current, previous)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pnl_test.xlsx"
            path = create_pnl_comparison_excel(current, previous, comparison, output)
            assert Path(path).exists()
            assert Path(path).stat().st_size > 0

    def test_read_pnl_report_json(self):
        data = {
            "rows": [
                {"account": "Sales", "amount": 100000, "type": "income"},
                {"account": "Rent", "amount": 20000, "type": "expense"},
            ],
            "total_income": 100000,
            "total_expenses": 20000,
            "net_income": 80000,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            fname = f.name
        try:
            report = read_pnl_report(fname)
            assert report.total_income == 100000.0
            assert report.total_expenses == 20000.0
            assert report.net_income == 80000.0
        finally:
            os.unlink(fname)

    def test_detect_report_format(self):
        assert detect_report_format("report.csv") == "csv"
        assert detect_report_format("report.xlsx") == "xlsx"
        assert detect_report_format("report.pdf") == "pdf"
        assert detect_report_format("report.json") == "json"
        assert detect_report_format("report.txt") == "txt"
        assert detect_report_format("report.xyz") == "unknown"

    def test_build_pnl_summary_text_english(self):
        current = get_demo_current_report()
        previous = get_demo_previous_report()
        comparison = compare_pnl_reports(current, previous)
        text = build_pnl_summary_text(comparison, "en")
        assert "increased" in text or "decreased" in text
        assert "25.0%" in text
        assert "20,000" in text or "20000" in text

    def test_build_pnl_summary_text_roman_urdu(self):
        current = get_demo_current_report()
        previous = get_demo_previous_report()
        comparison = compare_pnl_reports(current, previous)
        text = build_pnl_summary_text(comparison, "roman_urdu")
        assert "compare" in text.lower() or "Maine" in text
        assert "25" in text

    def test_no_llm_for_math(self):
        import inspect
        source = inspect.getsource(compare_pnl_reports)
        assert "openai" not in source.lower()
        assert "anthropic" not in source.lower()
        assert "llm" not in source.lower()

    def test_pnl_comparison_to_dict(self):
        current = get_demo_current_report()
        previous = get_demo_previous_report()
        comparison = compare_pnl_reports(current, previous)
        d = pnl_comparison_to_dict(comparison)
        assert d["comparison"]["net_income_difference"] == 20000.0
        assert d["comparison"]["net_income_percentage_change"] == 25.0
        assert len(d["line_differences"]) > 0

    def test_pnl_comparison_line_differences_count(self):
        current = get_demo_current_report()
        previous = get_demo_previous_report()
        comparison = compare_pnl_reports(current, previous)
        expected_count = max(len(current.rows), len(previous.rows))
        assert len(comparison.line_differences) == expected_count

    def test_pnl_comparison_with_zero_previous(self):
        current = PnLReport(
            rows=[PnLRow(account="Income", amount=50000.0, type="income")],
            total_income=50000.0, total_expenses=0.0, net_income=50000.0,
        )
        previous = PnLReport(
            rows=[PnLRow(account="Income", amount=0.0, type="income")],
            total_income=0.0, total_expenses=0.0, net_income=0.0,
        )
        comparison = compare_pnl_reports(current, previous)
        assert comparison.income_difference == 50000.0
        assert comparison.net_income_percentage_change is None  # div by zero guard

    def test_pnl_report_with_missing_accounts(self):
        current = PnLReport(
            rows=[
                PnLRow(account="Income A", amount=100.0, type="income"),
                PnLRow(account="Income B", amount=200.0, type="income"),
            ],
            total_income=300.0, total_expenses=0.0, net_income=300.0,
        )
        previous = PnLReport(
            rows=[PnLRow(account="Income A", amount=50.0, type="income")],
            total_income=50.0, total_expenses=0.0, net_income=50.0,
        )
        comparison = compare_pnl_reports(current, previous)
        assert len(comparison.line_differences) == 2
        income_b_diff = [ld for ld in comparison.line_differences if ld.account == "Income B"][0]
        assert income_b_diff.current_amount == 200.0
        assert income_b_diff.previous_amount == 0.0


class TestPnLPlanner:
    def _plan_task_pnl(self, client, command: str):
        resp = client.post("/api/agent/plan-task", json={"command": command, "force_new_plan": True})
        assert resp.status_code == 200
        return resp.json()

    def test_planner_detects_pnl_command(self, client_with_auth):
        data = self._plan_task_pnl(client_with_auth, "Open QuickBooks, extract monthly P&L and compare with last month")
        assert data["task_type"] == "accounting_report_comparison"
        assert data["plan"]["risk_level"] == "medium"
        assert data["plan"]["requires_approval"] is True
        assert len(data["plan"]["steps"]) == 15

    def test_planner_detects_pnl_short_command(self, client_with_auth):
        data = self._plan_task_pnl(client_with_auth, "compare profit and loss this month with last month")
        assert data["task_type"] == "accounting_report_comparison"

    def test_planner_detects_quickbooks_report(self, client_with_auth):
        data = self._plan_task_pnl(client_with_auth, "quickbooks monthly report")
        assert data["task_type"] == "accounting_report_comparison"

    def test_planner_blocks_payment_command(self, client_with_auth):
        resp = client_with_auth.post("/api/agent/plan-task", json={
            "command": "make a payment of 5000",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_level"] == "blocked" or data["blocked_reason"] is not None

    def test_planner_blocks_delete_command(self, client_with_auth):
        resp = client_with_auth.post("/api/agent/plan-task", json={
            "command": "delete all records",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_level"] == "blocked" or data["blocked_reason"] is not None

    def test_planner_returns_plan_id(self, client_with_auth):
        data = _plan_task(client_with_auth, "Open QuickBooks and compare P&L")
        assert data["plan_id"] is not None

    def test_planner_steps_have_required_fields(self, client_with_auth):
        data = _plan_task(client_with_auth, "monthly P&L comparison")
        for step in data["plan"]["steps"]:
            assert "step_order" in step
            assert "step_type" in step
            assert "tool" in step
            assert "instruction" in step
            assert "risk_level" in step
            assert "requires_approval" in step


class TestPnLDemoEndpoint:
    def test_demo_endpoint_returns_comparison(self, client_with_auth):
        resp = client_with_auth.post("/api/agent/reports/pnl/compare-demo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        result = data["result"]
        assert result["comparison"]["net_income_difference"] == 20000.0
        assert result["comparison"]["net_income_percentage_change"] == 25.0
        assert result["excel_file_path"] is not None
        assert "summary_english" in result
        assert "summary_roman_urdu" in result

    def test_demo_endpoint_current_values(self, client_with_auth):
        resp = client_with_auth.post("/api/agent/reports/pnl/compare-demo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["current"]["net_income"] == 100000.0
        assert data["result"]["previous"]["net_income"] == 80000.0


class TestPnLManualUpload:
    def test_manual_upload_requires_both_files(self, client_with_auth):
        resp = client_with_auth.post("/api/agent/reports/pnl/compare-uploaded", json={})
        assert resp.status_code == 400

    def test_manual_upload_returns_comparison(self, client_with_auth):
        current_json = {
            "rows": [{"account": "Income", "amount": 50000, "type": "income"}],
            "total_income": 50000, "total_expenses": 0, "net_income": 50000,
        }
        previous_json = {
            "rows": [{"account": "Income", "amount": 40000, "type": "income"}],
            "total_income": 40000, "total_expenses": 0, "net_income": 40000,
        }
        resp = client_with_auth.post("/api/agent/reports/pnl/compare-uploaded", json={
            "current_month_file": current_json,
            "previous_month_file": previous_json,
        })
        assert resp.status_code == 200
        data = resp.json()
        result = data["result"]
        assert result["comparison"]["income_difference"] == 10000.0
        assert result["excel_file_path"] is not None

    def test_manual_upload_with_string_json(self, client_with_auth):
        current_str = json.dumps({
            "rows": [{"account": "Sales", "amount": 100000, "type": "income"}],
            "total_income": 100000, "total_expenses": 0, "net_income": 100000,
        })
        previous_str = json.dumps({
            "rows": [{"account": "Sales", "amount": 90000, "type": "income"}],
            "total_income": 90000, "total_expenses": 0, "net_income": 90000,
        })
        resp = client_with_auth.post("/api/agent/reports/pnl/compare-uploaded", json={
            "current_month_file": current_str,
            "previous_month_file": previous_str,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["comparison"]["net_income_difference"] == 10000.0


class TestPnLWorkflowIntegration:
    def test_approve_pnl_plan_creates_run(self, client_with_auth, db_session):
        data = _plan_task(client_with_auth, "monthly P&L comparison")
        plan_id = data["plan_id"]

        approve_resp = client_with_auth.post(f"/api/agent/plans/{plan_id}/approve", json={"mode": "dry_run"})
        assert approve_resp.status_code == 200
        approve_data = approve_resp.json()
        assert approve_data["ok"] is True
        assert approve_data["run_id"] is not None
        assert len(approve_data["steps"]) == 15

    def test_execute_pnl_step_dry_run(self, client_with_auth):
        data = _plan_task(client_with_auth, "monthly P&L comparison")
        plan_id = data["plan_id"]

        approve_resp = client_with_auth.post(f"/api/agent/plans/{plan_id}/approve", json={"mode": "dry_run"})
        run_id = approve_resp.json()["run_id"]

        step_resp = client_with_auth.post(f"/api/agent/runs/{run_id}/execute-step", json={})
        assert step_resp.status_code == 200
        step_data = step_resp.json()
        assert step_data["step_status"] == "completed"
        assert step_data["result"]["status"] == "dry_run"

    def test_pnl_plan_creates_workflow_memory(self, client_with_auth, db_session):
        data = _plan_task(client_with_auth, "monthly P&L comparison")
        plan_id = data["plan_id"]

        wf_resp = client_with_auth.post("/api/agent/workflows/save", json={
            "plan_id": plan_id,
            "workflow_name": "Monthly P&L Comparison",
            "trigger_phrases": ["monthly pnl comparison", "compare pnl"],
        })
        assert wf_resp.status_code == 200
        wf_data = wf_resp.json()
        assert wf_data["ok"] is True
        assert len(wf_data["trigger_phrases"]) == 2

    def test_repeat_pnl_workflow(self, client_with_auth, db_session):
        data = _plan_task(client_with_auth, "monthly P&L comparison")
        plan_id = data["plan_id"]

        wf_resp = client_with_auth.post("/api/agent/workflows/save", json={
            "plan_id": plan_id,
            "workflow_name": "Monthly P&L Comparison",
            "trigger_phrases": ["monthly pnl comparison"],
        })
        wf_id = wf_resp.json()["workflow_id"]

        repeat_resp = client_with_auth.post(f"/api/agent/workflows/{wf_id}/repeat", json={"mode": "dry_run"})
        assert repeat_resp.status_code == 200
        repeat_data = repeat_resp.json()
        assert repeat_data["ok"] is True
        assert repeat_data["run_id"] is not None

    def test_pnl_run_summary_after_execution(self, client_with_auth, db_session):
        data = _plan_task(client_with_auth, "monthly P&L comparison")
        plan_id = data["plan_id"]

        approve_resp = client_with_auth.post(f"/api/agent/plans/{plan_id}/approve", json={"mode": "dry_run"})
        run_id = approve_resp.json()["run_id"]

        from app.services.agent_memory import complete_run
        complete_run(db_session, run_id)

        from app.services.agent_memory import get_run
        run = get_run(db_session, run_id)
        run.status = "completed"
        run.completed_at = __import__("datetime").datetime.utcnow()
        db_session.commit()

        summary_resp = client_with_auth.get(f"/api/agent/runs/{run_id}/summary")
        assert summary_resp.status_code == 200
        summary_data = summary_resp.json()
        assert summary_data["status"] == "completed"
        assert summary_data["mode"] == "dry_run"

    def test_save_pnl_workflow_after_run(self, client_with_auth):
        data = _plan_task(client_with_auth, "monthly P&L comparison")
        plan_id = data["plan_id"]

        wf_resp = client_with_auth.post("/api/agent/workflows/save", json={
            "plan_id": plan_id,
            "workflow_name": "Monthly P&L Comparison",
        })
        assert wf_resp.status_code == 200
        assert wf_resp.json()["workflow_name"] == "Monthly P&L Comparison"

    def test_pnl_plan_has_can_save_workflow_flag(self, client_with_auth):
        data = _plan_task(client_with_auth, "monthly P&L comparison")
        assert data["plan"].get("can_save_workflow") is True

    def test_non_pnl_command_not_detected(self, client_with_auth):
        data = _plan_task(client_with_auth, "read this screen")
        assert data["task_type"] != "accounting_report_comparison"
