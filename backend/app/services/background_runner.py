from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models.background_task import BackgroundTask
from .agent_tool_executor import execute_tool

logger = logging.getLogger("officepilot.background_runner")

COM_TIMEOUT = int(os.environ.get("OFFICEPILOT_COM_TIMEOUT", "60"))

COM_TOOLS = frozenset({
    "excel_create_pivot_table",
    "excel_switch_workbooks",
    "excel_advanced_formatting",
    "excel_calculate_and_read",
    "excel_create_chart",
})

# Phase 40C — Recovery strategies for known tool failures.
# Key: "<tool_name>:<error_substring>"  (error_substring is matched case-insensitively)
# Value: dict with "recovery_steps" (list) and "clarification_template" (str with {placeholders}).
# If recovery_steps is non-empty, the runner injects those steps and continues.
# If recovery_steps is empty, the runner pauses with the clarification_template.
RECOVERY_MAP: dict[str, dict[str, Any]] = {
    "extract_invoice_data:low_confidence": {
        "recovery_steps": [
            {
                "step_type": "screen_read_text",
                "tool": "screen_read_text",
                "params": {"target": "invoice_file", "prompt": "Extract all text from the visible invoice"},
                "description": "Attempting recovery: reading invoice text via screen OCR",
            },
        ],
        "clarification_template": "I couldn't read the total amount on {file_name}. Can you tell me the amount or provide a clearer file?",
    },
    "extract_invoice_data:not found": {
        "recovery_steps": [
            {
                "step_type": "file_find_latest_download",
                "tool": "file_find_latest_download",
                "params": {},
                "description": "Attempting recovery: searching for the invoice file in Downloads",
            },
        ],
        "clarification_template": "I couldn't find the invoice file {file_name}. Can you provide the correct file path?",
    },
    "excel_create_summary_from_file:unsupported": {
        "recovery_steps": [],
        "clarification_template": "The file {file_name} has an unsupported format. Could you save it as .xlsx or .csv and try again?",
    },
}


def _build_clarification_question(tool_name: str, error_message: str, params: dict) -> str:
    """Build a user-friendly clarification question from RECOVERY_MAP or a generic fallback."""
    file_name = params.get("file_path", params.get("file_name", "the file"))
    if "/" in str(file_name) or "\\" in str(file_name):
        file_name = file_name.split("/")[-1].split("\\")[-1]
    cmd = params.get("command", tool_name)
    for key, entry in RECOVERY_MAP.items():
        key_tool, key_err = key.split(":", 1)
        if key_tool == tool_name and key_err.lower() in error_message.lower():
            return entry.get("clarification_template", "").format(file_name=file_name, command=cmd)
    return f"I ran into an issue with '{tool_name}': {error_message}. Could you help me resolve this?"


def _get_recovery_steps(tool_name: str, error_message: str) -> list[dict] | None:
    """Return recovery steps from RECOVERY_MAP, or None if no match."""
    for key, entry in RECOVERY_MAP.items():
        key_tool, key_err = key.split(":", 1)
        if key_tool == tool_name and key_err.lower() in error_message.lower():
            return entry.get("recovery_steps", [])
    return None


