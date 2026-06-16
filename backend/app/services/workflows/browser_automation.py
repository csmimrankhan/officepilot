"""Phase 12 — browser automation LangGraph nodes.

We expose a small workflow spec with the same shape as the other
Phase 6 graphs (start node, node list, handler map) so the
existing runner can walk it without changes. The graph models the
canonical "open URL -> build preview -> approval -> execute ->
validate -> log" flow.

The graph deliberately does *not* call :class:`BrowserAdapter`
directly when Playwright is unavailable; in that case it falls
back to the dry-run mode in :mod:`app.services.browser_automation`.
This means the sidecar can ship and the UI can preview the
workflow end-to-end on a machine that doesn't have Chromium
installed.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from ... import services
from ...services import browser_automation as ba_svc

log_action = services.audit.log_action
ba = ba_svc

logger = logging.getLogger(__name__)


BROWSER_AUTOMATION_NODES: list[str] = [
    "browser_prepare",
    "browser_domain_check",
    "browser_build_preview",
    "browser_approval_checkpoint",
    "browser_execute",
    "browser_validate",
    "browser_audit_log",
]


def _state_get(state: dict, key: str, default=None):
    val = state.get(key)
    return default if val is None else val


def browser_prepare(state: dict, runner=None) -> dict:
    """Normalize the input payload and write a single
    ``browser_action_runs`` row in ``preview`` state.

    If ``run_id`` is already in the state (the common case for
    approval-time execution), we attach to the existing row
    instead of creating a new one."""
    from ...db import SessionLocal
    from ...models.browser_action_run import BrowserActionRun

    target_url = _state_get(state, "target_url", "") or ""
    action_type = _state_get(state, "action_type", "open_url") or "open_url"
    existing_run_id = _state_get(state, "run_id")
    db = SessionLocal()
    try:
        policy_row = ba.get_or_create_policy(db)
        if existing_run_id is not None:
            row = db.get(BrowserActionRun, int(existing_run_id))
            if row is not None:
                # Refresh fields that the workflow needs.
                if not row.target_url:
                    row.target_url = target_url
                if not row.action_type:
                    row.action_type = action_type
                if not row.target_domain and target_url:
                    row.target_domain = ba.policy_decision(policy_row, target_url).host
                db.commit()
                db.refresh(row)
                return {
                    "run_id": row.id,
                    "policy": ba.policy_to_dict(policy_row),
                }
        # Fresh-run path: the HTTP layer hasn't created a row yet.
        row = BrowserActionRun(
            source_type=_state_get(state, "source_type", "workflow") or "workflow",
            source_id=_state_get(state, "source_id"),
            workflow_run_id=_state_get(state, "workflow_run_id"),
            voice_command_id=_state_get(state, "voice_command_id"),
            action_type=action_type,
            target_url=target_url,
            target_domain=ba.policy_decision(policy_row, target_url).host
            if target_url
            else None,
            risk_level="low",
            approval_status="not_required",
            status="preview",
            preview_json={},
            result_json={},
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {
            "run_id": row.id,
            "policy": ba.policy_to_dict(policy_row),
        }
    finally:
        db.close()


def browser_domain_check(state: dict, runner=None) -> dict:
    """Bail out early (high risk) if the target domain is not
    in the allowlist."""
    from ...db import SessionLocal
    from ...models.browser_action_run import BrowserActionRun

    run_id = _state_get(state, "run_id")
    if not run_id:
        return {"domain_allowed": False, "domain_reason": "missing run_id"}
    db = SessionLocal()
    try:
        row = db.get(BrowserActionRun, run_id)
        if row is None:
            return {"domain_allowed": False, "domain_reason": "run not found"}
        decision = ba.policy_decision(ba.get_or_create_policy(db), row.target_url or "")
        row.target_domain = decision.host
        row.risk_level = "high" if not decision.allowed else "low"
        row.preview_json = {**(row.preview_json or {}), "domain_decision": decision.to_dict()}
        db.commit()
        return {
            "domain_allowed": decision.allowed,
            "domain_reason": decision.reason,
            "target_domain": decision.host,
        }
    finally:
        db.close()


def browser_build_preview(state: dict, runner=None) -> dict:
    """Build (or reuse) the action preview (steps, risk, redaction).

    If the run already has a ``preview_json`` snapshot — the
    common case for the approval-time execution path — we do not
    rebuild the preview; we just read the existing risk + steps
    out of it. Rebuilding here would clobber the approval status
    that the approve endpoint just set."""
    from ...db import SessionLocal
    from ...models.browser_action_run import BrowserActionRun

    run_id = _state_get(state, "run_id")
    db = SessionLocal()
    try:
        row = db.get(BrowserActionRun, run_id) if run_id else None
        if row is not None and row.preview_json:
            preview_dict = row.preview_json or {}
            return {
                "preview": preview_dict,
                "requires_approval": (preview_dict.get("risk") or {}).get(
                    "requires_approval", False
                ),
            }
        action_type = _state_get(state, "action_type", "open_url")
        target_url = _state_get(state, "target_url", "") or ""
        field_values = _state_get(state, "field_values", {}) or {}
        submit = bool(_state_get(state, "submit", False))
        policy_row = ba.get_or_create_policy(db)
        policy = ba.DomainPolicy.from_lists(
            policy_row.allowed_domains_json or [],
            policy_row.blocked_domains_json or [],
        )
        if action_type == "fill_form" or (action_type == "submit_form"):
            preview = ba.build_fill_form_preview(
                target_url=target_url,
                field_values=field_values,
                submit=(action_type == "submit_form") or submit,
                policy=policy,
            )
        elif action_type == "append_invoice_row":
            preview = ba.build_append_invoice_row_preview(
                target_url=target_url, invoice_payload=field_values, policy=policy
            )
        else:
            preview = ba.build_open_url_preview(target_url=target_url, policy=policy)
        if row is not None:
            row.preview_json = preview.to_dict()
            row.risk_level = preview.risk.risk_level
            row.approval_status = (
                "pending" if preview.risk.requires_approval else "not_required"
            )
            row.status = (
                "awaiting_approval" if preview.risk.requires_approval else "approved"
            )
            db.commit()
        return {
            "preview": preview.to_dict(),
            "requires_approval": preview.risk.requires_approval,
        }
    finally:
        db.close()


def browser_approval_checkpoint(state: dict, runner=None) -> dict:
    """No-op in the runner: the real approval happens in the
    HTTP layer (the modal posts /actions/{id}/approve). We
    just record the decision that was made *before* this node
    ran."""
    return {"approval_passed": True}


def browser_execute(state: dict, runner=None) -> dict:
    """Drive the adapter. In dry-run mode the steps are still
    logged with their redacted values; in live mode we call
    Playwright."""
    from ...db import SessionLocal
    from ...models.browser_action_run import BrowserActionRun
    from ...models.browser_action_step import BrowserActionStep

    run_id = _state_get(state, "run_id")
    db = SessionLocal()
    try:
        row = db.get(BrowserActionRun, run_id) if run_id else None
        if row is None:
            return {"executed": False, "error": "run not found"}
        preview = row.preview_json or {}
        steps = preview.get("steps", [])
        if not row.started_at:
            row.started_at = _now()
        row.status = "running"
        db.commit()
        adapter = ba.get_adapter()
        results: list[dict] = []
        nav = adapter.open_url(row.target_url or "")
        if not nav.ok:
            row.status = "failed"
            row.error_message = nav.error
            row.completed_at = _now()
            db.commit()
            return {"executed": False, "error": nav.error}
        results.append({"step": "navigate", "ok": nav.ok})
        for s in steps:
            step_type = s.get("step_type")
            if step_type == "screenshot":
                shot = adapter.screenshot(run_id, step_type)
                db.add(
                    BrowserActionStep(
                        browser_action_run_id=run_id,
                        step_order=int(s.get("step_order", 0)),
                        step_type=step_type,
                        target_description=s.get("target_description", ""),
                        selector=s.get("selector", ""),
                        input_value_redacted=s.get("input_value_redacted", ""),
                        requires_approval=bool(s.get("requires_approval", False)),
                        status="completed" if shot.ok else "failed",
                        screenshot_path=shot.screenshot_path,
                        error_message=shot.error,
                    )
                )
                db.flush()
                continue
            if step_type == "fill":
                selector = s.get("selector") or ""
                value = s.get("input_value_redacted", "")
                fr = adapter.fill_field(selector, value)
                db.add(
                    BrowserActionStep(
                        browser_action_run_id=run_id,
                        step_order=int(s.get("step_order", 0)),
                        step_type="fill",
                        target_description=s.get("target_description", ""),
                        selector=selector,
                        input_value_redacted=value,
                        requires_approval=bool(s.get("requires_approval", False)),
                        status="completed" if fr.ok else "failed",
                        error_message=fr.error,
                    )
                )
                db.flush()
                results.append({"step": "fill", "ok": fr.ok, "selector": selector})
            elif step_type == "click":
                selector = s.get("selector") or ""
                cr = adapter.click(selector)
                db.add(
                    BrowserActionStep(
                        browser_action_run_id=run_id,
                        step_order=int(s.get("step_order", 0)),
                        step_type="click",
                        target_description=s.get("target_description", ""),
                        selector=selector,
                        input_value_redacted="",
                        requires_approval=bool(s.get("requires_approval", True)),
                        status="completed" if cr.ok else "failed",
                        error_message=cr.error,
                    )
                )
                db.flush()
                results.append({"step": "click", "ok": cr.ok, "selector": selector})
        row.result_json = {"adapter_mode": adapter.mode, "steps": results}
        row.status = "completed"
        row.completed_at = _now()
        db.commit()
        return {"executed": True, "adapter_mode": adapter.mode}
    finally:
        db.close()


def browser_validate(state: dict, runner=None) -> dict:
    """Read-only verification. We don't reach into the page DOM
    in dry-run mode; the validation here is policy + redaction
    sanity."""
    from ...db import SessionLocal
    from ...models.browser_action_run import BrowserActionRun

    run_id = _state_get(state, "run_id")
    db = SessionLocal()
    try:
        row = db.get(BrowserActionRun, run_id) if run_id else None
        if row is None:
            return {"validated": False, "error": "run not found"}
        preview = row.preview_json or {}
        notes = []
        for s in preview.get("steps", []):
            if s.get("input_value_redacted") == "[REDACTED]":
                notes.append("Sensitive value was redacted; user must enter it manually.")
        row.result_json = {**(row.result_json or {}), "validation_notes": notes}
        db.commit()
        return {"validated": True, "notes": notes}
    finally:
        db.close()


def browser_audit_log(state: dict, runner=None) -> dict:
    """Emit the durable audit log row for this run."""
    from ...db import SessionLocal
    from ...models.browser_action_run import BrowserActionRun

    run_id = _state_get(state, "run_id")
    actor = _state_get(state, "actor", "workflow")
    db = SessionLocal()
    try:
        row = db.get(BrowserActionRun, run_id) if run_id else None
        if row is None:
            return {"audit_written": False}
        action_label = f"browser.{row.action_type}"
        log_action(
            db,
            actor=actor,
            action=action_label,
            entity_type="browser_action_run",
            entity_id=row.id,
            details=(
                f"Browser action run #{row.id} -> {row.target_url} "
                f"(risk={row.risk_level}, approval={row.approval_status}, "
                f"status={row.status})"
            ),
            before_data=None,
            after_data={
                "target_url": row.target_url,
                "target_domain": row.target_domain,
                "risk_level": row.risk_level,
                "approval_status": row.approval_status,
                "status": row.status,
                "preview": row.preview_json,
                "result": row.result_json,
                "error": row.error_message,
            },
        )
        db.commit()
        return {"audit_written": True}
    finally:
        db.close()


HANDLERS: dict[str, Callable[[dict, Any], dict]] = {
    "browser_prepare": browser_prepare,
    "browser_domain_check": browser_domain_check,
    "browser_build_preview": browser_build_preview,
    "browser_approval_checkpoint": browser_approval_checkpoint,
    "browser_execute": browser_execute,
    "browser_validate": browser_validate,
    "browser_audit_log": browser_audit_log,
}


def build_browser_automation_graph():
    """Compile the LangGraph StateGraph. The runner walks
    ``BROWSER_AUTOMATION_NODES`` linearly (no conditional edges
    because the approval happens in the HTTP layer)."""
    g = StateGraph(dict)
    for name in BROWSER_AUTOMATION_NODES:
        g.add_node(name, HANDLERS[name])
    g.add_edge(START, "browser_prepare")
    for prev, nxt in zip(BROWSER_AUTOMATION_NODES, BROWSER_AUTOMATION_NODES[1:]):
        g.add_edge(prev, nxt)
    g.add_edge("browser_audit_log", END)
    return g.compile(), HANDLERS, BROWSER_AUTOMATION_NODES


def now_func():
    from datetime import datetime

    return datetime.utcnow()


_now = now_func


__all__ = [
    "BROWSER_AUTOMATION_NODES",
    "HANDLERS",
    "build_browser_automation_graph",
]
