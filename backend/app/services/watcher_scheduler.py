from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models.background_task import BackgroundTask
from ..models.background_watcher import BackgroundWatcher
from ..services.background_runner import BackgroundTaskRunner
from ..services.tool_registry import TOOL_REGISTRY

logger = logging.getLogger("officepilot.watcher_scheduler")

WATCHER_ALLOWED_TOOLS: frozenset[str] = frozenset({
    "email_search",
    "email_preview_messages",
    "email_save_attachment",
    "drive_list_recent_files",
    "drive_download_file",
    "file_open_folder",
    "scan_local_folder",
    "extract_invoice_data",
})

HIGH_RISK_TOOLS: frozenset[str] = frozenset({
    "excel_create_summary_from_file",
    "excel_create_workbook",
    "create_daily_invoices_excel",
    "browser_open_url",
    "browser_click",
    "browser_type",
    "desktop_click",
    "desktop_type",
    "email_download_attachments",
})

SOURCE_TYPE_TO_PLAN: dict[str, list[dict[str, Any]]] = {
    "gmail": [
        {"tool": "email_search", "params": {"query": "has:attachment invoice OR receipt OR bill", "max_results": 10}},
        {"tool": "email_download_attachments", "params": {"download_all": True}},
        {"tool": "extract_invoice_data", "params": {}},
    ],
    "drive": [
        {"tool": "drive_list_recent_files", "params": {"days_back": 1, "keywords": ["invoice", "receipt", "bill"]}},
        {"tool": "drive_download_file", "params": {}},
        {"tool": "extract_invoice_data", "params": {}},
    ],
    "folder": [
        {"tool": "scan_local_folder", "params": {"date_filter": "today"}},
        {"tool": "extract_invoice_data", "params": {}},
    ],
}


def _validate_watcher_plan(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validated = []
    for step in steps:
        tool_name = step.get("tool", "")
        risk = get_tool_risk_level(tool_name)
        if risk in ("medium", "high"):
            validated.append({
                **step,
                "_blocked_reason": f"Tool '{tool_name}' has risk level '{risk}' and is not allowed in watcher plans. Pending approval.",
                "_needs_approval": True,
            })
        elif tool_name not in WATCHER_ALLOWED_TOOLS:
            validated.append({
                **step,
                "_blocked_reason": f"Tool '{tool_name}' is not in the watcher allowed list",
                "_blocked": True,
            })
        else:
            validated.append(step)
    return validated


def get_tool_risk_level(tool_name: str) -> str:
    for entry in TOOL_REGISTRY:
        if entry.name == tool_name:
            return entry.risk_level
    return "low"


class WatcherScheduler:
    _instance: WatcherScheduler | None = None
    _lock = threading.Lock()
    _POLL_INTERVAL = 60

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @classmethod
    def get_instance(cls) -> WatcherScheduler:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("WatcherScheduler started (poll interval=%ds)", self._POLL_INTERVAL)

    def stop(self) -> None:
        self._stop_event.set()
        logger.info("WatcherScheduler stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._check_due_watchers()
            except Exception:
                logger.exception("Error in watcher scheduler loop")
            self._stop_event.wait(self._POLL_INTERVAL)

    def _check_due_watchers(self) -> None:
        db: Session = SessionLocal()
        try:
            now = datetime.utcnow()
            watchers = db.query(BackgroundWatcher).filter(
                BackgroundWatcher.status == "active",
            ).all()

            for watcher in watchers:
                try:
                    if self._is_due(watcher, now):
                        self._execute_watcher(watcher, db)
                except Exception:
                    logger.exception("Error executing watcher %d", watcher.id)
                    watcher.status = "error"
                    db.commit()
        finally:
            db.close()

    def _is_due(self, watcher: BackgroundWatcher, now: datetime) -> bool:
        if watcher.last_run_at is None:
            return True
        cutoff = now - timedelta(minutes=watcher.schedule_minutes)
        return watcher.last_run_at < cutoff

    def _execute_watcher(self, watcher: BackgroundWatcher, db: Session) -> None:
        plan_steps = SOURCE_TYPE_TO_PLAN.get(watcher.source_type, [])
        config = {}
        try:
            config = json.loads(watcher.config_json) if watcher.config_json else {}
        except (json.JSONDecodeError, TypeError):
            pass

        merged_steps = []
        for step in plan_steps:
            merged_params = {**step.get("params", {})}
            if watcher.source_type == "gmail" and "query" in merged_params:
                keywords = config.get("keywords", ["invoice"])
                merged_params["query"] = f"has:attachment {' OR '.join(keywords)}"
                days_back = config.get("days_back", 1)
                merged_params["query"] += f" newer_than:{days_back}d"
            if watcher.source_type == "drive" and "days_back" in merged_params:
                merged_params["days_back"] = config.get("days_back", 1)
                merged_params["keywords"] = config.get("keywords", ["invoice", "receipt", "bill"])
            if watcher.source_type == "folder":
                merged_params["date_filter"] = "today"
            merged_steps.append({"tool": step["tool"], "params": merged_params})

        validated_steps = _validate_watcher_plan(merged_steps)
        has_blocked = any(s.get("_blocked") for s in validated_steps)
        has_pending_approval = any(s.get("_needs_approval") for s in validated_steps)

        if has_blocked:
            watcher.status = "error"
            blocked_tools = [s["tool"] for s in validated_steps if s.get("_blocked")]
            watcher.config_json = json.dumps({
                **config,
                "_last_error": f"Blocked tools: {', '.join(blocked_tools)}",
            })
            watcher.updated_at = datetime.utcnow()
            db.commit()
            return

        task = BackgroundTask(
            user_id=watcher.user_id,
            command=f"Watcher: {watcher.name}",
            plan_json=json.dumps(validated_steps),
            status="queued",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        if has_pending_approval:
            task.status = "pending_approval"
            task.current_step_description = "Watcher plan contains medium/high risk steps awaiting approval"
            db.commit()

        runner = BackgroundTaskRunner.get_instance()
        if not has_pending_approval:
            runner.start_task(task.id)

        watcher.last_run_at = datetime.utcnow()
        watcher.updated_at = datetime.utcnow()
        db.commit()

        if has_pending_approval:
            logger.info("Watcher %d created task %d (pending_approval)", watcher.id, task.id)
        else:
            logger.info("Watcher %d triggered task %d", watcher.id, task.id)

    def run_watcher_now(self, watcher_id: int) -> None:
        db: Session = SessionLocal()
        try:
            watcher = db.query(BackgroundWatcher).filter(BackgroundWatcher.id == watcher_id).first()
            if not watcher:
                return
            self._execute_watcher(watcher, db)
        finally:
            db.close()
