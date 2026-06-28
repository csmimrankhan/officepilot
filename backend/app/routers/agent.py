from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.agent_context import build_agent_context
from ..services.agent_swarm import SwarmManager, list_agent_profiles
from ..services.agent_memory import (
    add_run_step_logs,
    approve_plan,
    cancel_pending_step_logs,
    complete_plan,
    complete_run,
    create_run,
    find_recent_workflow,
    find_yesterday_workflows,
    get_plan,
    get_pending_step_logs,
    get_run,
    get_step_log,
    get_workflow_memory,
    list_plans,
    list_runs,
    list_step_logs,
    list_workflow_memory,
    repeat_workflow,
    save_plan,
    save_plan_as_workflow,
    update_step_log,
    update_workflow_memory_run,
)
from ..services.agent_tool_executor import execute_tool
from ..services.audit import log_action as record_audit
from ..services.safety import is_kill_switch_active
from ..services.accountant_agent import (
    get_agent_status,
)
from ..services.accountant_autopilot import build_accountant_plan
from ..services.multilingual_command import detect_language, normalize_command, translate_to_internal_english, generate_voice_reply, get_supported_languages
from ..services.voice_reply import build_user_reply

logger = logging.getLogger("officepilot.agent_router")

router = APIRouter(prefix="/api/agent", tags=["agent"])

# ── Agent Mode ──────────────────────────────────────────────────────────────

_agent_mode = {"mode": "plan"}  # plan | work | record | replay


@router.get("/mode")
def get_agent_mode(
    current_user: User = Depends(get_current_user),
):
    return _agent_mode


@router.post("/mode")
def set_agent_mode(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mode = body.get("mode", "plan")
    if mode not in ("plan", "work", "record", "replay"):
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}. Use plan, work, record, or replay.")
    _agent_mode["mode"] = mode

    record_audit(
        db=db,
        action="agent.set_mode",
        entity_type="agent_mode",
        entity_id=0,
        actor=current_user.email,
        details=f'{{"mode": "{mode}"}}',
    )

    return _agent_mode


# ── Current Task / Run ──────────────────────────────────────────────────────