class BackgroundTaskRunner:
    _instance: BackgroundTaskRunner | None = None
    _lock = threading.Lock()

    def __init__(self):
        self._active_tasks: dict[int, threading.Thread] = {}

    @classmethod
    def get_instance(cls) -> BackgroundTaskRunner:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start_task(self, task_id: int) -> None:
        if task_id in self._active_tasks:
            logger.warning("Task %d is already running", task_id)
            return
        thread = threading.Thread(target=self._run_task, args=(task_id,), daemon=True)
        self._active_tasks[task_id] = thread
        thread.start()

    def _run_task(self, task_id: int) -> None:
        db: Session = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if not task:
                logger.error("Task %d not found in DB", task_id)
                return

            plan = json.loads(task.plan_json)
            steps = plan if isinstance(plan, list) else plan.get("steps", [])
            total = len(steps)
            results = []

            for idx, step in enumerate(steps):
                if self._is_cancelled(db, task_id):
                    return

                if step.get("_blocked"):
                    task.status = "failed"
                    task.error_message = step.get("_blocked_reason", "Step blocked by watcher safety policy")
                    task.updated_at = datetime.utcnow()
                    db.commit()
                    return

                if step.get("_needs_approval"):
                    task.status = "pending_approval"
                    task.current_step_description = step.get("_blocked_reason", "Medium/high risk step awaiting approval")
                    task.updated_at = datetime.utcnow()
                    db.commit()
                    return

                tool_name = step.get("tool", step.get("type", ""))
                params = step.get("params", step.get("parameters", {}))
                step_desc = step.get("description", step.get("label", tool_name))

                task.current_step_description = step_desc
                task.progress_percent = int((idx / total) * 100) if total > 0 else 0
                task.status = "running"
                task.updated_at = datetime.utcnow()
                db.commit()

                try:
                    if tool_name in COM_TOOLS:
                        result_container = []
                        com_thread = threading.Thread(
                            target=lambda: result_container.append(
                                execute_tool(tool_name, params, mode="live", db=db, user=None)
                            ),
                            daemon=True,
                        )
                        com_thread.start()
                        com_thread.join(timeout=COM_TIMEOUT)
                        if com_thread.is_alive():
                            raise TimeoutError(
                                f"COM operation '{tool_name}' timed out after {COM_TIMEOUT}s"
                            )
                        result = result_container[0] if result_container else {
                            "status": "error", "error_message": "COM operation returned no result",
                            "message": "No result from COM operation",
                        }
                    else:
                        result = execute_tool(tool_name, params, mode="live", db=db, user=None)
                except TimeoutError as e:
                    result = {"status": "timeout", "error_message": str(e), "message": str(e)}
                except Exception as e:
                    result = {"status": "error", "error_message": str(e), "message": str(e)}

                results.append({
                    "step_index": idx,
                    "tool": tool_name,
                    "status": result.get("status", "failed"),
                    "output": result.get("output", {}),
                })

                if result.get("status") in ("failed", "error"):
                    error_msg = result.get("error_message", result.get("message", "Step failed"))
                    recovery_steps = _get_recovery_steps(tool_name, error_msg)
                    if recovery_steps is not None and len(recovery_steps) > 0:
                        # Inject recovery steps into the plan
                        current_step_description = task.current_step_description
                        for rstep in recovery_steps:
                            task.current_step_description = rstep.get("description", "Attempting recovery...")
                            task.updated_at = datetime.utcnow()
                            db.commit()
                            try:
                                rresult = execute_tool(
                                    rstep["tool"], rstep.get("params", {}),
                                    mode="live", db=db, user=None,
                                )
                            except Exception as e:
                                rresult = {"status": "error", "error_message": str(e)}
                            results.append({
                                "step_index": idx,
                                "tool": rstep["tool"],
                                "status": rresult.get("status", "failed"),
                                "output": rresult.get("output", {}),
                            })
                            if rresult.get("status") in ("failed", "error"):
                                clarification_question = _build_clarification_question(tool_name, error_msg, params)
                                task.status = "paused_for_input"
                                task.clarification_question = clarification_question
                                task.current_step_description = f"Recovery failed: {rresult.get('error_message', 'step errored')}"
                                task.error_message = error_msg
                                task.updated_at = datetime.utcnow()
                                db.commit()
                                return
                        # Recovery succeeded — keep running
                        continue
                    else:
                        clarification_question = _build_clarification_question(tool_name, error_msg, params)
                        if clarification_question:
                            task.status = "paused_for_input"
                            task.clarification_question = clarification_question
                            task.current_step_description = f"Paused: need input to proceed"
                            task.error_message = error_msg
                            task.updated_at = datetime.utcnow()
                            db.commit()
                            return
                        # No recovery and no clarification = fail
                        task.status = "failed"
                        task.error_message = error_msg
                        task.updated_at = datetime.utcnow()
                        db.commit()
                        return

            task.progress_percent = 100
            task.current_step_description = "Completed"
            task.status = "completed"
            task.result_summary_json = json.dumps({
                "total_steps": total,
                "completed_steps": len(results),
                "failed_steps": sum(1 for r in results if r["status"] == "failed"),
                "step_results": results,
            })
            task.updated_at = datetime.utcnow()
            db.commit()

        except Exception as e:
            logger.exception("Background task %d failed", task_id)
            try:
                task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    task.updated_at = datetime.utcnow()
                    db.commit()
            except Exception:
                logger.exception("Failed to update task %d status", task_id)
        finally:
            self._active_tasks.pop(task_id, None)
            db.close()

    def _is_cancelled(self, db: Session, task_id: int) -> bool:
        task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
        return task is not None and task.status == "cancelled"

    def cancel_task(self, task_id: int) -> None:
        db: Session = SessionLocal()
        try:
            task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
            if task and task.status == "running":
                task.status = "cancelled"
                task.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def is_task_running(self, task_id: int) -> bool:
        return task_id in self._active_tasks
