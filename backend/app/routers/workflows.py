"""Phase 6 — workflow API endpoints.

- ``POST /api/workflows/run/{workflow_name}``         — start a new run
- ``GET  /api/workflows/runs``                         — list runs
- ``GET  /api/workflows/runs/{id}``                    — run + logs + approvals
- ``POST /api/workflows/runs/{id}/approve``            — approve a pending checkpoint
- ``POST /api/workflows/runs/{id}/reject``             — reject a pending checkpoint
- ``POST /api/workflows/runs/{id}/cancel``             — cancel a run
- ``POST /api/workflows/runs/{id}/retry``              — retry from a failed node
- ``GET  /api/workflows/graphs``                       — list registered graphs
- ``GET  /api/workflows/runs/{id}/approvals``          — list approvals (incl. resolved)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.workflow_approval import ApprovalStatus, WorkflowApproval
from ..models.workflow_log import NodeLogStatus, WorkflowLog
from ..models.workflow_run import WorkflowRun, WorkflowStatus
from ..services import versioning as versioning_svc
from ..services.workflows import list_graphs
from ..services.workflows.registry import get_graph
from ..services.workflows.runner import WorkflowRunner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# --------------------------------------------------------------- schemas


class RunRequest(BaseModel):
    input: dict = Field(default_factory=dict)
    actor: Optional[str] = None


class ApprovalRequest(BaseModel):
    actor: str
    note: Optional[str] = None


class RejectRequest(BaseModel):
    actor: str
    note: Optional[str] = None


class CancelRequest(BaseModel):
    actor: str
    note: Optional[str] = None


class RetryRequest(BaseModel):
    actor: str
    from_node: Optional[str] = None


# --------------------------------------------------------------- serializers


def _serialize_run(run: WorkflowRun) -> dict:
    return {
        "id": run.id,
        "workflow_name": run.workflow_name,
        "status": run.status,
        "current_node": run.current_node,
        "input": run.input_json or {},
        "error_message": run.error_message,
        "actor": run.actor,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


def _serialize_log(log: WorkflowLog) -> dict:
    return {
        "id": log.id,
        "node_name": log.node_name,
        "status": log.status,
        "message": log.message,
        "data": log.data_json or {},
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def _serialize_approval(a: WorkflowApproval) -> dict:
    return {
        "id": a.id,
        "node_name": a.node_name,
        "status": a.status,
        "message": a.approval_message,
        "before": a.before_data_json,
        "after": a.after_data_json,
        "approved_by": a.approved_by,
        "approved_at": a.approved_at.isoformat() if a.approved_at else None,
        "decision_note": a.decision_note,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _serialize_detail(run: WorkflowRun, db: Session) -> dict:
    logs = (
        db.query(WorkflowLog)
        .filter(WorkflowLog.workflow_run_id == run.id)
        .order_by(WorkflowLog.id.asc())
        .all()
    )
    approvals = (
        db.query(WorkflowApproval)
        .filter(WorkflowApproval.workflow_run_id == run.id)
        .order_by(WorkflowApproval.id.asc())
        .all()
    )
    pending = [a for a in approvals if a.status == ApprovalStatus.PENDING.value]
    return {
        **_serialize_run(run),
        "state": run.state_json or {},
        "logs": [_serialize_log(l) for l in logs],
        "approvals": [_serialize_approval(a) for a in approvals],
        "pending_approval": _serialize_approval(pending[-1]) if pending else None,
    }


def _capture_workflow_version(
    db: Session,
    *,
    run: WorkflowRun,
    source_action: str,
    actor: str,
    change_summary: Optional[str] = None,
) -> None:
    """Phase 10: snapshot a workflow run's full state (status, current
    node, state_json, input_json, error_message, completed_at, plus
    a flattened view of all node logs and approvals) so a restore
    re-creates the exact pre-mutation state."""
    logs = (
        db.query(WorkflowLog)
        .filter(WorkflowLog.workflow_run_id == run.id)
        .order_by(WorkflowLog.id.asc())
        .all()
    )
    approvals = (
        db.query(WorkflowApproval)
        .filter(WorkflowApproval.workflow_run_id == run.id)
        .order_by(WorkflowApproval.id.asc())
        .all()
    )
    snapshot = {
        "status": run.status,
        "current_node": run.current_node,
        "error_message": run.error_message,
        "state_json": run.state_json or {},
        "input_json": run.input_json or {},
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "logs": [
            {
                "node_name": l.node_name,
                "status": l.status,
                "message": l.message,
                "data": l.data_json or {},
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
        "approvals": [
            {
                "node_name": a.node_name,
                "status": a.status,
                "message": a.approval_message,
                "before": a.before_data_json,
                "after": a.after_data_json,
                "approved_by": a.approved_by,
                "approved_at": a.approved_at.isoformat() if a.approved_at else None,
                "decision_note": a.decision_note,
            }
            for a in approvals
        ],
    }
    versioning_svc.capture_workflow_version(
        db,
        workflow_id=run.id,
        workflow_name=run.workflow_name,
        workflow_json=snapshot,
        source_action=source_action,
        created_by=actor,
        change_summary=change_summary,
    )


# --------------------------------------------------------------- endpoints


@router.get("/graphs", summary="List registered workflow graphs")
def get_graphs() -> dict:
    return {"graphs": list_graphs()}


@router.post("/run/{workflow_name}", summary="Start a new workflow run")
def start_run(
    workflow_name: str,
    body: RunRequest,
    db: Session = Depends(get_db),
):
    try:
        spec = get_graph(workflow_name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown workflow: {workflow_name!r}")

    settings = get_settings()
    actor = body.actor or "user"
    run = WorkflowRun(
        workflow_name=workflow_name,
        status=WorkflowStatus.PENDING.value,
        current_node=spec.start,
        state_json=dict(body.input or {}),
        input_json=dict(body.input or {}),
        actor=actor,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    runner = WorkflowRunner(db, run, settings=settings)
    runner.advance(spec.node_handlers_dict, from_node=spec.start)
    db.refresh(run)
    _capture_workflow_version(
        db,
        run=run,
        source_action="workflow.start",
        actor=actor,
        change_summary=f"Started run for workflow {workflow_name!r}",
    )
    db.commit()
    db.refresh(run)
    return _serialize_detail(run, db)


@router.get("/runs", summary="List workflow runs")
def list_runs(
    workflow_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(WorkflowRun).order_by(WorkflowRun.id.desc())
    if workflow_name:
        q = q.filter(WorkflowRun.workflow_name == workflow_name)
    if status:
        q = q.filter(WorkflowRun.status == status)
    rows = q.limit(limit).all()
    return {"runs": [_serialize_run(r) for r in rows]}


@router.get("/runs/{run_id}", summary="Get a workflow run with logs and approvals")
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"workflow run {run_id} not found")
    return _serialize_detail(run, db)


@router.get("/runs/{run_id}/approvals", summary="List approvals for a run")
def list_approvals(run_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(WorkflowApproval)
        .filter(WorkflowApproval.workflow_run_id == run_id)
        .order_by(WorkflowApproval.id.asc())
        .all()
    )
    return {"approvals": [_serialize_approval(a) for a in rows]}


@router.post("/runs/{run_id}/approve", summary="Approve a pending checkpoint")
def approve_run(
    run_id: int,
    body: ApprovalRequest,
    db: Session = Depends(get_db),
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"workflow run {run_id} not found")
    if run.status != WorkflowStatus.AWAITING_APPROVAL.value:
        raise HTTPException(
            status_code=409,
            detail=f"run is not awaiting approval (status={run.status})",
        )
    pending = (
        db.query(WorkflowApproval)
        .filter(
            WorkflowApproval.workflow_run_id == run_id,
            WorkflowApproval.status == ApprovalStatus.PENDING.value,
        )
        .order_by(WorkflowApproval.id.desc())
        .first()
    )
    if pending is None:
        raise HTTPException(status_code=409, detail="no pending approval")
    from datetime import datetime as _dt
    pending.status = ApprovalStatus.APPROVED.value
    pending.approved_by = body.actor
    pending.approved_at = _dt.utcnow()
    pending.decision_note = body.note
    db.add(pending)
    db.commit()
    # Resume the run from the next node.
    spec = get_graph(run.workflow_name)
    node_names = spec.node_names
    try:
        idx = node_names.index(pending.node_name)
        next_node = node_names[idx + 1] if idx + 1 < len(node_names) else None
    except ValueError:
        next_node = None
    if next_node is None:
        # Last node — mark completed.
        run.status = WorkflowStatus.COMPLETED.value
        from datetime import datetime as _dt
        run.completed_at = _dt.utcnow()
        db.add(run)
        db.commit()
    else:
        settings = get_settings()
        runner = WorkflowRunner(db, run, settings=settings)
        runner.advance(spec.node_handlers_dict, from_node=next_node)
    db.refresh(run)
    _capture_workflow_version(
        db,
        run=run,
        source_action="workflow.approve",
        actor=body.actor,
        change_summary=(
            f"Approved checkpoint at node {pending.node_name!r}"
        ),
    )
    db.commit()
    db.refresh(run)
    return _serialize_detail(run, db)


@router.post("/runs/{run_id}/reject", summary="Reject a pending checkpoint")
def reject_run(
    run_id: int,
    body: RejectRequest,
    db: Session = Depends(get_db),
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"workflow run {run_id} not found")
    settings = get_settings()
    runner = WorkflowRunner(db, run, settings=settings)
    pending = runner.pending_approval(run.current_node or "")
    if pending is None:
        raise HTTPException(status_code=409, detail="no pending approval")
    runner.reject(pending.node_name, actor=body.actor, note=body.note)
    db.refresh(run)
    _capture_workflow_version(
        db,
        run=run,
        source_action="workflow.reject",
        actor=body.actor,
        change_summary=(
            f"Rejected checkpoint at node {pending.node_name!r}"
        ),
    )
    db.commit()
    db.refresh(run)
    return _serialize_detail(run, db)


@router.post("/runs/{run_id}/cancel", summary="Cancel a running or pending workflow")
def cancel_run(
    run_id: int,
    body: CancelRequest,
    db: Session = Depends(get_db),
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"workflow run {run_id} not found")
    if run.status in (
        WorkflowStatus.COMPLETED.value,
        WorkflowStatus.FAILED.value,
        WorkflowStatus.CANCELLED.value,
        WorkflowStatus.REJECTED.value,
    ):
        raise HTTPException(
            status_code=409, detail=f"cannot cancel run in status {run.status}"
        )
    settings = get_settings()
    runner = WorkflowRunner(db, run, settings=settings)
    runner.cancel(reason=body.note, actor=body.actor)
    db.refresh(run)
    _capture_workflow_version(
        db,
        run=run,
        source_action="workflow.cancel",
        actor=body.actor,
        change_summary=f"Run cancelled: {body.note or ''}".rstrip(),
    )
    db.commit()
    db.refresh(run)
    return _serialize_detail(run, db)


@router.post("/runs/{run_id}/retry", summary="Retry a failed or cancelled run")
def retry_run(
    run_id: int,
    body: RetryRequest,
    db: Session = Depends(get_db),
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"workflow run {run_id} not found")
    if run.status not in (
        WorkflowStatus.FAILED.value,
        WorkflowStatus.CANCELLED.value,
        WorkflowStatus.REJECTED.value,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"cannot retry run in status {run.status}",
        )
    settings = get_settings()
    # Reset the failed node so the next advance re-runs it.
    # Clear the error from the persisted state so the runner
    # doesn't immediately re-fail on the same marker.
    run.status = WorkflowStatus.RUNNING.value
    run.error_message = None
    from datetime import datetime as _dt
    import json as _json
    run.completed_at = None
    if run.state_json:
        raw = run.state_json
        state = raw if isinstance(raw, dict) else _json.loads(raw)
        state.pop("error", None)
        run.state_json = state
    db.add(run)
    db.commit()
    spec = get_graph(run.workflow_name)
    runner = WorkflowRunner(db, run, settings=settings)
    runner.advance(spec.node_handlers_dict, from_node=body.from_node or run.current_node or spec.start)
    db.refresh(run)
    _capture_workflow_version(
        db,
        run=run,
        source_action="workflow.retry",
        actor=body.actor,
        change_summary=(
            f"Retried from node {body.from_node or run.current_node or spec.start!r}"
        ),
    )
    db.commit()
    db.refresh(run)
    return _serialize_detail(run, db)