@router.get("/current-task")
def get_current_task(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plans = list_plans(db, user_id=current_user.id, limit=5)
    active = [p for p in plans if p.status in ("pending", "approved")]
    if not active:
        return {"has_task": False, "task": None}

    latest = active[0]
    plan_data = {}
    if latest.plan_json:
        try:
            plan_data = json.loads(latest.plan_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "has_task": True,
        "task": {
            "plan_id": latest.id,
            "command_text": latest.command_text[:500],
            "risk_level": latest.risk_level,
            "status": latest.status,
            "task_type": plan_data.get("task_type", "general"),
            "created_at": latest.created_at.isoformat() if latest.created_at else None,
        },
    }


@router.get("/current-run")
def get_current_run(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    all_runs = list_runs(db, user_id=current_user.id, limit=20)
    active = [r for r in all_runs if r.status in ("pending", "approved", "running")]
    if not active:
        return {"has_run": False, "run": None}

    latest = active[0]
    step_logs = list_step_logs(db, latest.id)

    return {
        "has_run": True,
        "run": {
            "run_id": latest.id,
            "workflow_memory_id": latest.workflow_memory_id,
            "plan_id": latest.plan_id,
            "mode": latest.mode,
            "status": latest.status,
            "command_text": latest.command_text[:500] if latest.command_text else None,
            "current_step_order": latest.current_step_order,
            "error_message": latest.error_message,
            "started_at": latest.started_at.isoformat() if latest.started_at else None,
            "steps": [
                {
                    "id": s.id,
                    "step_order": s.step_order,
                    "step_type": s.step_type,
                    "status": s.status,
                }
                for s in step_logs
            ],
        },
    }


# ── Record Workflow ─────────────────────────────────────────────────────────

_recording_state = {"active": False, "recorded_steps": [], "started_at": None}


@router.post("/record/start")
def start_recording(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if _recording_state["active"]:
        return {"ok": True, "message": "Already recording.", **_recording_state}

    _recording_state["active"] = True
    _recording_state["recorded_steps"] = []
    _recording_state["started_at"] = datetime.utcnow().isoformat()

    record_audit(
        db=db,
        action="agent.record_start",
        entity_type="agent_recording",
        entity_id=0,
        actor=current_user.email,
        details='{"action": "start_recording"}',
    )

    return {"ok": True, "message": "Recording started.", **_recording_state}


@router.post("/record/stop")
def stop_recording(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _recording_state["active"]:
        return {"ok": False, "message": "No active recording.", "workflow_draft": None}

    workflow_name = body.get("workflow_name", "Recorded Workflow")
    steps = _recording_state.get("recorded_steps", [])

    from ..services.agent_memory import save_workflow_from_recorded_steps

    draft = save_workflow_from_recorded_steps(
        db, current_user.id, workflow_name, steps,
    )

    _recording_state["active"] = False
    _recording_state["recorded_steps"] = []
    _recording_state["started_at"] = None

    record_audit(
        db=db,
        action="agent.record_stop",
        entity_type="agent_workflow_memory",
        entity_id=draft.id if draft else 0,
        actor=current_user.email,
        details=f'{{"workflow_name": "{workflow_name}", "step_count": {len(steps)}}}',
    )

    return {
        "ok": True,
        "message": "Recording stopped. Workflow draft created.",
        "workflow_draft": {
            "id": draft.id if draft else None,
            "workflow_name": draft.workflow_name if draft else workflow_name,
            "step_count": len(steps),
        } if draft else None,
    }


# ── Replay Yesterday ────────────────────────────────────────────────────────


@router.post("/replay/yesterday")
def replay_yesterday(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mode = body.get("mode", "dry_run")

    if is_kill_switch_active():
        raise HTTPException(status_code=403, detail="Kill switch is active. Cannot replay.")

    yesterday_workflows = find_yesterday_workflows(db, current_user.id)

    if not yesterday_workflows:
        return {
            "found": False,
            "message": "I couldn't find a workflow from yesterday. Do you want to record one now?",
            "workflows": [],
        }

    if len(yesterday_workflows) == 1:
        w = yesterday_workflows[0]
        run = repeat_workflow(db, w.id, current_user.id, command_text=f"Repeat: {w.workflow_name}", mode=mode)

        record_audit(
            db=db,
            action="agent.replay_yesterday",
            entity_type="agent_workflow_memory",
            entity_id=w.id,
            actor=current_user.email,
            details=f'{{"workflow_name": "{w.workflow_name}", "mode": "{mode}", "run_id": {run.id if run else "null"}}}',
        )

        steps = list_step_logs(db, run.id) if run else []

        return {
            "found": True,
            "single_match": True,
            "run_id": run.id if run else None,
            "workflow_id": w.id,
            "workflow_name": w.workflow_name,
            "mode": mode,
            "steps": [
                {
                    "step_order": s.step_order,
                    "step_type": s.step_type,
                    "status": s.status,
                    "action_preview": json.loads(s.action_preview_json) if s.action_preview_json else None,
                }
                for s in steps
            ],
        }

    workflows_data = [
        {
            "id": w.id,
            "workflow_name": w.workflow_name,
            "platform_hint": w.platform_hint,
            "last_run_at": w.last_run_at.isoformat() if w.last_run_at else w.created_at.isoformat(),
            "run_count": w.run_count or 0,
        }
        for w in yesterday_workflows
    ]

    return {
        "found": True,
        "single_match": False,
        "message": "I found multiple workflows from yesterday. Please choose one.",
        "workflows": workflows_data,
    }


# ── Emergency Stop ──────────────────────────────────────────────────────────


@router.post("/emergency-stop")
def emergency_stop(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    all_runs = list_runs(db, user_id=current_user.id, limit=50)
    active_runs = [r for r in all_runs if r.status in ("pending", "approved", "running")]

    if not active_runs:
        return {"ok": True, "message": "No active runs to stop.", "stopped_count": 0}

    stopped_count = 0
    for run in active_runs:
        cancel_pending_step_logs(db, run.id)
        run.status = "stopped"
        run.stopped_at = datetime.utcnow()
        run.stopped_by = current_user.email
        run.error_message = body.get("reason", "Emergency stop")
        stopped_count += 1

    db.commit()

    record_audit(
        db=db,
        action="agent.emergency_stop",
        entity_type="agent_workflow_run",
        entity_id=0,
        actor=current_user.email,
        details=f'{{"stopped_count": {stopped_count}}}',
    )

    return {"ok": True, "message": f"Emergency stop executed. {stopped_count} run(s) stopped.", "stopped_count": stopped_count}


@router.get("/status")
def agent_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_agent_status()


@router.get("/llm-status")
def llm_status():
    import os
    import urllib.request
    import urllib.error

    from ..config import get_settings
    settings = get_settings()
    base_url = os.environ.get("OLLAMA_BASE_URL", settings.ollama_base_url)
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            return {"status": "connected", "models": models, "base_url": base_url}
    except Exception as e:
        return {"status": "offline", "error": str(e), "base_url": base_url}


@router.post("/context")
def agent_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = build_agent_context(db, current_user)
    return {"context": ctx}


@router.post("/plan-task")
def plan_task(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    command = body.get("command", "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="Command is required.")

    if is_kill_switch_active():
        raise HTTPException(status_code=403, detail="Kill switch is active. Agent execution blocked.")

    force_new_plan = body.get("force_new_plan", False)
    plan = build_accountant_plan(db, command, current_user, force_new_plan=force_new_plan)

    swarm = SwarmManager(db, current_user)
    assigned_agent = swarm.classify_and_route(command)
    plan["assigned_agent"] = assigned_agent

    # Navigation response — return early without creating plan/audit
    if plan.get("type") == "navigation":
        return {
            "type": "navigation",
            "target": plan.get("target"),
            "route": plan.get("route"),
            "message": plan.get("message", ""),
            "plan_id": None,
            "plan": plan,
            "original_command": command,
            "detected_language": plan.get("language"),
            "task_type": "navigation",
            "risk_level": "low",
            "requires_approval": False,
            "clarification_needed": False,
            "clarification_question": None,
            "blocked_reason": None,
            "suggested_next_actions": [],
            "can_save_workflow": False,
        }

    # Skill match response — return early with different shape
    if plan.get("type") == "skill_match":
        matched_skill = plan.get("matched_skill", {})
        return {
            "type": "skill_match",
            "matched_skill": matched_skill,
            "original_command": command,
            "voice_reply_text": plan.get("voice_reply", ""),
            "suggested_next_actions": plan.get("suggested_actions", [
                "dry_run_skill", "create_new_plan", "edit_skill", "cancel",
            ]),
            "risk_level": matched_skill.get("safety_rules", {}).get("max_risk_level", "low"),
            "requires_approval": matched_skill.get("approval_required", True),
        }

    lang = plan.get("language", detect_language(command))
    normalized = normalize_command(command)
    internal_english = translate_to_internal_english(command)

    if plan.get("blocked_reason"):
        voice_reply_text = generate_voice_reply("task_blocked", lang)
    elif plan.get("clarification_needed"):
        voice_reply_text = generate_voice_reply("clarification_needed", lang)
    elif plan.get("task_type") == "workflow_replay":
        voice_reply_text = build_user_reply("workflow_repeated", lang, name=plan.get("workflow_name", "unknown"))
    else:
        voice_reply_text = build_user_reply("plan_preview", lang, summary=plan.get("summary_for_user", plan.get("task_summary", "")), risk=plan.get("risk_level", "low"))

    suggested_next_actions = []
    if plan.get("clarification_needed"):
        suggested_next_actions = ["Read this screen", "Download today's invoices", "Show workflow memory"]
    elif plan.get("blocked_reason"):
        suggested_next_actions = []
    elif plan.get("risk_level") in ("low", "medium", "high"):
        suggested_next_actions = ["Approve and execute", "Save as workflow", "Modify plan"]
    if plan.get("can_save_workflow") and "Save as workflow" not in suggested_next_actions:
        suggested_next_actions.append("Save as workflow")

    plan_id = None
    if plan.get("risk_level") != "blocked":
        context = build_agent_context(db, current_user)
        saved = save_plan(
            db=db,
            user_id=current_user.id,
            command_text=command,
            context_summary=json.dumps(context, default=str)[:2000],
            plan_json=json.dumps(plan),
            risk_level=plan.get("risk_level", "low"),
        )
        plan_id = saved.id

        record_audit(
            db=db,
            action="agent.plan_task",
            entity_type="agent_task_plan",
            entity_id=saved.id,
            actor=current_user.email,
            details=json.dumps({
                "command": command[:200],
                "risk_level": plan.get("risk_level"),
                "blocked": plan.get("risk_level") == "blocked",
                "language": lang,
                "task_type": plan.get("task_type"),
            }),
        )

    summary_for_user = plan.get("summary_for_user") or plan.get("task_summary", "Task plan ready.")

    return {
        "plan_id": plan_id,
        "plan": plan,
        "original_command": command,
        "detected_language": lang,
        "normalized_command": normalized,
        "internal_english_command": internal_english,
        "summary_for_user": summary_for_user,
        "voice_reply_text": voice_reply_text,
        "task_type": plan.get("task_type", "general"),
        "risk_level": plan.get("risk_level", "low"),
        "requires_approval": plan.get("requires_approval", True),
        "clarification_needed": plan.get("clarification_needed", False),
        "clarification_question": plan.get("clarification_question"),
        "blocked_reason": plan.get("blocked_reason"),
        "suggested_next_actions": suggested_next_actions,
        "can_save_workflow": plan.get("can_save_workflow", False),
        "matched_workflow_id": plan.get("workflow_memory_id"),
        "matched_workflow_name": plan.get("workflow_name"),
        "assigned_agent": plan.get("assigned_agent", "general"),
    }


@router.post("/match-skill")
def match_skill_endpoint(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    command = body.get("command", "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="Command is required.")

    from ..services.accounting_skills import find_skill_for_command
    match = find_skill_for_command(db, command, current_user.id)
    if not match:
        return {"matched": False, "matches": []}

    return {
        "matched": True,
        "match_type": match.get("match_type", "possible"),
        "matches": [match],
    }


# ── Phase 23D: Controlled Plan Execution ─────────────────────────────────────


@router.post("/plans/{plan_id}/approve")
def approve_plan_with_run(
    plan_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if is_kill_switch_active():
        raise HTTPException(status_code=403, detail="Kill switch is active. Cannot approve plans.")

    plan = get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")

    if plan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only approve your own plans.")

    if plan.risk_level == "blocked":
        raise HTTPException(status_code=400, detail="Cannot approve a blocked plan.")

    mode = body.get("mode", "dry_run")

    approved = approve_plan(db, plan_id)
    if not approved:
        raise HTTPException(status_code=500, detail="Failed to approve plan.")

    plan_data = {}
    if plan.plan_json:
        try:
            plan_data = json.loads(plan.plan_json)
        except (json.JSONDecodeError, TypeError):
            pass
    steps = plan_data.get("steps", [])

    run = create_run(db, current_user.id, plan_id, plan.command_text or "", mode=mode)
    if not run:
        raise HTTPException(status_code=500, detail="Failed to create workflow run.")

    run.status = "approved"
    run.approved_at = datetime.utcnow()
    run.current_step_order = 0
    db.commit()

    step_logs = add_run_step_logs(db, run.id, steps)

    record_audit(
        db=db,
        action="agent.plan_approve",
        entity_type="agent_task_plan",
        entity_id=plan_id,
        actor=current_user.email,
        details=json.dumps({"command": plan.command_text[:200], "mode": mode, "run_id": run.id}),
    )

    # Phase 39: Background execution — auto-create BackgroundTask
    background_task_id = None
    if plan_data.get("run_in_background"):
        from ..models.background_task import BackgroundTask
        from ..services.background_runner import BackgroundTaskRunner

        bt = BackgroundTask(
            user_id=current_user.id,
            command=plan.command_text or "",
            plan_json=json.dumps({"steps": steps}),
            status="queued",
        )
        db.add(bt)
        db.commit()
        db.refresh(bt)
        background_task_id = bt.id
        runner = BackgroundTaskRunner.get_instance()
        runner.start_task(bt.id)

    result = {
        "ok": True,
        "plan_id": plan_id,
        "run_id": run.id,
        "mode": mode,
        "status": "approved",
        "steps": [
            {
                "step_log_id": sl.id,
                "step_order": sl.step_order,
                "step_type": sl.step_type,
                "status": sl.status,
                "action_preview": json.loads(sl.action_preview_json) if sl.action_preview_json else None,
            }
            for sl in step_logs
        ],
    }
    if background_task_id is not None:
        result["background_task_id"] = background_task_id

    return result


@router.post("/runs/{run_id}/execute-step")
def execute_run_step(
    run_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    step_log_id = body.get("step_log_id")

    if is_kill_switch_active():
        raise HTTPException(status_code=403, detail="Kill switch is active. Cannot execute steps.")

    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only execute your own runs.")

    if run.status in ("stopped", "cancelled", "completed", "failed"):
        raise HTTPException(status_code=400, detail=f"Run is '{run.status}'. Cannot execute steps.")

    if run.mode not in ("dry_run", "live"):
        raise HTTPException(status_code=400, detail=f"Unknown mode: {run.mode}")

    if step_log_id:
        step_log = get_step_log(db, step_log_id)
        if not step_log or step_log.workflow_run_id != run_id:
            raise HTTPException(status_code=404, detail="Step log not found for this run.")
    else:
        pending = get_pending_step_logs(db, run_id)
        if not pending:
            raise HTTPException(status_code=400, detail="No pending steps to execute.")
        step_log = pending[0]

    if step_log.status != "pending":
        raise HTTPException(status_code=400, detail=f"Step is already '{step_log.status}'.")

    preview = {}
    if step_log.action_preview_json:
        try:
            preview = json.loads(step_log.action_preview_json)
        except (json.JSONDecodeError, TypeError):
            pass

    tool_name = preview.get("tool", step_log.step_type)
    params = dict(preview.get("parameters", {}))

    user_params = {}
    for p in ("file_path", "path", "sheet_name", "group_by_column", "value_column", "amount_column", "user_confirmed", "manual_login_complete", "guided_export_complete", "output_folder", "download_folder"):
        if p in body:
            user_params[p] = body[p]
    params.update(user_params)

    # Resolve template variable references in param values
    # e.g. {"path": "{file_path}"} with user_params["file_path"]="C:\\file.xlsx"
    # becomes {"path": "C:\\file.xlsx", "file_path": "C:\\file.xlsx"}
    # If the variable is not provided by the user, it resolves to empty string
    # so auto-detection can take over downstream.
    for key in list(params.keys()):
        val = params[key]
        if isinstance(val, str) and val.startswith("{") and val.endswith("}"):
            var_name = val[1:-1]
            if var_name in user_params:
                params[key] = user_params[var_name]
            else:
                # Look up from completed step outputs (e.g. selected_file_path from file_find_in_downloads)
                resolved = None
                for sl in list_step_logs(db, run_id):
                    if sl.status == "completed" and sl.result_json:
                        try:
                            step_out = json.loads(sl.result_json)
                            if isinstance(step_out, dict) and var_name in step_out:
                                resolved = step_out[var_name]
                                break
                        except (json.JSONDecodeError, TypeError):
                            pass
                params[key] = resolved if resolved is not None else ""

    result = execute_tool(tool_name, params, run.mode, db, current_user)

    status_map = {
        "success": "completed",
        "failed": "failed",
        "blocked": "blocked",
        "needs_approval": "pending",
        "dry_run": "completed",
    }
    new_status = status_map.get(result["status"], "failed")

    update_step_log(
        db, step_log.id,
        status=new_status,
        result_json=json.dumps(result.get("output", {})),
        error_message=result.get("error_message"),
    )

    run.current_step_order = step_log.step_order
    if new_status == "failed":
        run.error_message = result.get("error_message", "Step failed")
    db.commit()

    record_audit(
        db=db,
        action="agent.execute_step",
        entity_type="agent_workflow_run",
        entity_id=run_id,
        actor=current_user.email,
        details=json.dumps({
            "step_log_id": step_log.id,
            "step_order": step_log.step_order,
            "tool": tool_name,
            "status": new_status,
            "mode": run.mode,
        }),
    )

    pending_steps = get_pending_step_logs(db, run_id)
    next_step = pending_steps[0] if pending_steps else None

    return {
        "ok": new_status == "completed",
        "step_log_id": step_log.id,
        "step_order": step_log.step_order,
        "tool": tool_name,
        "step_status": new_status,
        "result": result,
        "next_step": {
            "step_log_id": next_step.id,
            "step_order": next_step.step_order,
            "step_type": next_step.step_type,
            "action_preview": json.loads(next_step.action_preview_json) if next_step.action_preview_json else None,
        } if next_step else None,
    }


@router.post("/runs/{run_id}/dry-run")
def dry_run_all_steps(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if is_kill_switch_active():
        raise HTTPException(status_code=403, detail="Kill switch is active.")

    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only dry-run your own runs.")

    pending = get_pending_step_logs(db, run_id)
    if not pending:
        raise HTTPException(status_code=400, detail="No pending steps to dry-run.")

    results = []
    for step_log in pending:
        preview = {}
        if step_log.action_preview_json:
            try:
                preview = json.loads(step_log.action_preview_json)
            except (json.JSONDecodeError, TypeError):
                pass
        tool_name = preview.get("tool", step_log.step_type)
        params = preview.get("parameters", {})

        result = execute_tool(tool_name, params, "dry_run", db, current_user)

        update_step_log(
            db, step_log.id,
            status="completed",
            result_json=json.dumps(result.get("output", {})),
        )

        results.append({
            "step_log_id": step_log.id,
            "step_order": step_log.step_order,
            "tool": tool_name,
            "result": result,
        })

    run.status = "completed"
    run.completed_at = datetime.utcnow()
    run.dry_run_result_json = json.dumps(results)
    db.commit()

    record_audit(
        db=db,
        action="agent.dry_run",
        entity_type="agent_workflow_run",
        entity_id=run_id,
        actor=current_user.email,
        details=json.dumps({"step_count": len(results)}),
    )

    return {
        "ok": True,
        "run_id": run_id,
        "mode": "dry_run",
        "step_count": len(results),
        "results": results,
    }


@router.post("/runs/{run_id}/start-live")
def start_live_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if is_kill_switch_active():
        raise HTTPException(status_code=403, detail="Kill switch is active.")

    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only start your own runs.")

    if run.status not in ("approved", "pending"):
        raise HTTPException(status_code=400, detail=f"Run is '{run.status}'. Must be 'approved' or 'pending'.")

    run.mode = "live"
    run.status = "running"
    db.commit()

    record_audit(
        db=db,
        action="agent.start_live",
        entity_type="agent_workflow_run",
        entity_id=run_id,
        actor=current_user.email,
        details=json.dumps({"mode": "live"}),
    )

    return {
        "ok": True,
        "run_id": run_id,
        "mode": "live",
        "status": "running",
    }


@router.post("/runs/{run_id}/stop")
def stop_run(
    run_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only stop your own runs.")

    if run.status in ("stopped", "cancelled", "completed"):
        raise HTTPException(status_code=400, detail=f"Run is already '{run.status}'.")

    reason = body.get("reason", "User requested stop")

    cancel_pending_step_logs(db, run_id)
    run.status = "stopped"
    run.stopped_at = datetime.utcnow()
    run.stopped_by = current_user.email
    run.error_message = reason
    db.commit()

    record_audit(
        db=db,
        action="agent.stop_run",
        entity_type="agent_workflow_run",
        entity_id=run_id,
        actor=current_user.email,
        details=json.dumps({"reason": reason, "stopped_by": current_user.email}),
    )

    return {
        "ok": True,
        "run_id": run_id,
        "status": "stopped",
        "message": "Run stopped. Pending steps cancelled.",
    }


@router.get("/plans")
def list_agent_plans(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plans = list_plans(db, user_id=current_user.id, limit=limit)
    return {
        "plans": [
            {
                "id": p.id,
                "command_text": p.command_text[:200],
                "risk_level": p.risk_level,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "approved_at": p.approved_at.isoformat() if p.approved_at else None,
            }
            for p in plans
        ]
    }


@router.post("/workflows/save")
def save_workflow(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan_id = body.get("plan_id")
    workflow_name = body.get("workflow_name", "").strip()
    workflow_description = body.get("workflow_description", "").strip() or None
    trigger_phrases = body.get("trigger_phrases")

    if not plan_id:
        raise HTTPException(status_code=400, detail="plan_id is required.")
    if not workflow_name:
        raise HTTPException(status_code=400, detail="workflow_name is required.")

    plan = get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    if plan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only save your own plans.")

    memory = save_plan_as_workflow(
        db, current_user.id, plan_id, workflow_name, workflow_description,
        trigger_phrases=trigger_phrases,
    )
    if not memory:
        raise HTTPException(status_code=500, detail="Failed to save workflow.")

    record_audit(
        db=db,
        action="agent.save_workflow",
        entity_type="agent_workflow_memory",
        entity_id=memory.id,
        actor=current_user.email,
        details=json.dumps({"workflow_name": workflow_name, "plan_id": plan_id}),
    )

    stored_phrases = []
    if memory.trigger_phrases_json:
        try:
            stored_phrases = json.loads(memory.trigger_phrases_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "ok": True,
        "workflow_id": memory.id,
        "workflow_name": memory.workflow_name,
        "trigger_phrases": stored_phrases,
    }


@router.get("/workflows")
def list_workflows(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workflows = list_workflow_memory(db, user_id=current_user.id, limit=limit)
    return {
        "workflows": [
            {
                "id": w.id,
                "workflow_name": w.workflow_name,
                "workflow_description": w.workflow_description,
                "platform_hint": w.platform_hint,
                "run_count": w.run_count or 0,
                "last_run_at": w.last_run_at.isoformat() if w.last_run_at else None,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in workflows
        ]
    }


@router.post("/workflows/{workflow_id}/repeat")
def repeat_workflow_endpoint(
    workflow_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mode = body.get("mode", "dry_run")

    if is_kill_switch_active():
        raise HTTPException(status_code=403, detail="Kill switch is active. Cannot repeat workflows.")

    memory = get_workflow_memory(db, workflow_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    if memory.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only repeat your own workflows.")

    run = repeat_workflow(db, workflow_id, current_user.id, command_text=f"Repeat workflow: {memory.workflow_name}", mode=mode)
    if not run:
        raise HTTPException(status_code=500, detail="Failed to start workflow run.")

    record_audit(
        db=db,
        action="agent.repeat_workflow",
        entity_type="agent_workflow_memory",
        entity_id=workflow_id,
        actor=current_user.email,
        details=json.dumps({"workflow_name": memory.workflow_name, "mode": mode, "run_id": run.id}),
    )

    steps = list_step_logs(db, run.id)

    return {
        "ok": True,
        "run_id": run.id,
        "mode": mode,
        "workflow_name": memory.workflow_name,
        "steps": [
            {
                "step_order": s.step_order,
                "step_type": s.step_type,
                "status": s.status,
                "action_preview": json.loads(s.action_preview_json) if s.action_preview_json else None,
            }
            for s in steps
        ],
    }


@router.post("/workflows/repeat-recent")
def repeat_recent_workflow(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mode = body.get("mode", "dry_run")

    if is_kill_switch_active():
        raise HTTPException(status_code=403, detail="Kill switch is active.")

    yesterday_workflows = find_yesterday_workflows(db, current_user.id)

    if not yesterday_workflows:
        return {
            "found": False,
            "message": "I couldn't find a workflow from yesterday. Do you want to record one now?",
            "workflows": [],
        }

    workflows_data = [
        {
            "id": w.id,
            "workflow_name": w.workflow_name,
            "platform_hint": w.platform_hint,
            "last_run_at": w.last_run_at.isoformat() if w.last_run_at else w.created_at.isoformat(),
            "run_count": w.run_count or 0,
        }
        for w in yesterday_workflows
    ]

    if len(yesterday_workflows) == 1:
        w = yesterday_workflows[0]
        run = repeat_workflow(db, w.id, current_user.id, command_text=f"Repeat: {w.workflow_name}", mode=mode)
        if not run:
            raise HTTPException(status_code=500, detail="Failed to start workflow run.")

        record_audit(
            db=db,
            action="agent.repeat_recent",
            entity_type="agent_workflow_memory",
            entity_id=w.id,
            actor=current_user.email,
            details=json.dumps({"workflow_name": w.workflow_name, "mode": mode, "run_id": run.id}),
        )

        steps = list_step_logs(db, run.id)

        return {
            "found": True,
            "single_match": True,
            "run_id": run.id,
            "workflow_id": w.id,
            "workflow_name": w.workflow_name,
            "mode": mode,
            "steps": [
                {
                    "step_order": s.step_order,
                    "step_type": s.step_type,
                    "status": s.status,
                    "action_preview": json.loads(s.action_preview_json) if s.action_preview_json else None,
                }
                for s in steps
            ],
        }

    return {
        "found": True,
        "single_match": False,
        "message": "I found multiple workflows from yesterday. Please choose one.",
        "workflows": workflows_data,
    }


@router.get("/workflows/{workflow_id}/runs")
def list_workflow_runs(
    workflow_id: int,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    runs = list_runs(db, workflow_memory_id=workflow_id, user_id=current_user.id, limit=limit)
    return {
        "runs": [
            {
                "id": r.id,
                "mode": r.mode,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "error_message": r.error_message,
            }
            for r in runs
        ]
    }


@router.get("/runs/{run_id}/steps")
def get_run_steps(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    steps = list_step_logs(db, run_id)
    return {
        "steps": [
            {
                "id": s.id,
                "step_order": s.step_order,
                "step_type": s.step_type,
                "status": s.status,
                "action_preview": json.loads(s.action_preview_json) if s.action_preview_json else None,
                "result": json.loads(s.result_json) if s.result_json else None,
                "error_message": s.error_message,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in steps
        ]
    }


@router.get("/runs/{run_id}/summary")
def get_run_summary(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    steps = list_step_logs(db, run_id)
    completed_steps = [s for s in steps if s.status == "completed"]
    invoice_count = 0
    total_amount = 0.0
    excel_file_path = None
    pnl_summary_en = None
    pnl_summary_ru = None
    pnl_comparison_data = None

    for s in completed_steps:
        preview = {}
        result_data = {}
        if s.action_preview_json:
            try:
                preview = json.loads(s.action_preview_json)
            except Exception:
                pass
        if s.result_json:
            try:
                result_data = json.loads(s.result_json)
            except Exception:
                pass
        tool = preview.get("tool", s.step_type)
        if tool == "extract_invoice_data":
            rows = result_data.get("rows", result_data.get("parsed", []))
            if isinstance(rows, list):
                invoice_count = len(rows)
        if tool == "calculate_excel_total":
            total_amount = result_data.get("total", result_data.get("output", {}).get("total", 0))
            if isinstance(total_amount, (int, float)):
                total_amount = float(total_amount)
            else:
                total_amount = 0.0
        if tool in ("create_excel_workbook", "create_pnl_comparison_excel"):
            excel_file_path = result_data.get("filepath", result_data.get("output", {}).get("filepath"))
        if tool == "compare_pnl_reports":
            output = result_data.get("output", result_data)
            pnl_summary_en = output.get("summary_english") or result_data.get("summary_english")
            pnl_summary_ru = output.get("summary_roman_urdu") or result_data.get("summary_roman_urdu")
            pnl_comparison_data = {
                "current_net_income": output.get("comparison", output).get("current", {}).get("net_income") or output.get("current", {}).get("net_income"),
                "previous_net_income": output.get("comparison", output).get("previous", {}).get("net_income") or output.get("previous", {}).get("net_income"),
                "net_income_difference": output.get("comparison", {}).get("net_income_difference"),
                "net_income_percentage_change": output.get("comparison", {}).get("net_income_percentage_change"),
            }

    if pnl_summary_en:
        summary_en = pnl_summary_en
        summary_ru = pnl_summary_ru or pnl_summary_en
    elif invoice_count > 0:
        summary_ru = f"Maine aaj ki {invoice_count} invoices process ki hain. Total {total_amount:.2f} hai."
        if excel_file_path:
            summary_ru += f" Excel file yahan save ho gayi hai: {excel_file_path}."
        summary_en = f"I processed {invoice_count} invoices for today. Total is {total_amount:.2f}."
        if excel_file_path:
            summary_en += f" Excel file saved: {excel_file_path}."
    else:
        task_types = list(set(s.step_type for s in completed_steps))
        summary_en = f"Completed {len(completed_steps)} step(s): {', '.join(task_types[:5])}."
        summary_ru = f"{len(completed_steps)} step(s) mukammal hue hain."

    return {
        "run_id": run_id,
        "status": run.status,
        "mode": run.mode,
        "steps_completed": len(completed_steps),
        "steps_total": len(steps),
        "invoice_count": invoice_count,
        "total_amount": total_amount,
        "excel_file_path": excel_file_path,
        "summary_roman_urdu": summary_ru,
        "summary_english": summary_en,
        "pnl_comparison": pnl_comparison_data,
        "run": {
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "stopped_at": run.stopped_at.isoformat() if run.stopped_at else None,
        },
    }


@router.post("/runs/{run_id}/verify-excel")
def verify_run_excel(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    steps = list_step_logs(db, run_id)
    excel_path = None
    expected_total = 0.0
    rows_written = 0

    for s in steps:
        if s.status != "completed":
            continue
        preview = {}
        result_data = {}
        if s.action_preview_json:
            try:
                preview = json.loads(s.action_preview_json)
            except Exception:
                pass
        if s.result_json:
            try:
                result_data = json.loads(s.result_json)
            except Exception:
                pass
        tool = preview.get("tool", s.step_type)
        if tool == "create_excel_workbook":
            excel_path = result_data.get("filepath") or (result_data.get("output") or {}).get("filepath")
            rows_written = result_data.get("rows") or (result_data.get("output") or {}).get("rows", 0)
        if tool == "calculate_excel_total":
            expected_total = result_data.get("total") or (result_data.get("output") or {}).get("total", 0)

    import os
    from pathlib import Path

    file_exists = excel_path is not None and Path(excel_path).exists() if excel_path else False
    file_size = os.path.getsize(excel_path) if file_exists else 0

    return {
        "ok": file_exists,
        "excel_file_path": excel_path,
        "file_exists": file_exists,
        "file_size": file_size,
        "rows_written": rows_written,
        "expected_total": expected_total,
        "verification": "verified" if file_exists else "not_found",
    }


# ── Phase 23F: P&L Report Comparison Endpoints ──────────────────────────────


@router.post("/reports/pnl/compare-demo")
def pnl_compare_demo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.accounting_report_comparison import (
        get_demo_current_report,
        get_demo_previous_report,
        compare_pnl_reports,
        create_pnl_comparison_excel,
        build_pnl_summary_text,
        pnl_comparison_to_dict,
    )
    from ..services.agent_tool_executor import _data_dir

    current = get_demo_current_report()
    previous = get_demo_previous_report()
    comparison = compare_pnl_reports(current, previous)

    output_dir = _data_dir() / "exports" / "pnl"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"pnl_comparison_demo_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    excel_path = create_pnl_comparison_excel(current, previous, comparison, output_path)

    result = pnl_comparison_to_dict(comparison)
    result["excel_file_path"] = excel_path
    result["summary_english"] = build_pnl_summary_text(comparison, "en")
    result["summary_roman_urdu"] = build_pnl_summary_text(comparison, "roman_urdu")

    record_audit(
        db=db,
        action="agent.pnl_compare_demo",
        entity_type="pnl_comparison",
        entity_id=0,
        actor=current_user.email,
        details=json.dumps({
            "current_net_income": current.net_income,
            "previous_net_income": previous.net_income,
            "difference": comparison.net_income_difference,
        }),
    )

    return {"ok": True, "result": result}


@router.post("/reports/pnl/compare-uploaded")
def pnl_compare_uploaded(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_json = body.get("current_month_file")
    previous_json = body.get("previous_month_file")

    if not current_json or not previous_json:
        raise HTTPException(status_code=400, detail="Both current_month_file and previous_month_file are required.")

    from ..services.accounting_report_comparison import (
        PnLReport, PnLRow, compare_pnl_reports,
        create_pnl_comparison_excel, build_pnl_summary_text,
        pnl_comparison_to_dict,
    )
    from ..services.agent_tool_executor import _data_dir

    def _parse_json(data):
        if isinstance(data, str):
            import json as _json
            data = _json.loads(data)
        rows_data = data.get("rows", data.get("data", []))
        rows = []
        for r in rows_data:
            rows.append(PnLRow(
                account=r.get("account", r.get("name", "")),
                amount=float(r.get("amount", 0)),
                type=r.get("type", "expense"),
            ))
        return PnLReport(
            rows=rows,
            total_income=float(data.get("total_income", sum(r.amount for r in rows if r.type == "income"))),
            total_expenses=float(data.get("total_expenses", sum(r.amount for r in rows if r.type == "expense"))),
            net_income=float(data.get("net_income", 0)),
            period_label=data.get("period_label", data.get("period", "")),
        )

    current = _parse_json(current_json)
    previous = _parse_json(previous_json)
    comparison = compare_pnl_reports(current, previous)

    output_dir = _data_dir() / "exports" / "pnl"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"pnl_comparison_upload_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    excel_path = create_pnl_comparison_excel(current, previous, comparison, output_path)

    result = pnl_comparison_to_dict(comparison)
    result["excel_file_path"] = excel_path
    result["summary_english"] = build_pnl_summary_text(comparison, "en")
    result["summary_roman_urdu"] = build_pnl_summary_text(comparison, "roman_urdu")

    record_audit(
        db=db,
        action="agent.pnl_compare_uploaded",
        entity_type="pnl_comparison",
        entity_id=0,
        actor=current_user.email,
        details=json.dumps({
            "current_rows": len(current.rows),
            "previous_rows": len(previous.rows),
            "difference": comparison.net_income_difference,
        }),
    )

    return {"ok": True, "result": result}


@router.get("/reports/pnl/runs")
def list_pnl_runs(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plans = list_plans(db, user_id=current_user.id, limit=limit)
    pnl_plans = [p for p in plans if p.plan_json and '"task_type": "accounting_report_comparison"' in p.plan_json]
    return {
        "runs": [
            {
                "id": p.id,
                "command_text": p.command_text[:200],
                "risk_level": p.risk_level,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in pnl_plans
        ]
    }


@router.get("/reports/pnl/runs/{plan_id}")
def get_pnl_run(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.agent_memory import get_plan
    plan = get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    if plan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return {
        "id": plan.id,
        "command_text": plan.command_text[:200],
        "risk_level": plan.risk_level,
        "status": plan.status,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "plan_json": json.loads(plan.plan_json) if plan.plan_json else None,
    }


# ── Phase 25: Local Folder Invoice Workflow Endpoints ────────────────────────


@router.post("/folder-invoice/scan")
def folder_invoice_scan(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folder_path = body.get("folder_path", "")
    date_filter = body.get("date_filter", "today")
    from ..services.local_invoice_workflow import scan_folder_for_invoices

    files = scan_folder_for_invoices(folder_path, date_filter=date_filter)
    file_list = [
        {"path": f.path, "filename": f.filename, "modified": f.modified, "size": f.size}
        for f in files
    ]

    record_audit(
        db=db,
        action="agent.folder_invoice_scan",
        entity_type="folder_invoice",
        entity_id=0,
        actor=current_user.email,
        details=json.dumps({"folder": folder_path, "files_found": len(file_list)}),
    )

    return {"ok": True, "files": file_list, "count": len(file_list)}


@router.post("/folder-invoice/create-excel")
def folder_invoice_create_excel(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.local_invoice_workflow import ExtractedInvoice, create_daily_invoices_excel, build_folder_invoice_summary_text
    from ..services.agent_tool_executor import _data_dir

    invoices_data = body.get("invoices", body.get("rows", []))
    output_dir = _data_dir() / "exports" / "invoices"
    output_dir.mkdir(parents=True, exist_ok=True)

    invoices = []
    for d in invoices_data:
        invoices.append(ExtractedInvoice(
            vendor=d.get("vendor", d.get("vendor_name", "")),
            invoice_number=d.get("invoice_no", d.get("invoice_number", "")),
            invoice_date=d.get("date", d.get("invoice_date", "")),
            total_amount=float(d.get("amount", d.get("total_amount", 0))),
            tax=float(d.get("tax", 0)),
            currency=d.get("currency", "USD"),
            source_file=d.get("source_file", d.get("filepath", "")),
            confidence=float(d.get("confidence", 1.0)),
            warnings=d.get("warnings", []),
            status=d.get("status", "imported"),
        ))

    filepath = create_daily_invoices_excel(invoices, str(output_dir))
    total = sum(inv.total_amount for inv in invoices)
    success_count = sum(1 for inv in invoices if inv.confidence >= 0.4 and inv.total_amount > 0)

    record_audit(
        db=db,
        action="agent.folder_invoice_create_excel",
        entity_type="folder_invoice",
        entity_id=0,
        actor=current_user.email,
        details=json.dumps({"filepath": filepath, "invoice_count": len(invoices), "total": total}),
    )

    return {
        "ok": True,
        "filepath": filepath,
        "invoice_count": len(invoices),
        "success_count": success_count,
        "total_amount": total,
        "summary_english": build_folder_invoice_summary_text(len(invoices), success_count, total, filepath, "en"),
        "summary_roman_urdu": build_folder_invoice_summary_text(len(invoices), success_count, total, filepath, "roman_urdu"),
    }


@router.get("/folder-invoice/runs")
def list_folder_invoice_runs(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plans = list_plans(db, user_id=current_user.id, limit=limit)
    folder_plans = [p for p in plans if p.plan_json and '"task_type": "local_folder_invoice_workflow"' in p.plan_json]
    return {
        "runs": [
            {
                "id": p.id,
                "command_text": p.command_text[:200],
                "risk_level": p.risk_level,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in folder_plans
        ]
    }


@router.get("/folder-invoice/runs/{plan_id}")
def get_folder_invoice_run(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = get_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    if plan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return {
        "id": plan.id,
        "command_text": plan.command_text[:200],
        "risk_level": plan.risk_level,
        "status": plan.status,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "plan_json": json.loads(plan.plan_json) if plan.plan_json else None,
    }


@router.post("/bank/parse")
def bank_parse_feed(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.bank_reconciliation import BankFeedAdapter

    content = body.get("content", "")
    filename = body.get("filename", "feed.csv")
    transactions = BankFeedAdapter().parse_feed_text(content, filename)

    record_audit(
        db=db,
        action="agent.bank_parse_feed",
        entity_type="bank_reconciliation",
        entity_id=0,
        actor=current_user.email,
        details=json.dumps({"count": len(transactions)}),
    )

    return {
        "ok": True,
        "transactions": [
            {"date": t.date, "description": t.description, "amount": t.amount, "type": t.txn_type}
            for t in transactions
        ],
        "count": len(transactions),
    }


@router.post("/bank/reconcile")
def bank_reconcile(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.agent_tool_executor import execute_tool, _data_dir

    transactions = body.get("transactions", [])
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided.")

    output_dir = _data_dir() / "exports" / "reconciliation"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / f"reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

    result = execute_tool(
        "bank_reconcile_and_report",
        {"transactions": transactions, "output_path": output_path},
        "live",
        db,
        current_user,
    )

    record_audit(
        db=db,
        action="agent.bank_reconcile",
        entity_type="bank_reconciliation",
        entity_id=0,
        actor=current_user.email,
        details=json.dumps({"count": len(transactions), "status": result.get("status", "unknown")}),
    )

    if result.get("status") == "success":
        return {
            "ok": True,
            "filepath": output_path,
            "summary": result.get("output", {}).get("summary", {}),
        }
    return {
        "ok": False,
        "status": result.get("status", "failed"),
        "error": result.get("error_message", "Reconciliation failed."),
    }
