"""Phase 22.5 — Voice Command Router."""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..config import get_settings, Settings
from ..db import get_db
from ..models.user import User
from ..models.voice_command import VoiceCommand
from ..routers.auth import get_current_user
from ..schemas.voice import (
    VoiceCommandRead,
    VoiceCommandCreate,
    VoiceTranscribeResponse,
    VoiceParseResponse,
    VoiceExecuteResponse,
    AvailableCommand,
    VoiceHistoryResponse,
    STTStatusResponse
)
from ..services.accountant_autopilot import build_accountant_plan
from ..services.multilingual_command import detect_language, normalize_command, translate_to_internal_english, generate_voice_reply
from ..services.voice_reply import build_user_reply
from ..services.voice import VoiceSTTService, VoiceIntentParser
from ..services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

AVAILABLE_COMMANDS: List[dict] = [
    {"category": "Invoice", "description": "View, open, and copy from invoices", "examples": ["show pending invoices", "open invoice INV-1001", "copy amount from this invoice"]},
    {"category": "Excel", "description": "Export and generate reports", "examples": ["export approved invoices to Excel", "create monthly summary"]},
    {"category": "Accounting", "description": "Sync with accounting platforms", "examples": ["export to QuickBooks", "export to Xero", "show failed syncs"]},
    {"category": "Browser", "description": "Navigate and fill browser forms", "examples": ["open Google Sheets", "fill this into test form"]},
    {"category": "Screen Control", "description": "Read and interact with your screen", "examples": ["read current window", "open invoice folder", "emergency stop"]},
]

@router.get("/stt-status", response_model=STTStatusResponse)
def get_stt_status(settings: Settings = Depends(get_settings)):
    stt = VoiceSTTService(settings)
    return stt.get_status()

@router.get("/available-commands", response_model=List[AvailableCommand])
def get_available_commands():
    return AVAILABLE_COMMANDS

@router.get("/history", response_model=VoiceHistoryResponse)
def get_voice_history(limit: int = 50, db: Session = Depends(get_db)):
    cmds = db.query(VoiceCommand).order_by(desc(VoiceCommand.created_at)).limit(limit).all()
    return {"commands": cmds}

@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_voice(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings)
):
    # Enforce size limits
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.voice_audio_max_mb:
        raise HTTPException(status_code=413, detail=f"Audio file too large ({size_mb:.1f}MB > {settings.voice_audio_max_mb}MB)")

    stt = VoiceSTTService(settings)
    res = await stt.transcribe(content, file.filename)
    
    if res.get("status") == "failed":
        raise HTTPException(status_code=500, detail=res.get("error_message"))
    
    return res

@router.post("/parse-command", response_model=VoiceParseResponse)
def parse_voice_command(
    payload: VoiceCommandCreate, 
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
):
    plan = build_accountant_plan(db, payload.raw_text, current_user)

    lang = plan.get("language", detect_language(payload.raw_text))
    normalized = normalize_command(payload.raw_text)
    internal_english = translate_to_internal_english(payload.raw_text)

    domain = plan.get("task_type", "general")
    intent = plan.get("task_title", "Execute Task")
    risk_level = plan.get("risk_level", "low")
    requires_approval = plan.get("requires_approval", True)
    clarification_needed = plan.get("clarification_needed", False)
    clarification_question = plan.get("clarification_question")
    blocked_reason = plan.get("blocked_reason")

    params = {
        "normalized_command": normalized,
        "internal_english_command": internal_english,
        "detected_language": lang,
        "summary_for_user": plan.get("summary_for_user") or plan.get("task_summary", ""),
        "platform_detected": plan.get("platform_detected", "unknown"),
        "can_save_workflow": plan.get("can_save_workflow", False),
        "task_type": domain,
        "blocked_reason": blocked_reason,
    }

    preview_message = plan.get("summary_for_user") or plan.get("task_summary", "Task plan ready.")

    suggestions = []
    if clarification_needed:
        suggestions = ["Read this screen", "Download today's invoices", "Show workflow memory"]
    elif blocked_reason:
        suggestions = []
    else:
        suggestions = ["Approve and execute"]
        if plan.get("can_save_workflow"):
            suggestions.append("Save as workflow")

    status = "detected"
    if requires_approval:
        status = "pending_approval"
    if blocked_reason:
        status = "failed"
    if clarification_needed:
        status = "detected"

    cmd = VoiceCommand(
        raw_text=payload.raw_text,
        status=status,
        domain=domain,
        intent=intent,
        parsed_intent=plan,
        risk_level=risk_level,
        confidence=1.0,
        clarification_needed=clarification_needed,
        clarification_question=clarification_question,
        provider=settings.voice_provider,
    )
    if blocked_reason:
        cmd.error_message = blocked_reason

    db.add(cmd)
    db.commit()
    db.refresh(cmd)

    return {
        "command_id": cmd.id,
        "raw_text": cmd.raw_text,
        "domain": domain,
        "intent": intent,
        "params": params,
        "needs_approval": requires_approval,
        "preview_message": preview_message,
        "risk_level": risk_level,
        "confidence": 1.0,
        "clarification_needed": clarification_needed,
        "clarification_question": clarification_question,
        "suggestions": suggestions,
    }

@router.post("/execute-command", response_model=VoiceExecuteResponse)
def execute_voice_command(command_id: int, db: Session = Depends(get_db)):
    cmd = db.query(VoiceCommand).filter(VoiceCommand.id == command_id).first()
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    
    if cmd.status == "pending_approval":
        return {
            "success": False, 
            "message": "This command requires explicit approval.",
            "requires_approval": True
        }

    # Execute logic based on domain/intent
    success = True
    message = f"Executed {cmd.intent} in {cmd.domain}."
    
    # In a real implementation, this would call browser_automation, accounting services, etc.
    # For now, we mock success and log the action.
    
    cmd.status = "completed"
    db.commit()
    
    log_action(
        db, 
        actor="voice", 
        action="execute", 
        entity_type="voice_command", 
        entity_id=cmd.id,
        details=f"Executed {cmd.domain}:{cmd.intent}"
    )
    
    return {"success": success, "message": message}

@router.post("/commands/{command_id}/confirm", response_model=VoiceExecuteResponse)
def confirm_voice_command(command_id: int, db: Session = Depends(get_db)):
    cmd = db.query(VoiceCommand).filter(VoiceCommand.id == command_id).first()
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    
    cmd.status = "executing"
    db.commit()
    
    # Trigger actual execution...
    success = True
    message = f"Approved and executed {cmd.intent}."
    
    cmd.status = "completed"
    db.commit()
    
    log_action(
        db, 
        actor="voice", 
        action="confirm", 
        entity_type="voice_command", 
        entity_id=cmd.id,
        details=f"Approved {cmd.domain}:{cmd.intent}"
    )
    
    return {"success": success, "message": message}
