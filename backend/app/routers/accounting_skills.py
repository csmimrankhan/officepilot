from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.accounting_skills import (
    archive_skill,
    complete_skill_run,
    create_skill_from_workflow,
    dry_run_skill,
    execute_skill,
    find_skill_by_phrase,
    get_skill,
    get_skill_versions,
    list_skills,
    list_skill_runs,
    restore_skill_version,
    update_skill,
)
from ..services.audit import log_action as record_audit

logger = logging.getLogger("officepilot.accounting_skills")

router = APIRouter(prefix="/api/accounting-skills", tags=["accounting-skills"])


@router.post("/from-workflow")
def create_skill(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan_id = body.get("plan_id")
    workflow_memory_id = body.get("workflow_memory_id")
    name = body.get("name")
    description = body.get("description")
    trigger_phrases = body.get("trigger_phrases")

    if not plan_id and not workflow_memory_id:
        raise HTTPException(status_code=400, detail="Either plan_id or workflow_memory_id is required")

    result = create_skill_from_workflow(
        db=db,
        user_id=current_user.id,
        plan_id=plan_id,
        workflow_memory_id=workflow_memory_id,
        name=name,
        description=description,
        trigger_phrases=trigger_phrases,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create skill"))
    return result


@router.get("/match")
def match_skill(
    phrase: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = find_skill_by_phrase(db=db, phrase=phrase, user_id=current_user.id)
    if not result:
        return {"matched": False, "skill": None}
    return {"matched": True, "skill": result}


@router.get("")
def list_all_skills(
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_skills(db=db, user_id=current_user.id, status=status)


@router.get("/{skill_id}")
def get_skill_detail(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    skill = get_skill(db=db, user_id=current_user.id, skill_id=skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.patch("/{skill_id}")
def edit_skill(
    skill_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = update_skill(db=db, user_id=current_user.id, skill_id=skill_id, updates=body)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to update skill"))
    return result


@router.post("/{skill_id}/dry-run")
def run_dry_run(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = dry_run_skill(db=db, user_id=current_user.id, skill_id=skill_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Dry-run failed"))
    return result


@router.post("/{skill_id}/execute")
def run_execute(
    skill_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    variables = body.get("variables")
    result = execute_skill(db=db, user_id=current_user.id, skill_id=skill_id, variables=variables)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Execution failed"))
    return result


@router.post("/runs/{run_id}/complete")
def complete_run(
    run_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result_json = body.get("result_json")
    result = complete_skill_run(db=db, run_id=run_id, user_id=current_user.id, result_json=result_json)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to complete run"))
    return result


@router.get("/{skill_id}/versions")
def skill_versions(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    versions = get_skill_versions(db=db, user_id=current_user.id, skill_id=skill_id)
    return versions


@router.post("/{skill_id}/restore/{version}")
def restore_version(
    skill_id: int,
    version: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = restore_skill_version(db=db, user_id=current_user.id, skill_id=skill_id, version=version)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Restore failed"))
    return result


@router.post("/{skill_id}/archive")
def archive_skill_route(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = archive_skill(db=db, user_id=current_user.id, skill_id=skill_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Archive failed"))
    return result


@router.get("/{skill_id}/runs")
def skill_runs(
    skill_id: int,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_skill_runs(db=db, user_id=current_user.id, skill_id=skill_id, limit=limit)


@router.post("/seed-defaults")
def seed_default_excel_skills_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.accounting_skills import seed_default_excel_skills
    seeded = seed_default_excel_skills(db, current_user.id)
    return {"ok": True, "seeded": seeded, "count": len(seeded)}
