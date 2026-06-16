"""Phase 12 — browser automation HTTP API.

Endpoints (all under ``/api/browser``):

* ``GET    /policies``              — read the singleton policy row
* ``PATCH  /policies``              — toggle / edit allowlist / etc.
* ``GET    /status``                — runtime status (adapter mode, last URL)
* ``POST   /stop``                  — stop the adapter
* ``POST   /preview-open-url``      — build a preview for a navigation
* ``POST   /preview-fill-form``     — build a preview for a form fill
* ``POST   /preview-append-invoice-row`` — preview for invoice -> row
* ``POST   /open-url``              — execute (after approval if needed)
* ``POST   /fill-form``             — execute a form fill
* ``POST   /append-invoice-row``    — execute an invoice append
* ``POST   /click-approved-button`` — execute a click of an approved selector
* ``POST   /actions/{id}/approve``  — mark a run as approved
* ``POST   /actions/{id}/reject``   — mark a run as rejected
* ``POST   /actions/{id}/cancel``   — cancel a run
* ``GET    /actions``               — list recent runs
* ``GET    /actions/{id}``          — full run details
* ``GET    /actions/{id}/steps``    — per-step log
* ``GET    /actions/{id}/snapshot``  — captured page snapshot
* ``POST   /voice``                 — voice intent preview/dispatch
* ``GET    /test-form``             — render the local test form HTML
* ``POST   /test-form/fill-preview`` — preview filling the test form
* ``GET    /voices``                — list known voice intents (read-only)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.browser_action_run import BrowserActionRun
from ..models.browser_action_step import BrowserActionStep
from ..models.browser_automation_policy import BrowserAutomationPolicy
from ..models.browser_page_snapshot import BrowserPageSnapshot
from ..models.invoice import Invoice
from ..schemas.browser import (
    BrowserActionPreview,
    BrowserActionRequest,
    BrowserActionResponse,
    BrowserActionRunRead,
    BrowserActionRunSummary,
    BrowserActionStepRead,
    BrowserApprovalRequest,
    BrowserCancelRequest,
    BrowserPageSnapshotRead,
    BrowserPolicyRead,
    BrowserPolicyUpdate,
    BrowserPreviewRequest,
    BrowserPreviewResponse,
    BrowserRejectRequest,
    BrowserStatusRead,
    BrowserTestFormFillRequest,
    BrowserVoiceIntentRequest,
    BrowserVoiceIntentResponse,
)
from ..services import browser_automation as ba
from ..services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/browser", tags=["browser"])


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


@router.get("/policies", response_model=BrowserPolicyRead)
def get_policies(db: Session = Depends(get_db)):
    row = ba.get_or_create_policy(db)
    db.commit()
    return ba.policy_to_dict(row)


@router.patch("/policies", response_model=BrowserPolicyRead)
def update_policies(
    payload: BrowserPolicyUpdate,
    actor: str = Query("user"),
    db: Session = Depends(get_db),
):
    row = ba.get_or_create_policy(db)
    patch = payload.model_dump(exclude_unset=True)
    before = ba.policy_to_dict(row)
    if "allowed_domains" in patch and patch["allowed_domains"] is not None:
        row.allowed_domains_json = [
            d.strip().lower() for d in patch["allowed_domains"] if d and d.strip()
        ]
    if "blocked_domains" in patch and patch["blocked_domains"] is not None:
        row.blocked_domains_json = [
            d.strip().lower() for d in patch["blocked_domains"] if d and d.strip()
        ]
    for key in (
        "require_approval_for_submit",
        "require_approval_for_write",
        "screenshots_enabled",
        "enabled",
        "headless",
        "notes",
    ):
        if key in patch and patch[key] is not None:
            setattr(row, key, patch[key])
    row.updated_at = datetime.utcnow()
    after = ba.policy_to_dict(row)
    log_action(
        db,
        actor=actor,
        action="browser.policy.update",
        entity_type="browser_policy",
        entity_id=row.id,
        details="Updated browser automation policy",
        before_data=before,
        after_data=after,
    )
    db.commit()
    return after


# ---------------------------------------------------------------------------
# Status / stop
# ---------------------------------------------------------------------------


@router.get("/status", response_model=BrowserStatusRead)
def get_status(db: Session = Depends(get_db)):
    row = ba.get_or_create_policy(db)
    adapter = ba.get_adapter()
    s = adapter.status()
    return BrowserStatusRead(
        enabled=bool(row.enabled),
        headless=bool(row.headless),
        screenshots_enabled=bool(row.screenshots_enabled),
        adapter_mode=s.get("mode", "dry-run"),
        live=bool(s.get("live", False)),
        allowed_domains=list(row.allowed_domains_json or []),
        blocked_domains=list(row.blocked_domains_json or []),
        last_url=s.get("last_url", ""),
        last_title=s.get("last_title", ""),
    )


@router.post("/stop")
def stop_browser(db: Session = Depends(get_db)):
    ba.reset_adapter()
    row = ba.get_or_create_policy(db)
    log_action(
        db,
        actor="user",
        action="browser.stop",
        entity_type="browser_policy",
        entity_id=row.id,
        details="Operator stopped the browser adapter.",
    )
    db.commit()
    return {"stopped": True, "adapter_mode": ba.get_adapter().mode}


# ---------------------------------------------------------------------------
# Preview helpers
# ---------------------------------------------------------------------------


def _build_preview(
    db: Session,
    *,
    action_type: str,
    target_url: str,
    field_values: dict,
    submit: bool,
    invoice_id: Optional[int],
    source_type: str,
    source_id: Optional[int],
    workflow_run_id: Optional[int],
    voice_command_id: Optional[int],
    actor: str,
) -> BrowserPreviewResponse:
    settings = get_settings()
    policy_row = ba.get_or_create_policy(db)
    if not policy_row.enabled:
        raise HTTPException(
            status_code=403,
            detail="browser automation is disabled in policy (see Settings)",
        )
    policy = ba.DomainPolicy.from_lists(
        policy_row.allowed_domains_json or [],
        policy_row.blocked_domains_json or [],
    )
    # Resolve invoice payload if invoice_id provided.
    if invoice_id is not None and not field_values:
        inv = db.get(Invoice, invoice_id)
        if inv is None:
            raise HTTPException(
                status_code=404, detail=f"invoice {invoice_id} not found"
            )
        field_values = ba.invoice_to_test_form_payload(inv)
    if action_type in ("fill_form", "submit_form"):
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
    # Persist a BrowserActionRun in preview state.
    run = BrowserActionRun(
        source_type=source_type,
        source_id=source_id,
        workflow_run_id=workflow_run_id,
        voice_command_id=voice_command_id,
        action_type=preview.action_type,
        target_url=preview.target_url,
        target_domain=preview.target_domain,
        risk_level=preview.risk.risk_level,
        approval_status="pending" if preview.risk.requires_approval else "not_required",
        status="awaiting_approval" if preview.risk.requires_approval else "approved",
        preview_json=preview.to_dict(),
        result_json={},
    )
    db.add(run)
    log_action(
        db,
        actor=actor,
        action=f"browser.{preview.action_type}.preview",
        entity_type="browser_action_run",
        entity_id=None,
        details=(
            f"Preview built for {preview.target_url} "
            f"(risk={preview.risk.risk_level}, "
            f"requires_approval={preview.risk.requires_approval})"
        ),
        after_data={"preview": preview.to_dict()},
    )
    db.commit()
    db.refresh(run)
    return BrowserPreviewResponse(
        run_id=run.id,
        preview=BrowserActionPreview(**preview.to_dict()),
        requires_approval=preview.risk.requires_approval,
        domain_allowed=(preview.domain_decision.allowed if preview.domain_decision else False),
        message="preview created; approve before executing" if preview.risk.requires_approval else "preview created; safe to run",
    )


@router.post("/preview-open-url", response_model=BrowserPreviewResponse)
def preview_open_url(payload: BrowserPreviewRequest, db: Session = Depends(get_db)):
    return _build_preview(
        db,
        action_type="open_url",
        target_url=payload.target_url,
        field_values=payload.field_values or {},
        submit=False,
        invoice_id=payload.invoice_id,
        source_type=payload.source_type,
        source_id=payload.source_id,
        workflow_run_id=payload.workflow_run_id,
        voice_command_id=payload.voice_command_id,
        actor=payload.actor,
    )


@router.post("/preview-fill-form", response_model=BrowserPreviewResponse)
def preview_fill_form(payload: BrowserPreviewRequest, db: Session = Depends(get_db)):
    return _build_preview(
        db,
        action_type="fill_form",
        target_url=payload.target_url,
        field_values=payload.field_values or {},
        submit=payload.submit,
        invoice_id=payload.invoice_id,
        source_type=payload.source_type,
        source_id=payload.source_id,
        workflow_run_id=payload.workflow_run_id,
        voice_command_id=payload.voice_command_id,
        actor=payload.actor,
    )


@router.post(
    "/preview-append-invoice-row", response_model=BrowserPreviewResponse
)
def preview_append_invoice_row(
    payload: BrowserPreviewRequest, db: Session = Depends(get_db)
):
    return _build_preview(
        db,
        action_type="append_invoice_row",
        target_url=payload.target_url,
        field_values=payload.field_values or {},
        submit=True,
        invoice_id=payload.invoice_id,
        source_type=payload.source_type,
        source_id=payload.source_id,
        workflow_run_id=payload.workflow_run_id,
        voice_command_id=payload.voice_command_id,
        actor=payload.actor,
    )


# ---------------------------------------------------------------------------
# Execute (after approval)
# ---------------------------------------------------------------------------


def _run_browser_workflow(db: Session, run_id: int, actor: str) -> BrowserActionResponse:
    """Drive the LangGraph browser workflow for an existing run."""
    from ..services.workflows.registry import get_graph

    run = db.get(BrowserActionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="browser action run not found")
    if run.approval_status == "rejected":
        raise HTTPException(
            status_code=409, detail="browser action was rejected; create a new preview"
        )
    if run.approval_status == "pending":
        raise HTTPException(
            status_code=409,
            detail="browser action requires approval before execution; call /approve first",
        )
    if run.status in ("running", "completed"):
        return BrowserActionResponse(
            run_id=run.id,
            status=run.status,
            approval_status=run.approval_status,
            risk_level=run.risk_level,
            target_url=run.target_url,
            target_domain=run.target_domain,
            error_message=run.error_message,
            started_at=run.started_at,
            completed_at=run.completed_at,
            result=run.result_json or {},
        )
    spec = get_graph("browser_automation")
    state: dict = {
        "run_id": run.id,
        "action_type": run.action_type,
        "target_url": run.target_url,
        "field_values": (run.preview_json or {}).get("normalized") or {},
        "submit": run.action_type in ("submit_form", "append_invoice_row"),
        "actor": actor,
    }
    try:
        for node_name in spec.node_names:
            handler = spec.handlers[node_name]
            patch = handler(state, runner=None) or {}
            state.update(patch)
    except Exception as exc:
        logger.exception("browser workflow failed for run %s", run.id)
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=f"browser workflow failed: {exc}")
    db.refresh(run)
    return BrowserActionResponse(
        run_id=run.id,
        status=run.status,
        approval_status=run.approval_status,
        risk_level=run.risk_level,
        target_url=run.target_url,
        target_domain=run.target_domain,
        error_message=run.error_message,
        started_at=run.started_at,
        completed_at=run.completed_at,
        result=run.result_json or {},
    )


@router.post("/open-url", response_model=BrowserActionResponse)
def execute_open_url(payload: BrowserActionRequest, db: Session = Depends(get_db)):
    return _run_browser_workflow(db, run_id=payload.run_id, actor=payload.actor)


@router.post("/fill-form", response_model=BrowserActionResponse)
def execute_fill_form(payload: BrowserActionRequest, db: Session = Depends(get_db)):
    return _run_browser_workflow(db, run_id=payload.run_id, actor=payload.actor)


@router.post("/append-invoice-row", response_model=BrowserActionResponse)
def execute_append_invoice_row(
    payload: BrowserActionRequest, db: Session = Depends(get_db)
):
    return _run_browser_workflow(db, run_id=payload.run_id, actor=payload.actor)


@router.post("/click-approved-button", response_model=BrowserActionResponse)
def execute_click_approved_button(
    payload: BrowserActionRequest, db: Session = Depends(get_db)
):
    return _run_browser_workflow(db, run_id=payload.run_id, actor=payload.actor)


# ---------------------------------------------------------------------------
# Approval / reject / cancel
# ---------------------------------------------------------------------------


@router.post("/actions/{action_id}/approve", response_model=BrowserActionResponse)
def approve_action(
    action_id: int,
    payload: BrowserApprovalRequest,
    db: Session = Depends(get_db),
):
    run = db.get(BrowserActionRun, action_id)
    if run is None:
        raise HTTPException(status_code=404, detail="browser action run not found")
    if run.approval_status not in ("pending", "not_required"):
        raise HTTPException(
            status_code=409,
            detail=f"browser action is in approval_status={run.approval_status!r}",
        )
    run.approval_status = "approved"
    run.status = "approved"
    log_action(
        db,
        actor=payload.actor,
        action="browser.action.approve",
        entity_type="browser_action_run",
        entity_id=run.id,
        details=payload.reason or "User approved the browser action.",
        after_data={"approval_status": "approved"},
    )
    db.commit()
    # Auto-execute after approval unless the caller wants to
    # inspect the preview first. The spec's "approve" is
    # intended to be the moment of execution.
    return _run_browser_workflow(db, run_id=run.id, actor=payload.actor)


@router.post("/actions/{action_id}/reject", response_model=BrowserActionResponse)
def reject_action(
    action_id: int,
    payload: BrowserRejectRequest,
    db: Session = Depends(get_db),
):
    run = db.get(BrowserActionRun, action_id)
    if run is None:
        raise HTTPException(status_code=404, detail="browser action run not found")
    run.approval_status = "rejected"
    run.status = "rejected"
    run.completed_at = datetime.utcnow()
    log_action(
        db,
        actor=payload.actor,
        action="browser.action.reject",
        entity_type="browser_action_run",
        entity_id=run.id,
        details=payload.reason or "User rejected the browser action.",
        after_data={"approval_status": "rejected"},
    )
    db.commit()
    return BrowserActionResponse(
        run_id=run.id,
        status=run.status,
        approval_status=run.approval_status,
        risk_level=run.risk_level,
        target_url=run.target_url,
        target_domain=run.target_domain,
        error_message=run.error_message,
        started_at=run.started_at,
        completed_at=run.completed_at,
        result=run.result_json or {},
    )


@router.post("/actions/{action_id}/cancel", response_model=BrowserActionResponse)
def cancel_action(
    action_id: int,
    payload: BrowserCancelRequest,
    db: Session = Depends(get_db),
):
    run = db.get(BrowserActionRun, action_id)
    if run is None:
        raise HTTPException(status_code=404, detail="browser action run not found")
    if run.status in ("completed", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"browser action already finished (status={run.status!r})",
        )
    run.status = "cancelled"
    run.approval_status = "rejected"
    run.completed_at = datetime.utcnow()
    log_action(
        db,
        actor=payload.actor,
        action="browser.action.cancel",
        entity_type="browser_action_run",
        entity_id=run.id,
        details=payload.reason or "User cancelled the browser action.",
        after_data={"status": "cancelled"},
    )
    db.commit()
    ba.reset_adapter()
    return BrowserActionResponse(
        run_id=run.id,
        status=run.status,
        approval_status=run.approval_status,
        risk_level=run.risk_level,
        target_url=run.target_url,
        target_domain=run.target_domain,
        error_message=run.error_message,
        started_at=run.started_at,
        completed_at=run.completed_at,
        result=run.result_json or {},
    )


# ---------------------------------------------------------------------------
# Logs / read
# ---------------------------------------------------------------------------


@router.get("/actions", response_model=list[BrowserActionRunSummary])
def list_actions(
    limit: int = Query(50, ge=1, le=500),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    q = db.query(BrowserActionRun).order_by(BrowserActionRun.id.desc())
    if status_filter:
        q = q.filter(BrowserActionRun.status == status_filter)
    return q.limit(limit).all()


@router.get("/actions/{action_id}", response_model=BrowserActionRunRead)
def get_action(action_id: int, db: Session = Depends(get_db)):
    run = db.get(BrowserActionRun, action_id)
    if run is None:
        raise HTTPException(status_code=404, detail="browser action run not found")
    return run


@router.get("/actions/{action_id}/steps", response_model=list[BrowserActionStepRead])
def get_action_steps(action_id: int, db: Session = Depends(get_db)):
    run = db.get(BrowserActionRun, action_id)
    if run is None:
        raise HTTPException(status_code=404, detail="browser action run not found")
    return (
        db.query(BrowserActionStep)
        .filter(BrowserActionStep.browser_action_run_id == action_id)
        .order_by(BrowserActionStep.step_order.asc(), BrowserActionStep.id.asc())
        .all()
    )


@router.get(
    "/actions/{action_id}/snapshot",
    response_model=list[BrowserPageSnapshotRead],
)
def get_action_snapshots(action_id: int, db: Session = Depends(get_db)):
    run = db.get(BrowserActionRun, action_id)
    if run is None:
        raise HTTPException(status_code=404, detail="browser action run not found")
    return (
        db.query(BrowserPageSnapshot)
        .filter(BrowserPageSnapshot.browser_action_run_id == action_id)
        .order_by(BrowserPageSnapshot.id.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Voice intent dispatch
# ---------------------------------------------------------------------------


@router.get("/voices")
def list_voice_intents():
    """List the voice intents the browser layer recognises.

    Returns both the spec (action, default URL, needs_approval)
    and a friendly description for the UI."""
    out = []
    for name, spec in ba.VOICE_INTENTS.items():
        out.append(
            {
                "intent": name,
                "action_type": spec.get("action_type"),
                "default_url": spec.get("default_url", ""),
                "needs_approval": bool(spec.get("needs_approval", False)),
                "blocked": bool(spec.get("blocked", False)),
                "note": spec.get("note", ""),
            }
        )
    return out


@router.post("/voice", response_model=BrowserVoiceIntentResponse)
def voice_dispatch(payload: BrowserVoiceIntentRequest, db: Session = Depends(get_db)):
    spec = ba.VOICE_INTENTS.get(payload.intent)
    if spec is None:
        raise HTTPException(
            status_code=404, detail=f"unknown voice intent: {payload.intent!r}"
        )
    if spec.get("blocked"):
        log_action(
            db,
            actor=payload.actor,
            action="browser.voice.blocked",
            entity_type="voice_intent",
            entity_id=None,
            details=spec.get("note", "voice intent is blocked in this phase"),
            after_data={"intent": payload.intent},
        )
        db.commit()
        return BrowserVoiceIntentResponse(
            intent=payload.intent,
            blocked=True,
            preview=None,
            message=spec.get("note", "voice intent is blocked in this phase"),
        )
    target_url = payload.target_url or spec.get("default_url") or ""
    preview_obj = ba.voice_intent_preview(
        payload.intent, target_url=target_url
    )
    if preview_obj is None:
        raise HTTPException(status_code=404, detail="voice intent has no preview")
    # Persist a preview row for the UI to attach to.
    run = BrowserActionRun(
        source_type="voice",
        source_id=None,
        workflow_run_id=None,
        voice_command_id=None,
        action_type=preview_obj.action_type,
        target_url=preview_obj.target_url,
        target_domain=preview_obj.target_domain,
        risk_level=preview_obj.risk.risk_level,
        approval_status=("pending" if preview_obj.risk.requires_approval else "not_required"),
        status="awaiting_approval" if preview_obj.risk.requires_approval else "approved",
        preview_json=preview_obj.to_dict(),
    )
    db.add(run)
    log_action(
        db,
        actor=payload.actor,
        action="browser.voice.preview",
        entity_type="browser_action_run",
        entity_id=None,
        details=f"Voice intent {payload.intent!r} -> preview built for {target_url}",
        after_data={"preview": preview_obj.to_dict()},
    )
    db.commit()
    db.refresh(run)
    message = (
        "voice intent requires approval; show the preview modal"
        if preview_obj.risk.requires_approval
        else "voice intent is read-only and can run without further approval"
    )
    return BrowserVoiceIntentResponse(
        intent=payload.intent,
        blocked=False,
        preview=BrowserActionPreview(**preview_obj.to_dict()),
        message=message,
    )


# ---------------------------------------------------------------------------
# Test form
# ---------------------------------------------------------------------------


@router.get("/test-form", response_class=HTMLResponse)
def render_test_form():
    return HTMLResponse(content=ba.render_test_form_html())


@router.post("/test-form/fill-preview", response_model=BrowserPreviewResponse)
def test_form_fill_preview(
    payload: BrowserTestFormFillRequest, db: Session = Depends(get_db)
):
    settings = get_settings()
    target_url = f"http://127.0.0.1:{settings.agent_port}/api/browser/test-form"
    return _build_preview(
        db,
        action_type="fill_form",
        target_url=target_url,
        field_values={},
        submit=payload.submit,
        invoice_id=payload.invoice_id,
        source_type="test_form",
        source_id=None,
        workflow_run_id=None,
        voice_command_id=None,
        actor=payload.actor,
    )


# ---------------------------------------------------------------------------
# Phase 12 lifecycle hook: prune old runs on startup
# ---------------------------------------------------------------------------


def prune_old_runs(db: Session) -> int:
    settings = get_settings()
    keep = settings.browser_max_runs
    if keep <= 0:
        return 0
    total = db.query(BrowserActionRun).count()
    if total <= keep:
        return 0
    cutoff_id = (
        db.query(BrowserActionRun.id)
        .order_by(BrowserActionRun.id.desc())
        .offset(keep)
        .limit(1)
        .scalar()
    )
    if cutoff_id is None:
        return 0
    deleted_steps = (
        db.query(BrowserActionStep)
        .filter(BrowserActionStep.browser_action_run_id < cutoff_id)
        .delete(synchronize_session=False)
    )
    deleted_snaps = (
        db.query(BrowserPageSnapshot)
        .filter(BrowserPageSnapshot.browser_action_run_id < cutoff_id)
        .delete(synchronize_session=False)
    )
    deleted_runs = (
        db.query(BrowserActionRun)
        .filter(BrowserActionRun.id < cutoff_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    logger.info(
        "browser_automation prune: deleted %s runs / %s steps / %s snapshots",
        deleted_runs,
        deleted_steps,
        deleted_snaps,
    )
    return int(deleted_runs or 0)
