"""Phase 40C — Autonomous Error Recovery & Self-Correction tests."""
from __future__ import annotations

import json
import time

import pytest
from app.db import SessionLocal
from app.models.background_task import BackgroundTask
from app.services.background_runner import _build_clarification_question, _get_recovery_steps


# ── RECOVERY_MAP helper tests (pure functions, no DB needed) ──


class TestRecoveryMap:
    def test_get_recovery_steps_matches_tool_and_error(self):
        steps = _get_recovery_steps("extract_invoice_data", "low_confidence on invoice")
        assert steps is not None
        assert len(steps) == 1
        assert steps[0]["tool"] == "screen_read_text"

    def test_get_recovery_steps_no_match_returns_none(self):
        steps = _get_recovery_steps("browser_open_url", "some random error")
        assert steps is None

    def test_get_recovery_steps_with_not_found(self):
        steps = _get_recovery_steps("extract_invoice_data", "file not found")
        assert steps is not None
        assert len(steps) == 1
        assert steps[0]["tool"] == "file_find_latest_download"

    def test_get_recovery_steps_unsupported_returns_empty_list(self):
        steps = _get_recovery_steps("excel_create_summary_from_file", "unsupported format")
        assert steps is not None
        assert len(steps) == 0

    def test_build_clarification_question_matched(self):
        question = _build_clarification_question("extract_invoice_data", "low_confidence on Invoice_Acme.pdf", {"file_path": "/tmp/Invoice_Acme.pdf"})
        assert "Invoice_Acme.pdf" in question
        assert "I couldn't read" in question

    def test_build_clarification_question_fallback(self):
        question = _build_clarification_question("unknown_tool", "something broke", {"command": "do stuff"})
        assert "unknown_tool" in question
        assert "something broke" in question

    def test_build_clarification_question_extracts_filename_from_path(self):
        question = _build_clarification_question("excel_create_summary_from_file", "unsupported format", {"file_path": "C:\\Users\\test\\file.xls"})
        assert "file.xls" in question


# ── Recovery step injection via BackgroundTaskRunner ──


@pytest.fixture(autouse=True)
def _patch_execute_tool():
    """Patch execute_tool for recovery tests. Each test sets mock results before triggering."""
    import app.services.background_runner as bg_runner
    original = bg_runner.execute_tool
    call_count = [0]
    mock_results = [{"status": "success", "output": {}}]

    def mock_execute(tool_name, params, mode, db, user):
        idx = call_count[0]
        call_count[0] += 1
        results = mock_execute._mock_results
        if idx < len(results):
            return results[idx]
        return {"status": "success", "output": {}}

    mock_execute._mock_call_count = call_count
    mock_execute._mock_results = mock_results
    bg_runner.execute_tool = mock_execute
    yield
    bg_runner.execute_tool = original


