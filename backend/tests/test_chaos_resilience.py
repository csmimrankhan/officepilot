"""Phase 46D — Edge-Case QA & Chaos Testing.

Each test intentionally breaks something and verifies graceful recovery.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

os.environ["OFFICEPILOT_APP_VERSION"] = "1.0.0"
os.environ["AGENT_PROVIDER"] = "mock"
os.environ["QUICKBOOKS_WRITEBACK_ENABLED"] = "true"

from app.db import SessionLocal, init_db
from app.models.background_task import BackgroundTask
from app.services.background_runner import BackgroundTaskRunner
from app.services.agent_tool_executor import (
    EXECUTOR_RESULT_FAILED,
    EXECUTOR_RESULT_OK,
    execute_tool,
)
from app.services.semantic_memory import reset_semantic_memory


# ── Test 1: Garbage Bank Feed ──────────────────────────────────────────────────


def test_garbage_bank_feed_returns_empty_list():
    from app.services.bank_reconciliation import BankFeedAdapter

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as f:
        f.write(b"\x00\x01\x02\xff\xfe\xfd\x00\x1f\x8b\x00" * 1000)
        path = f.name
    try:
        adapter = BankFeedAdapter()
        result = adapter.parse_feed(path)
        assert result == [], f"Expected empty list, got {result}"
    finally:
        try:
            os.unlink(path)
        except PermissionError:
            pass


# ── Test 2: Ollama Malformed JSON ──────────────────────────────────────────────


def test_ollama_malformed_html_falls_back_to_mock():
    from app.services.accountant_agent import call_agent_provider

    from urllib.error import HTTPError
    import io

    fp = io.BytesIO(b"<html>502 Bad Gateway</html>")
    http_error = HTTPError(
        "http://localhost:11434/api/generate", 502, "Bad Gateway", {}, fp
    )

    with patch.dict(os.environ, {"AGENT_PROVIDER": "ollama"}):
        with patch("urllib.request.urlopen", side_effect=http_error):
            result = call_agent_provider("show me invoices", {}, db=None, user_id=None)

    assert isinstance(result, str)
    parsed = json.loads(result)
    assert "steps" in parsed
    assert parsed.get("clarification_needed") is True


# ── Test 3: COM Automation Timeout → App.quit() called ─────────────────────────


def test_com_timeout_quits_app():
    mock_adapter = MagicMock()
    mock_adapter.available = True
    mock_adapter._app = MagicMock()
    mock_adapter.create_pivot_table.side_effect = TimeoutError(
        "Excel COM operation timed out after 60s"
    )
    mock_adapter.__enter__.return_value = mock_adapter

    with patch(
        "app.services.agent_tool_executor._get_excel_com_adapter",
        return_value=mock_adapter,
    ):
        result = execute_tool(
            "excel_create_pivot_table",
            {
                "file_path": os.path.join(
                    os.environ.get("OFFICEPILOT_DATA_DIR", tempfile.gettempdir()),
                    "test.xlsx",
                ),
                "data_range": "A1:Z100",
                "pivot_location": "A1",
                "row_fields": ["Category"],
                "value_field": "Amount",
            },
            mode="live",
            db=None,
            user=None,
        )

    assert result["status"] == EXECUTOR_RESULT_FAILED
    assert result["output"].get("timeout") is True
    # Ensure the context manager exited normally (no zombie EXCEL.EXE)
    assert mock_adapter.__exit__.called


# ── Test 4: Empty Vector DB Search ─────────────────────────────────────────────


def test_empty_vector_db_search_returns_empty_list():
    reset_semantic_memory()

    from app.services.semantic_memory import get_semantic_memory

    sm = get_semantic_memory()
    try:
        results = sm.semantic_search("invoice", top_k=5, user_id=1)
    except Exception as e:
        assert False, f"semantic_search raised: {e}"

    assert isinstance(results, list)
    assert len(results) == 0


# ── Test 5: QuickBooks Network Failure ─────────────────────────────────────────


def test_quickbooks_network_failure_returns_failed():
    from app.services.accounting_writeback import QuickBooksWritebackAdapter

    with patch.object(
        QuickBooksWritebackAdapter,
        "create_bill",
        side_effect=ConnectionError("Failed to connect to QuickBooks API"),
    ):
        db = SessionLocal()
        try:
            result = execute_tool(
                "quickbooks_create_bill",
                {
                    "vendor_name": "Acme Corp",
                    "line_items": [{"description": "Consulting", "amount": 5000.0}],
                    "total_amount": 5000.0,
                    "due_date": "2026-07-28",
                },
                mode="live",
                db=db,
                user=None,
            )
        finally:
            db.close()

    assert result["status"] == EXECUTOR_RESULT_FAILED
    error_msg = result.get("error_message", result.get("message", ""))
    assert "QuickBooks" in error_msg or "connect" in error_msg

    db2 = SessionLocal()
    try:
        from app.models.audit_log import AuditLog

        entries = (
            db2.query(AuditLog)
            .filter(AuditLog.action.like("accounting.writeback.%"))
            .all()
        )
        # No audit entry should exist since exception happened before log
        for entry in entries:
            assert entry.action != "accounting.writeback.quickbooks.create_bill"
    finally:
        db2.close()


# ── Test 6: Background Task Cancellation Race Condition ────────────────────────


def test_background_task_cancellation_before_step_two():
    """Verify cancel_task sets status to cancelled and _is_cancelled works."""
    init_db()

    task_id = None
    db = SessionLocal()
    try:
        steps = [
            {
                "tool": "validate_result",
                "params": {},
                "step_type": "validate_result",
            }
            for _ in range(10)
        ]
        plan = {"steps": steps}
        task = BackgroundTask(
            user_id=1,
            command="long running task",
            plan_json=json.dumps(plan),
            status="running",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
    finally:
        db.close()

    runner = BackgroundTaskRunner.get_instance()

    db2 = SessionLocal()
    try:
        assert runner._is_cancelled(db2, task_id) is False
    finally:
        db2.close()

    runner.cancel_task(task_id)

    db3 = SessionLocal()
    try:
        task = (
            db3.query(BackgroundTask)
            .filter(BackgroundTask.id == task_id)
            .first()
        )
        assert task is not None
        assert task.status == "cancelled"
        assert runner._is_cancelled(db3, task_id) is True
    finally:
        db3.close()
