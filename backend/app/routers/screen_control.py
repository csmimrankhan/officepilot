"""Phase 16A — Screen Control HTTP API (real execution layer).

Endpoints (all under ``/api/screen``):

* ``GET    /policies``              — read the singleton policy row
* ``PATCH  /policies``              — toggle / edit permissions / etc.
* ``GET    /status``                — runtime status
* ``GET    /capabilities``          — available capabilities (OCR, click, type)
* ``GET    /ocr/status``            — OCR engine availability
* ``POST   /start-session``         — start a screen control session
* ``POST   /end-session``           — end a session
* ``POST   /emergency-stop``        — emergency stop
* ``POST   /read``                  — read active window context
* ``POST   /capture``               — capture screenshot
* ``POST   /ocr``                   — extract visible text (real OCR)
* ``POST   /summarize``             — summarize screen context
* ``POST   /plan-action``           — build an action preview
* ``GET    /actions``               — list recent actions
* ``GET    /actions/{id}``          — action details
* ``POST   /actions/{id}/approve``  — approve an action
* ``POST   /actions/{id}/reject``   — reject an action
* ``POST   /actions/{id}/execute-step`` — execute one approved step
* ``POST   /actions/{id}/execute-all`` — execute all approved steps
* ``POST   /actions/{id}/cancel``   — cancel an action
* ``GET    /actions/{id}/steps``    — step logs for an action
* ``GET    /sessions``              — list sessions
* ``POST   /voice``                 — voice intent dispatch
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.screen_control import (
    DEFAULT_ALLOWED_APPS,
    DEFAULT_BLOCKED_APPS,
    ScreenControlAction,
    ScreenControlPolicy,
    ScreenControlSession,
    ScreenControlStepLog,
)
from ..schemas.screen_control import (
    ScreenActionApproveResponse,
    ScreenActionPreviewResponse,
    ScreenActionRead,
    ScreenActionReadWithPreview,
    ScreenActionRejectResponse,
    ScreenCapabilitiesResponse,
    ScreenCaptureResponse,
    ScreenEmergencyStopResponse,
    ScreenExecuteAllResponse,
    ScreenOcrResponse,
    ScreenOcrStatusResponse,
    ScreenOpenFileRequest,
    ScreenOpenFolderRequest,
    ScreenPolicyRead,
    ScreenPolicyUpdate,
    ScreenReadContextResponse,
    ScreenSessionRead,
    ScreenSessionStartResponse,
    ScreenStatusRead,
    ScreenStepExecuteResponse,
    ScreenStepLogRead,
    ScreenSummarizeResponse,
    ScreenVoiceIntentRequest,
    ScreenVoiceIntentResponse,
)
from ..services.screen_control import (
    KNOWN_VOICE_INTENTS,
    _get_allowed_apps,
    _get_blocked_apps,
    _get_blocked_domains,
    _log_audit,
    allowed_app_check,
    approve_screen_action,
    blocked_app_check,
    blocked_domain_check,
    build_action_preview,
    cancel_screen_action,
    capture_screenshot,
    check_permission_level,
    create_screen_action,
    detect_active_window,
    dispatch_voice_intent,
    emergency_stop_screen,
    end_screen_session,
    enforce_app_allowlist,
    execute_all_approved_steps,
    execute_screen_action_step,
    extract_visible_text_ocr,
    get_capabilities,
    get_or_create_policy,
    reject_screen_action,
    start_screen_session,
    summarize_screen_context,
)

logger = logging.getLogger("officepilot.screen_control")
router = APIRouter(prefix="/api/screen", tags=["Screen Control"])


# ── Policies ────────────────────────────────────────────────────────


@router.get("/policies", response_model=ScreenPolicyRead)
def get_screen_policies(db: Session = Depends(get_db)):
    policy = get_or_create_policy(db)
    return ScreenPolicyRead(
        id=policy.id,
        enabled=policy.enabled,
        permission_level=policy.permission_level,
        screenshots_enabled=policy.screenshots_enabled,
        ocr_enabled=policy.ocr_enabled,
        click_enabled=policy.click_enabled,
        type_enabled=policy.type_enabled,
        clipboard_enabled=policy.clipboard_enabled,
        allowed_apps=json.loads(policy.allowed_apps_json or "[]"),
        blocked_apps=json.loads(policy.blocked_apps_json or "[]"),
        allowed_folders=json.loads(policy.allowed_folders_json or "[]"),
        blocked_domains=json.loads(policy.blocked_domains_json or "[]"),
        require_approval_for_click=policy.require_approval_for_click,
        require_approval_for_type=policy.require_approval_for_type,
        require_approval_for_submit=policy.require_approval_for_submit,
        require_approval_for_clipboard=policy.require_approval_for_clipboard,
        emergency_stop_enabled=policy.emergency_stop_enabled,
        notes=policy.notes,
        created_at=policy.created_at.isoformat() if policy.created_at else None,
        updated_at=policy.updated_at.isoformat() if policy.updated_at else None,
    )


@router.patch("/policies", response_model=ScreenPolicyRead)
def update_screen_policies(body: ScreenPolicyUpdate, db: Session = Depends(get_db)):
    policy = get_or_create_policy(db)

    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "allowed_apps" and value is not None:
            policy.allowed_apps_json = json.dumps(value)
        elif field == "blocked_apps" and value is not None:
            policy.blocked_apps_json = json.dumps(value)
        elif field == "allowed_folders" and value is not None:
            policy.allowed_folders_json = json.dumps(value)
        elif field == "blocked_domains" and value is not None:
            policy.blocked_domains_json = json.dumps(value)
        else:
            setattr(policy, field, value)

    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)

    _log_audit(db, "screen.policy_updated", f"Screen policy updated by user")
    return get_screen_policies(db)


# ── Status / Session ────────────────────────────────────────────────


@router.get("/status", response_model=ScreenStatusRead)
def get_screen_status(db: Session = Depends(get_db)):
    policy = get_or_create_policy(db)
    active = db.query(ScreenControlSession).filter(
        ScreenControlSession.status == "active"
    ).first()

    ctx = detect_active_window()

    return ScreenStatusRead(
        enabled=policy.enabled,
        permission_level=policy.permission_level,
        screenshots_enabled=policy.screenshots_enabled,
        ocr_enabled=policy.ocr_enabled,
        click_enabled=policy.click_enabled,
        type_enabled=policy.type_enabled,
        clipboard_enabled=policy.clipboard_enabled,
        session_active=active is not None,
        session_id=active.id if active else None,
        active_app=active.active_app if active else ctx.get("app", ""),
        active_window_title=active.active_window_title if active else ctx.get("window_title", ""),
        allowed_apps=_get_allowed_apps(policy),
        blocked_apps=_get_blocked_apps(policy),
        allowed_folders=json.loads(policy.allowed_folders_json or "[]"),
    )


@router.post("/start-session", response_model=ScreenSessionStartResponse)
def start_session(db: Session = Depends(get_db)):
    try:
        result = start_screen_session(db)
        return ScreenSessionStartResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/capabilities", response_model=ScreenCapabilitiesResponse)
def get_screen_capabilities():
    caps = get_capabilities()
    return ScreenCapabilitiesResponse(**caps)


@router.get("/ocr/status", response_model=ScreenOcrStatusResponse)
def get_ocr_status():
    caps = get_capabilities()
    msg = ""
    if caps["ocr_available"]:
        msg = f"OCR engine '{caps['ocr_engine']}' is available"
    else:
        msg = f"OCR engine '{caps['ocr_engine']}' is not installed or not configured"
    return ScreenOcrStatusResponse(
        engine=caps["ocr_engine"],
        available=caps["ocr_available"],
        message=msg,
    )


@router.post("/end-session")
def end_session(
    session_id: int = Query(...),
    stopped_by: str = Query("user"),
    reason: str = Query(""),
    db: Session = Depends(get_db),
):
    try:
        result = end_screen_session(db, session_id, stopped_by, reason)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/emergency-stop", response_model=ScreenEmergencyStopResponse)
def emergency_stop_route(
    session_id: int = Query(None),
    stopped_by: str = Query("user"),
    db: Session = Depends(get_db),
):
    result = emergency_stop_screen(db, session_id=session_id, stopped_by=stopped_by)
    return ScreenEmergencyStopResponse(**result)


# ── Read-only context ───────────────────────────────────────────────


@router.post("/read", response_model=ScreenReadContextResponse)
def read_screen_context(db: Session = Depends(get_db)):
    policy = get_or_create_policy(db)
    if not check_permission_level(policy, 1):
        raise HTTPException(status_code=403, detail="Screen control is disabled or permission level too low")

    ctx = detect_active_window()
    screenshot_path = ""
    ocr_text = ""

    if policy.screenshots_enabled:
        active = db.query(ScreenControlSession).filter(
            ScreenControlSession.status == "active"
        ).first()
        if active:
            screenshot_path = capture_screenshot(active.id)

    if policy.ocr_enabled and screenshot_path:
        ocr_text = extract_visible_text_ocr(screenshot_path)

    summary = summarize_screen_context(ctx.get("app", ""), ctx.get("window_title", ""), ocr_text)

    _log_audit(db, "screen.read_context", f"Read screen context: {summary[:100]}")

    return ScreenReadContextResponse(
        active_app=ctx.get("app", "unknown"),
        active_window_title=ctx.get("window_title", ""),
        ocr_text=ocr_text,
        screenshot_path=screenshot_path,
        summary=summary,
    )


@router.post("/capture", response_model=ScreenCaptureResponse)
def capture_screen(db: Session = Depends(get_db)):
    policy = get_or_create_policy(db)
    if not check_permission_level(policy, 1):
        raise HTTPException(status_code=403, detail="Screen control is disabled or permission level too low")
    if not policy.screenshots_enabled:
        raise HTTPException(status_code=403, detail="Screenshots are disabled in policy")

    active = db.query(ScreenControlSession).filter(
        ScreenControlSession.status == "active"
    ).first()
    if not active:
        raise HTTPException(status_code=400, detail="No active screen session")

    path = capture_screenshot(active.id)
    _log_audit(db, "screen.capture", f"Screenshot captured for session #{active.id}")

    return ScreenCaptureResponse(screenshot_path=path, stored=bool(path))


@router.post("/ocr", response_model=ScreenOcrResponse)
def ocr_screen(db: Session = Depends(get_db)):
    policy = get_or_create_policy(db)
    if not check_permission_level(policy, 1):
        raise HTTPException(status_code=403, detail="Screen control is disabled or permission level too low")
    if not policy.ocr_enabled:
        raise HTTPException(status_code=403, detail="OCR is disabled in policy")

    active = db.query(ScreenControlSession).filter(
        ScreenControlSession.status == "active"
    ).first()
    if not active:
        raise HTTPException(status_code=400, detail="No active screen session")

    screenshot_path = capture_screenshot(active.id) if policy.screenshots_enabled else ""
    text = extract_visible_text_ocr(screenshot_path)
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    return ScreenOcrResponse(text=text, lines=lines)


@router.post("/summarize", response_model=ScreenSummarizeResponse)
def summarize_screen(db: Session = Depends(get_db)):
    policy = get_or_create_policy(db)
    if not check_permission_level(policy, 1):
        raise HTTPException(status_code=403, detail="Screen control is disabled or permission level too low")

    ctx = detect_active_window()
    summary = summarize_screen_context(ctx.get("app", ""), ctx.get("window_title", ""))

    return ScreenSummarizeResponse(
        summary=summary,
        app=ctx.get("app", "unknown"),
        window=ctx.get("window_title", ""),
        text_length=0,
    )


# ── Planning ────────────────────────────────────────────────────────


@router.post("/plan-action", response_model=ScreenActionPreviewResponse)
def plan_action(
    intent: str = Query(""),
    action_type: str = Query(""),
    app_name: str = Query(""),
    window_title: str = Query(""),
    target: str = Query(""),
    source_type: str = Query("ui"),
    source_id: str = Query(""),
    db: Session = Depends(get_db),
):
    policy = get_or_create_policy(db)
    if not check_permission_level(policy, 1):
        raise HTTPException(status_code=403, detail="Screen control is disabled or permission level too low")

    resolved_type = action_type or intent.lower().replace(" ", "_")
    if not resolved_type:
        raise HTTPException(status_code=400, detail="Either intent or action_type is required")

    ctx = detect_active_window()
    app = app_name or ctx.get("app", "unknown")
    window = window_title or ctx.get("window_title", "")

    # Blocked app check
    blocked_apps = _get_blocked_apps(policy)
    if blocked_app_check(app, blocked_apps):
        return ScreenActionPreviewResponse(
            action_id=0,
            action_type=resolved_type,
            app_name=app,
            window_title=window,
            target_description=target,
            risk={"risk_level": "high", "requires_approval": True, "reasons": [f"App '{app}' is blocked"]},
            steps=[],
            blocked={"allowed": False, "reason": f"Application '{app}' is blocked"},
        )

    # Ensure active session
    active = db.query(ScreenControlSession).filter(
        ScreenControlSession.status == "active"
    ).first()
    session_id = active.id if active else None
    if not session_id:
        try:
            session_info = start_screen_session(db)
            session_id = session_info["session_id"]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Check click/type permissions
    if resolved_type in ("click",) and not policy.click_enabled:
        raise HTTPException(status_code=403, detail="Click actions are disabled in policy")
    if resolved_type in ("type_text", "paste_text", "hotkey") and not policy.type_enabled:
        raise HTTPException(status_code=403, detail="Type actions are disabled in policy")

    action_info = create_screen_action(
        db=db,
        session_id=session_id,
        action_type=resolved_type,
        source_type=source_type,
        source_id=source_id,
        app_name=app,
        window_title=window,
        target_description=target,
    )

    return ScreenActionPreviewResponse(
        action_id=action_info["action_id"],
        action_type=resolved_type,
        app_name=app,
        window_title=window,
        target_description=target,
        risk={
            "risk_level": action_info["risk_level"],
            "requires_approval": action_info["requires_approval"],
            "reasons": action_info["risk_reasons"],
        },
        steps=action_info["steps"],
    )


# ── Actions ─────────────────────────────────────────────────────────


@router.get("/actions", response_model=list[ScreenActionRead])
def list_actions(
    session_id: int = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(ScreenControlAction).order_by(ScreenControlAction.id.desc())
    if session_id:
        q = q.filter(ScreenControlAction.session_id == session_id)
    actions = q.offset(skip).limit(limit).all()

    result = []
    for a in actions:
        result.append(ScreenActionRead(
            id=a.id,
            session_id=a.session_id,
            source_type=a.source_type,
            source_id=a.source_id,
            action_type=a.action_type,
            app_name=a.app_name,
            window_title=a.window_title,
            target_description=a.target_description,
            risk_level=a.risk_level,
            approval_status=a.approval_status,
            status=a.status,
            screenshot_path=a.screenshot_path,
            ocr_text_excerpt=a.ocr_text_excerpt,
            error_message=a.error_message,
            browser_action_run_id=a.browser_action_run_id,
            stopped_by=a.stopped_by if hasattr(a, 'stopped_by') else "",
            stop_reason=a.stop_reason if hasattr(a, 'stop_reason') else "",
            created_at=a.created_at.isoformat() if a.created_at else None,
            completed_at=a.completed_at.isoformat() if a.completed_at else None,
        ))
    return result


@router.get("/actions/{action_id}", response_model=ScreenActionRead)
def get_action(action_id: int, db: Session = Depends(get_db)):
    action = db.get(ScreenControlAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Screen action not found")
    return ScreenActionRead(
        id=action.id,
        session_id=action.session_id,
        source_type=action.source_type,
        source_id=action.source_id,
        action_type=action.action_type,
        app_name=action.app_name,
        window_title=action.window_title,
        target_description=action.target_description,
        risk_level=action.risk_level,
        approval_status=action.approval_status,
        status=action.status,
        screenshot_path=action.screenshot_path,
        ocr_text_excerpt=action.ocr_text_excerpt,
        error_message=action.error_message,
        browser_action_run_id=action.browser_action_run_id,
        stopped_by=getattr(action, "stopped_by", ""),
        stop_reason=getattr(action, "stop_reason", ""),
        created_at=action.created_at.isoformat() if action.created_at else None,
        completed_at=action.completed_at.isoformat() if action.completed_at else None,
    )


@router.post("/actions/{action_id}/approve", response_model=ScreenActionApproveResponse)
def approve_action(action_id: int, db: Session = Depends(get_db)):
    try:
        result = approve_screen_action(db, action_id)
        action = db.get(ScreenControlAction, action_id)
        return ScreenActionApproveResponse(
            action_id=result["action_id"],
            status=result["status"],
            approval_status=result["approval_status"],
            steps=[{
                "step_order": 1,
                "step_type": action.action_type,
                "target_description": action.target_description,
                "requires_approval": False,
            }] if action else [],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/actions/{action_id}/reject", response_model=ScreenActionRejectResponse)
def reject_action(action_id: int, db: Session = Depends(get_db)):
    try:
        result = reject_screen_action(db, action_id)
        return ScreenActionRejectResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/actions/{action_id}/execute-step", response_model=ScreenStepExecuteResponse)
def execute_step(
    action_id: int,
    approve_first: bool = Query(True),
    db: Session = Depends(get_db),
):
    try:
        result = execute_screen_action_step(db, action_id, approve_before_execute=approve_first)
        return ScreenStepExecuteResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/actions/{action_id}/execute-all", response_model=ScreenExecuteAllResponse)
def execute_all_approved(
    action_id: int,
    db: Session = Depends(get_db),
):
    try:
        results = execute_all_approved_steps(db, action_id)
        return ScreenExecuteAllResponse(
            action_id=action_id,
            results=[
                ScreenStepExecuteResponse(**r) for r in results
            ],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/actions/{action_id}/cancel")
def cancel_action(action_id: int, db: Session = Depends(get_db)):
    try:
        result = cancel_screen_action(db, action_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/actions/{action_id}/steps", response_model=list[ScreenStepLogRead])
def list_action_steps(action_id: int, db: Session = Depends(get_db)):
    steps = (
        db.query(ScreenControlStepLog)
        .filter(ScreenControlStepLog.action_id == action_id)
        .order_by(ScreenControlStepLog.step_order)
        .all()
    )
    return [
        ScreenStepLogRead(
            id=s.id,
            action_id=s.action_id,
            step_order=s.step_order,
            step_type=s.step_type,
            target_description=s.target_description,
            status=s.status,
            screenshot_path=s.screenshot_path,
            error_message=s.error_message,
            browser_action_step_id=s.browser_action_step_id,
            stopped_by=getattr(s, "stopped_by", ""),
            stop_reason=getattr(s, "stop_reason", ""),
            created_at=s.created_at.isoformat() if s.created_at else None,
        )
        for s in steps
    ]


# ── Sessions ────────────────────────────────────────────────────────


@router.get("/sessions", response_model=list[ScreenSessionRead])
def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=500),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ScreenControlSession)
        .order_by(ScreenControlSession.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        ScreenSessionRead(
            id=s.id,
            user_id=s.user_id,
            status=s.status,
            permission_level=s.permission_level,
            active_app=s.active_app,
            active_window_title=s.active_window_title,
            started_at=s.started_at.isoformat() if s.started_at else None,
            ended_at=s.ended_at.isoformat() if s.ended_at else None,
            stopped_by=s.stopped_by,
            stop_reason=s.stop_reason,
        )
        for s in sessions
    ]


# ── Voice ───────────────────────────────────────────────────────────


@router.get("/voices")
def list_voice_intents():
    return KNOWN_VOICE_INTENTS


@router.post("/voice", response_model=ScreenVoiceIntentResponse)
def voice_intent_route(body: ScreenVoiceIntentRequest, db: Session = Depends(get_db)):
    result = dispatch_voice_intent(db, intent=body.intent, source_id=body.source_id)
    error = result.get("error")
    if error:
        raise HTTPException(status_code=400, detail=error)
    return ScreenVoiceIntentResponse(
        intent=result["intent"],
        parsed_action=result["parsed_action"],
        preview=result["preview"],
    )