class TestRecoveryStepInjection:
    def test_recovery_step_injected_on_matching_failure(self, client):
        """Test that a failing tool with a RECOVERY_MAP match injects a recovery step."""
        import app.services.background_runner as bg_runner
        bg_runner.execute_tool._mock_results = [
            {"status": "failed", "error_message": "low_confidence on invoice ABC", "message": "Could not read invoice"},
            {"status": "success", "output": {"text": "Invoice total: $500"}},
        ]
        bg_runner.execute_tool._mock_call_count[0] = 0

        resp = client.post("/api/auth/register", json={
            "email": "rec_test@example.com", "password": "Password123!",
            "full_name": "Rec Test", "confirm_password": "Password123!",
        })
        token = (resp.json().get("access_token") or resp.json().get("token", ""))
        if not token:
            resp = client.post("/api/auth/login", json={"email": "rec_test@example.com", "password": "Password123!"})
            token = resp.json().get("access_token") or resp.json().get("token", "")

        headers = {"Authorization": f"Bearer {token}"}
        plan = {"steps": [{"tool": "extract_invoice_data", "params": {"file_path": "/tmp/invoice.pdf"}, "description": "Extract invoice data"}]}
        resp = client.post("/api/agent/run-background", json={"command": "test recovery", "plan_json": plan}, headers=headers)
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]
        time.sleep(1)

        resp = client.get(f"/api/agent/background-tasks/{task_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed", f"Expected completed, got {data['status']}: {data}"
        result_summary = data.get("result_summary", {})
        step_results = result_summary.get("step_results", [])
        recovery_steps = [s for s in step_results if s["tool"] == "screen_read_text"]
        assert len(recovery_steps) == 1
        assert recovery_steps[0]["status"] == "success"

    def test_unrecoverable_error_pauses_for_input(self, client):
        """Test that an unrecoverable error sets paused_for_input and clarification_question."""
        import app.services.background_runner as bg_runner
        bg_runner.execute_tool._mock_results = [
            {"status": "failed", "error_message": "unsupported format: .xyz files not supported", "message": "Format error"},
        ]
        bg_runner.execute_tool._mock_call_count[0] = 0

        resp = client.post("/api/auth/register", json={
            "email": "rec_test2@example.com", "password": "Password123!",
            "full_name": "Rec Test2", "confirm_password": "Password123!",
        })
        token = (resp.json().get("access_token") or resp.json().get("token", ""))
        if not token:
            resp = client.post("/api/auth/login", json={"email": "rec_test2@example.com", "password": "Password123!"})
            token = resp.json().get("access_token") or resp.json().get("token", "")

        headers = {"Authorization": f"Bearer {token}"}
        plan = {"steps": [{"tool": "excel_create_summary_from_file", "params": {"file_path": "/tmp/bad_file.xyz"}, "description": "Create summary"}]}
        resp = client.post("/api/agent/run-background", json={"command": "test unrecoverable", "plan_json": plan}, headers=headers)
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]
        time.sleep(1)

        resp = client.get(f"/api/agent/background-tasks/{task_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paused_for_input", f"Expected paused_for_input, got {data['status']}: {data}"
        assert data["clarification_question"] is not None
        assert "bad_file" in data["clarification_question"] or ".xyz" in data["clarification_question"]

    def test_generic_error_fallback_pauses_with_question(self, client):
        """Test that a tool error with no RECOVERY_MAP match pauses with a generic question."""
        import app.services.background_runner as bg_runner
        bg_runner.execute_tool._mock_results = [
            {"status": "error", "error_message": "Browser crashed with SIGSEGV", "message": "Browser error"},
        ]
        bg_runner.execute_tool._mock_call_count[0] = 0

        resp = client.post("/api/auth/register", json={
            "email": "rec_test3@example.com", "password": "Password123!",
            "full_name": "Rec Test3", "confirm_password": "Password123!",
        })
        token = (resp.json().get("access_token") or resp.json().get("token", ""))
        if not token:
            resp = client.post("/api/auth/login", json={"email": "rec_test3@example.com", "password": "Password123!"})
            token = resp.json().get("access_token") or resp.json().get("token", "")

        headers = {"Authorization": f"Bearer {token}"}
        plan = {"steps": [{"tool": "browser_open_url", "params": {"url": "https://example.com"}, "description": "Open browser"}]}
        resp = client.post("/api/agent/run-background", json={"command": "test generic", "plan_json": plan}, headers=headers)
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]
        time.sleep(1)

        resp = client.get(f"/api/agent/background-tasks/{task_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paused_for_input", f"Expected paused_for_input, got {data['status']}: {data}"
        assert data["clarification_question"] is not None
        assert "browser_open_url" in data["clarification_question"]

    def test_recovery_step_fails_then_pauses(self, client):
        """Test that when a recovery step itself fails, the task pauses with clarification."""
        import app.services.background_runner as bg_runner
        bg_runner.execute_tool._mock_results = [
            {"status": "failed", "error_message": "low_confidence on invoice.pdf", "message": "Low confidence"},
            {"status": "failed", "error_message": "OCR service unavailable", "message": "Service down"},
        ]
        bg_runner.execute_tool._mock_call_count[0] = 0

        resp = client.post("/api/auth/register", json={
            "email": "rec_test4@example.com", "password": "Password123!",
            "full_name": "Rec Test4", "confirm_password": "Password123!",
        })
        token = (resp.json().get("access_token") or resp.json().get("token", ""))
        if not token:
            resp = client.post("/api/auth/login", json={"email": "rec_test4@example.com", "password": "Password123!"})
            token = resp.json().get("access_token") or resp.json().get("token", "")

        headers = {"Authorization": f"Bearer {token}"}
        plan = {"steps": [{"tool": "extract_invoice_data", "params": {"file_path": "/tmp/invoice.pdf"}, "description": "Extract invoice"}]}
        resp = client.post("/api/agent/run-background", json={"command": "test recovery failure", "plan_json": plan}, headers=headers)
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]
        time.sleep(1)

        resp = client.get(f"/api/agent/background-tasks/{task_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paused_for_input", f"Expected paused_for_input, got {data['status']}: {data}"
        assert data["clarification_question"] is not None


# ── /answer endpoint tests ──


class TestAnswerEndpoint:
    def _setup(self, client, status="paused_for_input"):
        resp = client.post("/api/auth/register", json={
            "email": "answer_test@example.com", "password": "Password123!",
            "full_name": "Answer Test", "confirm_password": "Password123!",
        })
        token = (resp.json().get("access_token") or resp.json().get("token", ""))
        if not token:
            resp = client.post("/api/auth/login", json={"email": "answer_test@example.com", "password": "Password123!"})
            token = resp.json().get("access_token") or resp.json().get("token", "")
        headers = {"Authorization": f"Bearer {token}"}

        db = SessionLocal()
        try:
            task = BackgroundTask(
                user_id=1,
                command="test answer",
                plan_json=json.dumps({"steps": [{"tool": "validate_result", "params": {}, "description": "Validate"}]}),
                status=status,
                clarification_question="What is the total amount?",
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            task_id = task.id
        finally:
            db.close()

        return task_id, headers

    def test_answer_resumes_paused_task(self, client):
        task_id, headers = self._setup(client)

        import app.services.background_runner as bg_runner
        runner = bg_runner.BackgroundTaskRunner.get_instance()
        original_start = runner.start_task
        runner.start_task = lambda task_id: None

        try:
            resp = client.post(
                f"/api/agent/background-tasks/{task_id}/answer",
                json={"user_answer": "The total is $500"},
                headers=headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "running"
            assert data["task_id"] == task_id

            db = SessionLocal()
            try:
                task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
                assert task.status == "running"
                assert task.clarification_question is None

                updated_plan = json.loads(task.plan_json)
                steps = updated_plan.get("steps", [])
                assert len(steps) == 2
                assert steps[1]["tool"] == "user_input"
                assert steps[1]["params"]["user_answer"] == "The total is $500"
            finally:
                db.close()
        finally:
            runner.start_task = original_start

    def test_answer_not_paused_returns_400(self, client):
        task_id, headers = self._setup(client, status="completed")

        resp = client.post(
            f"/api/agent/background-tasks/{task_id}/answer",
            json={"user_answer": "hello"},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_answer_other_user_returns_403(self, client):
        _, headers = self._setup(client)

        db = SessionLocal()
        try:
            task = BackgroundTask(
                user_id=999,
                command="test other user",
                plan_json=json.dumps({"steps": []}),
                status="paused_for_input",
                clarification_question="What?",
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            other_task_id = task.id
        finally:
            db.close()

        resp = client.post(
            f"/api/agent/background-tasks/{other_task_id}/answer",
            json={"user_answer": "hello"},
            headers=headers,
        )
        assert resp.status_code == 403

    def test_answer_not_found_returns_404(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "notfound_test@example.com", "password": "Password123!",
            "full_name": "NF Test", "confirm_password": "Password123!",
        })
        token = (resp.json().get("access_token") or resp.json().get("token", ""))
        if not token:
            resp = client.post("/api/auth/login", json={"email": "notfound_test@example.com", "password": "Password123!"})
            token = resp.json().get("access_token") or resp.json().get("token", "")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            "/api/agent/background-tasks/99999/answer",
            json={"user_answer": "hello"},
            headers=headers,
        )
        assert resp.status_code == 404
