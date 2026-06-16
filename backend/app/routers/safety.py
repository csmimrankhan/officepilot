"""Phase 16B/17 — Safety Policy Center + Kill Switch endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..schemas.safety import (
    AutomationStatusRead,
    KillSwitchResponse,
    SafetyPolicyRead,
    SafetyPolicyUpdate,
)
from ..services.permissions import check_permission
from ..services.safety import (
    activate_kill_switch,
    deactivate_kill_switch,
    get_or_create_safety_policy,
    is_kill_switch_active,
    update_safety_policy,
)

logger = logging.getLogger("officepilot.safety_router")

router = APIRouter(prefix="/api/safety", tags=["safety"])


@router.get("/policies", response_model=SafetyPolicyRead)
def get_safety_policies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    policy = get_or_create_safety_policy(db)
    return SafetyPolicyRead(
        id=policy.id,
        cloud_ai_allowed=policy.cloud_ai_allowed,
        browser_automation_enabled=policy.browser_automation_enabled,
        screen_control_enabled=policy.screen_control_enabled,
        workflow_recording_enabled=policy.workflow_recording_enabled,
        accounting_sync_enabled=policy.accounting_sync_enabled,
        voice_enabled=policy.voice_enabled,
        screenshots_enabled=policy.screenshots_enabled,
        ocr_enabled=policy.ocr_enabled,
        require_approval_for_write=policy.require_approval_for_write,
        require_snapshot_for_file_changes=policy.require_snapshot_for_file_changes,
        block_unknown_apps=policy.block_unknown_apps,
        block_unknown_domains=policy.block_unknown_domains,
        created_at=policy.created_at.isoformat() if policy.created_at else None,
        updated_at=policy.updated_at.isoformat() if policy.updated_at else None,
    )


@router.patch("/policies", response_model=SafetyPolicyRead)
def patch_safety_policies(
    body: SafetyPolicyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_permission(db, current_user.role, "manage_safety_policies"):
        raise HTTPException(status_code=403, detail="Only owners can update safety policies")

    updates = body.model_dump(exclude_none=True)
    policy = update_safety_policy(db, updates)
    db.commit()
    return SafetyPolicyRead(
        id=policy.id,
        cloud_ai_allowed=policy.cloud_ai_allowed,
        browser_automation_enabled=policy.browser_automation_enabled,
        screen_control_enabled=policy.screen_control_enabled,
        workflow_recording_enabled=policy.workflow_recording_enabled,
        accounting_sync_enabled=policy.accounting_sync_enabled,
        voice_enabled=policy.voice_enabled,
        screenshots_enabled=policy.screenshots_enabled,
        ocr_enabled=policy.ocr_enabled,
        require_approval_for_write=policy.require_approval_for_write,
        require_snapshot_for_file_changes=policy.require_snapshot_for_file_changes,
        block_unknown_apps=policy.block_unknown_apps,
        block_unknown_domains=policy.block_unknown_domains,
        created_at=policy.created_at.isoformat() if policy.created_at else None,
        updated_at=policy.updated_at.isoformat() if policy.updated_at else None,
    )


@router.post("/kill-switch", response_model=KillSwitchResponse)
def post_kill_switch(
    reason: str = "Manual emergency stop",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_permission(db, current_user.role, "manage_safety_policies") and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    disabled = activate_kill_switch(db, activated_by=current_user.email, reason=reason)
    db.commit()
    logger.warning("Kill switch activated by %s: %s", current_user.email, reason)
    return KillSwitchResponse(active=True, disabled_services=disabled, reason=reason)


@router.post("/resume-automation", response_model=KillSwitchResponse)
def post_resume_automation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_permission(db, current_user.role, "manage_safety_policies") and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    disabled = deactivate_kill_switch(db, resumed_by=current_user.email)
    db.commit()
    logger.info("Kill switch deactivated by %s", current_user.email)
    return KillSwitchResponse(active=False, disabled_services=disabled, reason="Resumed by %s" % current_user.email)


@router.get("/automation-status", response_model=AutomationStatusRead)
def get_automation_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    policy = get_or_create_safety_policy(db)
    ks_active = is_kill_switch_active()
    return AutomationStatusRead(
        kill_switch_active=ks_active,
        browser_automation_enabled=policy.browser_automation_enabled,
        screen_control_enabled=policy.screen_control_enabled,
        workflow_recording_enabled=policy.workflow_recording_enabled,
        accounting_sync_enabled=policy.accounting_sync_enabled,
        browser_automation_blocked=ks_active or not policy.browser_automation_enabled,
        screen_control_blocked=ks_active or not policy.screen_control_enabled,
        workflow_recording_blocked=ks_active or not policy.workflow_recording_enabled,
        accounting_sync_blocked=ks_active or not policy.accounting_sync_enabled,
    )
