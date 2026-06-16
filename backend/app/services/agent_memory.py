from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models.agent_task_plan import AgentTaskPlan
from ..models.agent_workflow_memory import AgentWorkflowMemory
from ..models.agent_workflow_run import AgentWorkflowRun
from ..models.agent_workflow_step_log import AgentWorkflowStepLog


def save_plan(db: Session, user_id: int, command_text: str, context_summary: str | None, plan_json: str | None, risk_level: str) -> AgentTaskPlan:
    plan = AgentTaskPlan(
        user_id=user_id,
        command_text=command_text,
        context_summary=context_summary,
        plan_json=plan_json,
        risk_level=risk_level,
        status="pending",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def approve_plan(db: Session, plan_id: int) -> AgentTaskPlan | None:
    plan = db.query(AgentTaskPlan).filter(AgentTaskPlan.id == plan_id).first()
    if not plan:
        return None
    plan.status = "approved"
    plan.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return plan


def complete_plan(db: Session, plan_id: int) -> AgentTaskPlan | None:
    plan = db.query(AgentTaskPlan).filter(AgentTaskPlan.id == plan_id).first()
    if not plan:
        return None
    plan.status = "completed"
    plan.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return plan


def get_plan(db: Session, plan_id: int) -> AgentTaskPlan | None:
    return db.query(AgentTaskPlan).filter(AgentTaskPlan.id == plan_id).first()


def list_plans(db: Session, user_id: int | None = None, limit: int = 50) -> list[AgentTaskPlan]:
    q = db.query(AgentTaskPlan)
    if user_id is not None:
        q = q.filter(AgentTaskPlan.user_id == user_id)
    return q.order_by(AgentTaskPlan.created_at.desc()).limit(limit).all()


DEFAULT_DAILY_INVOICE_TRIGGERS = [
    "daily invoice process",
    "aaj ki invoice process",
    "invoice process workflow",
    "today invoice workflow",
    "kal wala workflow repeat karo",
    "invoice download karo",
    "daily invoice autopilot",
]


def save_plan_as_workflow(db: Session, user_id: int, plan_id: int, workflow_name: str, workflow_description: str | None = None, trigger_phrases: list[str] | None = None) -> AgentWorkflowMemory | None:
    plan = get_plan(db, plan_id)
    if not plan:
        return None

    steps = []
    if plan.plan_json:
        try:
            plan_data = json.loads(plan.plan_json)
            steps = plan_data.get("steps", [])
        except (json.JSONDecodeError, TypeError):
            steps = []

    platform_hint = "unknown"
    if plan.plan_json:
        try:
            plan_data = json.loads(plan.plan_json)
            platform_hint = plan_data.get("platform_detected", "unknown")
        except (json.JSONDecodeError, TypeError):
            pass

    if not trigger_phrases:
        if "daily invoice" in workflow_name.lower() or "invoice" in workflow_name.lower():
            trigger_phrases = DEFAULT_DAILY_INVOICE_TRIGGERS
        else:
            trigger_phrases = []

    memory = AgentWorkflowMemory(
        user_id=user_id,
        workflow_name=workflow_name,
        workflow_description=workflow_description,
        source_task_plan_id=plan_id,
        steps_json=json.dumps(steps),
        platform_hint=platform_hint,
        run_count=0,
        trigger_phrases_json=json.dumps(trigger_phrases) if trigger_phrases else None,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def list_workflow_memory(db: Session, user_id: int | None = None, limit: int = 50) -> list[AgentWorkflowMemory]:
    q = db.query(AgentWorkflowMemory)
    if user_id is not None:
        q = q.filter(AgentWorkflowMemory.user_id == user_id)
    return q.order_by(AgentWorkflowMemory.last_run_at.desc().nullslast(), AgentWorkflowMemory.created_at.desc()).limit(limit).all()


def get_workflow_memory(db: Session, workflow_id: int) -> AgentWorkflowMemory | None:
    return db.query(AgentWorkflowMemory).filter(AgentWorkflowMemory.id == workflow_id).first()


def find_recent_workflow(db: Session, query: str, user_id: int) -> AgentWorkflowMemory | None:
    workflows = list_workflow_memory(db, user_id=user_id)
    ql = query.lower()
    for w in workflows:
        if ql in w.workflow_name.lower():
            return w
        if w.workflow_description and ql in w.workflow_description.lower():
            return w
    return None


def find_yesterday_workflows(db: Session, user_id: int) -> list[AgentWorkflowMemory]:
    from datetime import date, timedelta
    yesterday = date.today() - timedelta(days=1)

    runs = (
        db.query(AgentWorkflowRun)
        .filter(
            AgentWorkflowRun.user_id == user_id,
            AgentWorkflowRun.run_date == yesterday,
            AgentWorkflowRun.status == "completed",
        )
        .order_by(AgentWorkflowRun.started_at.desc())
        .all()
    )

    memory_ids = {r.workflow_memory_id for r in runs if r.workflow_memory_id}
    if memory_ids:
        return db.query(AgentWorkflowMemory).filter(AgentWorkflowMemory.id.in_(memory_ids)).all()

    yesterday_start = datetime.utcnow() - timedelta(hours=48)
    return (
        db.query(AgentWorkflowMemory)
        .filter(
            AgentWorkflowMemory.user_id == user_id,
            AgentWorkflowMemory.last_run_at >= yesterday_start,
        )
        .order_by(AgentWorkflowMemory.last_run_at.desc())
        .all()
    )


def repeat_workflow(db: Session, workflow_memory_id: int, user_id: int, command_text: str | None = None, mode: str = "dry_run") -> AgentWorkflowRun | None:
    memory = get_workflow_memory(db, workflow_memory_id)
    if not memory:
        return None

    from datetime import date
    run = AgentWorkflowRun(
        workflow_memory_id=workflow_memory_id,
        user_id=user_id,
        command_text=command_text,
        mode=mode,
        status="running",
        run_date=date.today(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    steps = []
    if memory.steps_json:
        try:
            steps = json.loads(memory.steps_json)
        except (json.JSONDecodeError, TypeError):
            steps = []

    for step in steps:
        log = AgentWorkflowStepLog(
            workflow_run_id=run.id,
            step_order=step.get("step_order", 1),
            step_type=step.get("step_type", "unknown"),
            status="pending",
            action_preview_json=json.dumps({
                "target": step.get("target", ""),
                "instruction": step.get("instruction", ""),
                "expected_result": step.get("expected_result", ""),
            }),
        )
        db.add(log)

    db.commit()

    memory.run_count = (memory.run_count or 0) + 1
    memory.last_run_at = datetime.utcnow()
    db.commit()

    db.refresh(run)
    return run


def complete_run(db: Session, run_id: int, error_message: str | None = None) -> AgentWorkflowRun | None:
    run = db.query(AgentWorkflowRun).filter(AgentWorkflowRun.id == run_id).first()
    if not run:
        return None
    run.status = "completed" if not error_message else "failed"
    run.completed_at = datetime.utcnow()
    run.error_message = error_message
    db.commit()
    db.refresh(run)
    return run


def get_run(db: Session, run_id: int) -> AgentWorkflowRun | None:
    return db.query(AgentWorkflowRun).filter(AgentWorkflowRun.id == run_id).first()


def list_runs(db: Session, workflow_memory_id: int | None = None, user_id: int | None = None, limit: int = 50) -> list[AgentWorkflowRun]:
    q = db.query(AgentWorkflowRun)
    if workflow_memory_id is not None:
        q = q.filter(AgentWorkflowRun.workflow_memory_id == workflow_memory_id)
    if user_id is not None:
        q = q.filter(AgentWorkflowRun.user_id == user_id)
    return q.order_by(AgentWorkflowRun.started_at.desc()).limit(limit).all()


def list_step_logs(db: Session, run_id: int) -> list[AgentWorkflowStepLog]:
    return (
        db.query(AgentWorkflowStepLog)
        .filter(AgentWorkflowStepLog.workflow_run_id == run_id)
        .order_by(AgentWorkflowStepLog.step_order.asc())
        .all()
    )


def find_workflow_by_trigger(db: Session, phrase: str, user_id: int) -> AgentWorkflowMemory | None:
    workflows = list_workflow_memory(db, user_id=user_id, limit=200)
    ql = phrase.lower().strip()
    for w in workflows:
        if w.trigger_phrases_json:
            try:
                phrases = json.loads(w.trigger_phrases_json)
                if isinstance(phrases, list):
                    for p in phrases:
                        if isinstance(p, str) and ql in p.lower():
                            return w
            except (json.JSONDecodeError, TypeError):
                pass
        if w.workflow_name and ql in w.workflow_name.lower():
            return w
    return None


def update_workflow_memory_run(db: Session, memory_id: int, variables: dict | None = None, context: dict | None = None) -> AgentWorkflowMemory | None:
    memory = get_workflow_memory(db, memory_id)
    if not memory:
        return None
    if variables is not None:
        memory.variables_json = json.dumps(variables)
    if context is not None:
        memory.last_run_context_json = json.dumps(context)
    memory.run_count = (memory.run_count or 0) + 1
    memory.last_run_at = datetime.utcnow()
    db.commit()
    db.refresh(memory)
    return memory


def create_run(db: Session, user_id: int, plan_id: int, command_text: str, mode: str = "dry_run") -> AgentWorkflowRun | None:
    from datetime import date
    run = AgentWorkflowRun(
        workflow_memory_id=0,
        user_id=user_id,
        plan_id=plan_id,
        command_text=command_text,
        mode=mode,
        status="pending",
        run_date=date.today(),
        current_step_order=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_step_log(db: Session, step_log_id: int) -> AgentWorkflowStepLog | None:
    return db.query(AgentWorkflowStepLog).filter(AgentWorkflowStepLog.id == step_log_id).first()


def add_run_step_logs(db: Session, run_id: int, steps: list[dict]) -> list[AgentWorkflowStepLog]:
    logs = []
    for step in steps:
        log = AgentWorkflowStepLog(
            workflow_run_id=run_id,
            step_order=step.get("step_order", 1),
            step_type=step.get("step_type", step.get("tool", "unknown")),
            status="pending",
            action_preview_json=json.dumps({
                "target": step.get("target", ""),
                "instruction": step.get("instruction", ""),
                "tool": step.get("tool", step.get("step_type", "")),
                "expected_result": step.get("expected_result", ""),
                "parameters": step.get("parameters", {}),
                "risk_level": step.get("risk_level", "low"),
            }),
        )
        db.add(log)
        logs.append(log)
    db.commit()
    for log in logs:
        db.refresh(log)
    return logs


def get_pending_step_logs(db: Session, run_id: int) -> list[AgentWorkflowStepLog]:
    return (
        db.query(AgentWorkflowStepLog)
        .filter(AgentWorkflowStepLog.workflow_run_id == run_id, AgentWorkflowStepLog.status == "pending")
        .order_by(AgentWorkflowStepLog.step_order.asc())
        .all()
    )


def cancel_pending_step_logs(db: Session, run_id: int) -> None:
    logs = get_pending_step_logs(db, run_id)
    for log in logs:
        log.status = "cancelled"
    db.commit()


def update_step_log(db: Session, step_log_id: int, status: str, result_json: str | None = None, error_message: str | None = None) -> AgentWorkflowStepLog | None:
    log = db.query(AgentWorkflowStepLog).filter(AgentWorkflowStepLog.id == step_log_id).first()
    if not log:
        return None
    log.status = status
    if result_json is not None:
        log.result_json = result_json
    if error_message is not None:
        log.error_message = error_message
    db.commit()
    db.refresh(log)
    return log


def save_workflow_from_recorded_steps(
    db: Session,
    user_id: int,
    workflow_name: str,
    steps: list[dict],
) -> AgentWorkflowMemory | None:
    """Save a list of recorded steps as a new workflow memory entry."""
    import json
    from datetime import datetime

    memory = AgentWorkflowMemory(
        user_id=user_id,
        workflow_name=workflow_name,
        workflow_description="Recorded workflow from live recording session.",
        steps_json=json.dumps(steps),
        platform_hint="recorded",
        run_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory
