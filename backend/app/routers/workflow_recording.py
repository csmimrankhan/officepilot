"""Phase 14 — Workflow Recording HTTP API.

Endpoints (all under ``/api/recording``):

``GET    /policies``
``PATCH  /policies``
``POST   /start``
``POST   /stop``
``POST   /events``
``GET    /sessions``
``GET    /sessions/{session_id}``
``POST   /sessions/{session_id}/save``
``GET    /workflows``
``POST   /workflows``
``GET    /workflows/{workflow_id}``
``PATCH  /workflows/{workflow_id}``
``DELETE /workflows/{workflow_id}``
``GET    /workflows/{workflow_id}/steps``
``PATCH  /workflows/{workflow_id}/steps/{step_id}``
``POST   /workflows/{workflow_id}/duplicate``
``POST   /workflows/{workflow_id}/dry-run``
``POST   /workflows/{workflow_id}/replay``
``POST   /runs/{run_id}/approve-step``
``POST   /runs/{run_id}/reject-step``
``POST   /runs/{run_id}/pause``
``POST   /runs/{run_id}/resume``
``POST   /runs/{run_id}/emergency-stop``
``GET    /runs``
``GET    /runs/{run_id}``
``GET    /runs/{run_id}/steps``
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.recorded_workflow import RecordedWorkflow
from ..models.recorded_workflow_step import RecordedWorkflowStep
from ..models.workflow_recording_policy import WorkflowRecordingPolicy
from ..models.workflow_recording_session import WorkflowRecordingSession
from ..models.workflow_replay_run import WorkflowReplayRun
from ..models.workflow_replay_step_log import WorkflowReplayStepLog
from ..schemas.workflow_recording import (
    CaptureEventRequest, CaptureEventResponse,
    RecordedWorkflowCreate, RecordedWorkflowUpdate, RecordedWorkflowRead,
    RecordedWorkflowStepRead, RecordedWorkflowStepUpdate,
    RecordingStartResponse, RecordingStopResponse,
    ReplayStartResponse, ReplayStopResponse, StepActionResponse,
    WorkflowDuplicateResponse,
    WorkflowRecordingPolicyRead, WorkflowRecordingPolicyUpdate,
    WorkflowRecordingSessionRead,
    WorkflowReplayRunRead, WorkflowReplayStepLogRead,
)
from ..services.workflow_recording import (
    start_recording, stop_recording, capture_event,
    save_recording_as_workflow, convert_raw_events_to_steps,
    start_dry_run, start_step_by_step_replay,
    approve_step, reject_step, pause_replay, resume_replay,
    emergency_stop, build_action_preview, validate_step_result,
    get_or_create_policy, classify_step_risk,
    blocked_app_check, blocked_domain_check,
)
from ..services.audit import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/recording", tags=["workflow_recording"])


# ── Policy ─────────────────────────────────────────────────────────────────


@router.get("/policies", response_model=WorkflowRecordingPolicyRead)
def get_policies(db: Session = Depends(get_db)):
    policy = get_or_create_policy(db)
    return policy


@router.patch("/policies", response_model=WorkflowRecordingPolicyRead)
def update_policies(payload: WorkflowRecordingPolicyUpdate, db: Session = Depends(get_db)):
    policy = get_or_create_policy(db)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(policy, key, value)
    policy.updated_at = datetime.utcnow()
    log_action(
        db,
        actor="user",
        action="recording.policy.update",
        entity_type="workflow_recording_policy",
        entity_id=policy.id,
        details="Updated workflow recording policy",
        after_data=update_data,
    )
    db.commit()
    db.refresh(policy)
    return policy


# ── Recording Sessions ─────────────────────────────────────────────────────


@router.post("/start", response_model=RecordingStartResponse)
def start_recording_session(db: Session = Depends(get_db)):
    result = start_recording(db)
    log_action(
        db,
        actor="user",
        action="recording.start",
        entity_type="workflow_recording_session",
        entity_id=result["session_id"],
        details="Started workflow recording session",
    )
    db.commit()
    return RecordingStartResponse(
        session_id=result["session_id"],
        status=result["status"],
    )


@router.post("/stop", response_model=RecordingStopResponse)
def stop_recording_session(session_id: int = Query(...), db: Session = Depends(get_db)):
    session = db.get(WorkflowRecordingSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Recording session not found")
    result = stop_recording(db, session_id)
    log_action(
        db,
        actor="user",
        action="recording.stop",
        entity_type="workflow_recording_session",
        entity_id=session_id,
        details=f"Stopped recording session #{session_id}",
    )
    db.commit()
    return RecordingStopResponse(
        session_id=result["session_id"],
        status=result["status"],
        event_count=result["event_count"],
        workflow_id=result.get("workflow_id"),
    )


@router.post("/events", response_model=CaptureEventResponse)
def capture_event_endpoint(
    payload: CaptureEventRequest,
    session_id: int = Query(...),
    db: Session = Depends(get_db),
):
    session = db.get(WorkflowRecordingSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Recording session not found")
    result = capture_event(db, session_id, event=payload.model_dump())
    return CaptureEventResponse(
        captured=result["captured"],
        redacted=result["redacted"],
        event_index=result["event_index"],
    )


@router.get("/sessions", response_model=list[WorkflowRecordingSessionRead])
def list_sessions(db: Session = Depends(get_db)):
    return (
        db.query(WorkflowRecordingSession)
        .order_by(WorkflowRecordingSession.id.desc())
        .all()
    )


@router.get("/sessions/{session_id}", response_model=WorkflowRecordingSessionRead)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.get(WorkflowRecordingSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Recording session not found")
    return session


@router.post("/sessions/{session_id}/save", response_model=WorkflowDuplicateResponse)
def save_session_as_workflow(
    session_id: int,
    name: str = Query(...),
    description: str = Query(""),
    db: Session = Depends(get_db),
):
    session = db.get(WorkflowRecordingSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Recording session not found")
    result = save_recording_as_workflow(db, session_id, name, description)
    log_action(
        db,
        actor="user",
        action="recording.save",
        entity_type="recorded_workflow",
        entity_id=result["workflow_id"],
        details=f"Saved recording session #{session_id} as workflow '{name}'",
    )
    db.commit()
    return WorkflowDuplicateResponse(
        workflow_id=result["workflow_id"],
        name=result["name"],
    )


# ── Recorded Workflows ─────────────────────────────────────────────────────


@router.get("/workflows", response_model=list[RecordedWorkflowRead])
def list_workflows(db: Session = Depends(get_db)):
    return (
        db.query(RecordedWorkflow)
        .order_by(RecordedWorkflow.updated_at.desc())
        .all()
    )


@router.post("/workflows", response_model=RecordedWorkflowRead)
def create_workflow(payload: RecordedWorkflowCreate, db: Session = Depends(get_db)):
    workflow = RecordedWorkflow(
        name=payload.name,
        description=payload.description,
        source_type=payload.source_type,
    )
    db.add(workflow)
    db.flush()
    log_action(
        db,
        actor="user",
        action="workflow.create",
        entity_type="recorded_workflow",
        entity_id=workflow.id,
        details=f"Created manual workflow '{payload.name}'",
    )
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/workflows/{workflow_id}", response_model=RecordedWorkflowRead)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.get(RecordedWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.patch("/workflows/{workflow_id}", response_model=RecordedWorkflowRead)
def update_workflow(
    workflow_id: int,
    payload: RecordedWorkflowUpdate,
    db: Session = Depends(get_db),
):
    workflow = db.get(RecordedWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(workflow, key, value)
    workflow.updated_at = datetime.utcnow()
    log_action(
        db,
        actor="user",
        action="workflow.update",
        entity_type="recorded_workflow",
        entity_id=workflow.id,
        details=f"Updated workflow #{workflow_id}",
        after_data=update_data,
    )
    db.commit()
    db.refresh(workflow)
    return workflow


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.get(RecordedWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.query(RecordedWorkflowStep).filter(
        RecordedWorkflowStep.workflow_id == workflow_id
    ).delete()
    db.delete(workflow)
    log_action(
        db,
        actor="user",
        action="workflow.delete",
        entity_type="recorded_workflow",
        entity_id=workflow_id,
        details=f"Deleted workflow #{workflow_id}",
    )
    db.commit()
    return {"deleted": True, "workflow_id": workflow_id}


# ── Workflow Steps ─────────────────────────────────────────────────────────


@router.get(
    "/workflows/{workflow_id}/steps",
    response_model=list[RecordedWorkflowStepRead],
)
def list_workflow_steps(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.get(RecordedWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return (
        db.query(RecordedWorkflowStep)
        .filter(RecordedWorkflowStep.workflow_id == workflow_id)
        .order_by(RecordedWorkflowStep.step_order)
        .all()
    )


@router.patch(
    "/workflows/{workflow_id}/steps/{step_id}",
    response_model=RecordedWorkflowStepRead,
)
def update_workflow_step(
    workflow_id: int,
    step_id: int,
    payload: RecordedWorkflowStepUpdate,
    db: Session = Depends(get_db),
):
    workflow = db.get(RecordedWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    step = (
        db.query(RecordedWorkflowStep)
        .filter(
            RecordedWorkflowStep.id == step_id,
            RecordedWorkflowStep.workflow_id == workflow_id,
        )
        .first()
    )
    if step is None:
        raise HTTPException(status_code=404, detail="Step not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(step, key, value)
    log_action(
        db,
        actor="user",
        action="workflow.step.update",
        entity_type="recorded_workflow_step",
        entity_id=step_id,
        details=f"Updated step #{step_id} in workflow #{workflow_id}",
    )
    db.commit()
    db.refresh(step)
    return step


@router.post(
    "/workflows/{workflow_id}/duplicate",
    response_model=WorkflowDuplicateResponse,
)
def duplicate_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.get(RecordedWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    new_workflow = RecordedWorkflow(
        name=f"{workflow.name} (copy)",
        description=workflow.description,
        status="draft",
        source_type=workflow.source_type,
        risk_level=workflow.risk_level,
        replay_mode_default=workflow.replay_mode_default,
    )
    db.add(new_workflow)
    db.flush()
    steps = (
        db.query(RecordedWorkflowStep)
        .filter(RecordedWorkflowStep.workflow_id == workflow_id)
        .order_by(RecordedWorkflowStep.step_order)
        .all()
    )
    for step in steps:
        new_step = RecordedWorkflowStep(
            workflow_id=new_workflow.id,
            step_order=step.step_order,
            step_type=step.step_type,
            app_name=step.app_name,
            window_title=step.window_title,
            target_description=step.target_description,
            selector_json=step.selector_json,
            ui_automation_json=step.ui_automation_json,
            fallback_coordinates_json=step.fallback_coordinates_json,
            input_value_redacted=step.input_value_redacted,
            expected_result_json=step.expected_result_json,
            requires_approval=step.requires_approval,
            risk_level=step.risk_level,
            enabled=step.enabled,
        )
        db.add(new_step)
    new_workflow.total_steps = len(steps)
    log_action(
        db,
        actor="user",
        action="workflow.duplicate",
        entity_type="recorded_workflow",
        entity_id=new_workflow.id,
        details=f"Duplicated workflow #{workflow_id} as '{new_workflow.name}'",
    )
    db.commit()
    db.refresh(new_workflow)
    return WorkflowDuplicateResponse(
        workflow_id=new_workflow.id,
        name=new_workflow.name,
    )


# ── Replay ─────────────────────────────────────────────────────────────────


@router.post(
    "/workflows/{workflow_id}/dry-run",
    response_model=ReplayStartResponse,
)
def dry_run_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.get(RecordedWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    result = start_dry_run(db, workflow_id)
    log_action(
        db,
        actor="user",
        action="replay.dry_run",
        entity_type="workflow_replay_run",
        entity_id=result["run_id"],
        details=f"Dry-run replay of workflow #{workflow_id}",
    )
    db.commit()
    return ReplayStartResponse(
        run_id=result["run_id"],
        mode=result["mode"],
        total_steps=result["total_steps"],
    )


@router.post(
    "/workflows/{workflow_id}/replay",
    response_model=ReplayStartResponse,
)
def replay_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.get(RecordedWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    result = start_step_by_step_replay(db, workflow_id)
    log_action(
        db,
        actor="user",
        action="replay.start",
        entity_type="workflow_replay_run",
        entity_id=result["run_id"],
        details=f"Started step-by-step replay of workflow #{workflow_id}",
    )
    db.commit()
    return ReplayStartResponse(
        run_id=result["run_id"],
        mode=result["mode"],
        total_steps=result["total_steps"],
        first_step=result.get("first_step"),
    )


@router.post(
    "/runs/{run_id}/approve-step",
    response_model=StepActionResponse,
)
def approve_replay_step(
    run_id: int,
    step_log_id: int = Query(...),
    db: Session = Depends(get_db),
):
    run = db.get(WorkflowReplayRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Replay run not found")
    result = approve_step(db, run_id, step_log_id)
    return StepActionResponse(
        step_log_id=result["step_log_id"],
        action_preview=result["action_preview"],
        requires_approval=result["requires_approval"],
        risk_level=result["risk_level"],
    )


@router.post(
    "/runs/{run_id}/reject-step",
    response_model=ReplayStopResponse,
)
def reject_replay_step(
    run_id: int,
    step_log_id: int = Query(...),
    db: Session = Depends(get_db),
):
    run = db.get(WorkflowReplayRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Replay run not found")
    result = reject_step(db, run_id, step_log_id)
    log_action(
        db,
        actor="user",
        action="replay.reject",
        entity_type="workflow_replay_step_log",
        entity_id=step_log_id,
        details=f"Rejected step log #{step_log_id} in replay run #{run_id}",
    )
    db.commit()
    return ReplayStopResponse(
        stopped=result["stopped"],
        run_id=result["run_id"],
        status=result["status"],
    )


@router.post("/runs/{run_id}/pause")
def pause_replay_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(WorkflowReplayRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Replay run not found")
    pause_replay(db, run_id)
    db.commit()
    return {"paused": True, "run_id": run_id}


@router.post("/runs/{run_id}/resume")
def resume_replay_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(WorkflowReplayRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Replay run not found")
    resume_replay(db, run_id)
    db.commit()
    return {"resumed": True, "run_id": run_id}


@router.post(
    "/runs/{run_id}/emergency-stop",
    response_model=ReplayStopResponse,
)
def emergency_stop_replay(run_id: int, db: Session = Depends(get_db)):
    run = db.get(WorkflowReplayRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Replay run not found")
    result = emergency_stop(db, run_id)
    log_action(
        db,
        actor="user",
        action="replay.emergency_stop",
        entity_type="workflow_replay_run",
        entity_id=run_id,
        details=f"Emergency stop of replay run #{run_id}",
    )
    db.commit()
    return ReplayStopResponse(
        stopped=result["stopped"],
        run_id=result["run_id"],
        status=result["status"],
    )


# ── Replay Runs ────────────────────────────────────────────────────────────


@router.get("/runs", response_model=list[WorkflowReplayRunRead])
def list_replay_runs(db: Session = Depends(get_db)):
    return (
        db.query(WorkflowReplayRun)
        .order_by(WorkflowReplayRun.id.desc())
        .all()
    )


@router.get("/runs/{run_id}", response_model=WorkflowReplayRunRead)
def get_replay_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(WorkflowReplayRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Replay run not found")
    return run


@router.get(
    "/runs/{run_id}/steps",
    response_model=list[WorkflowReplayStepLogRead],
)
def list_replay_step_logs(run_id: int, db: Session = Depends(get_db)):
    run = db.get(WorkflowReplayRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Replay run not found")
    return (
        db.query(WorkflowReplayStepLog)
        .filter(WorkflowReplayStepLog.replay_run_id == run_id)
        .order_by(WorkflowReplayStepLog.step_order)
        .all()
    )
