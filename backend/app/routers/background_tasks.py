from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.background_task import BackgroundTask
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.background_runner import BackgroundTaskRunner

logger = logging.getLogger("officepilot.background_tasks_router")

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_answer: str


class RunBackgroundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str
    plan_json: dict


@router.post("/run-background")
def run_background(
    body: RunBackgroundRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = BackgroundTask(
        user_id=current_user.id,
        command=body.command,
        plan_json=json.dumps(body.plan_json),
        status="queued",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    runner = BackgroundTaskRunner.get_instance()
    runner.start_task(task.id)

    return {
        "task_id": task.id,
        "status": task.status,
        "command": task.command,
    }


@router.get("/background-tasks")
def list_background_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tasks = (
        db.query(BackgroundTask)
        .filter(BackgroundTask.user_id == current_user.id)
        .order_by(BackgroundTask.created_at.desc())
        .all()
    )
    return {
        "tasks": [
            {
                "id": t.id,
                "command": t.command,
                "status": t.status,
                "progress_percent": t.progress_percent,
                "current_step_description": t.current_step_description,
                "clarification_question": t.clarification_question,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in tasks
        ]
    }


@router.get("/background-tasks/{task_id}")
def get_background_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Background task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this task")
    return {
        "id": task.id,
        "command": task.command,
        "status": task.status,
        "progress_percent": task.progress_percent,
        "current_step_description": task.current_step_description,
        "clarification_question": task.clarification_question,
        "result_summary": json.loads(task.result_summary_json) if task.result_summary_json else None,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


@router.post("/background-tasks/{task_id}/cancel")
def cancel_background_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Background task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this task")
    if task.status not in ("queued", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task with status '{task.status}'")

    task.status = "cancelled"
    task.updated_at = datetime.utcnow()
    db.commit()
    return {"task_id": task.id, "status": task.status}


@router.post("/background-tasks/{task_id}/answer")
def answer_background_task(
    task_id: int,
    body: AnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Background task not found")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to answer this task")
    if task.status != "paused_for_input":
        raise HTTPException(status_code=400, detail=f"Cannot answer task with status '{task.status}'")

    # Inject user answer into the plan as a new step
    plan = json.loads(task.plan_json)
    steps = plan if isinstance(plan, list) else plan.get("steps", [])
    steps.append({
        "step_order": len(steps) + 1,
        "step_type": "user_input",
        "tool": "user_input",
        "params": {"user_answer": body.user_answer},
        "description": "User provided input for recovery",
        "expected_result": "Input received",
        "requires_approval": False,
        "risk_level": "low",
    })
    if isinstance(plan, list):
        plan = steps
    else:
        plan["steps"] = steps
    task.plan_json = json.dumps(plan)

    task.status = "running"
    task.clarification_question = None
    task.current_step_description = "Resuming after user input..."
    task.updated_at = datetime.utcnow()
    db.commit()

    runner = BackgroundTaskRunner.get_instance()
    runner.start_task(task.id)

    return {"task_id": task.id, "status": task.status, "message": "Answer received, task resumed"}
