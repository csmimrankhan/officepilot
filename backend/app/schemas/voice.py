"""Phase 22.5 — Voice schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Any, Dict, List

from pydantic import BaseModel, Field


class VoiceCommandBase(BaseModel):
    raw_text: Optional[str] = None
    parsed_intent: Optional[Dict[str, Any]] = None
    status: str = "idle"
    domain: Optional[str] = None
    intent: Optional[str] = None
    risk_level: Optional[str] = None
    external_id: Optional[int] = None
    error_message: Optional[str] = None
    provider: Optional[str] = None
    confidence: Optional[float] = None
    clarification_needed: bool = False
    clarification_question: Optional[str] = None


class VoiceCommandCreate(BaseModel):
    raw_text: str


class VoiceCommandUpdate(BaseModel):
    status: Optional[str] = None
    parsed_intent: Optional[Dict[str, Any]] = None
    domain: Optional[str] = None
    intent: Optional[str] = None
    risk_level: Optional[str] = None
    external_id: Optional[int] = None
    error_message: Optional[str] = None
    provider: Optional[str] = None
    confidence: Optional[float] = None
    clarification_needed: Optional[bool] = None
    clarification_question: Optional[str] = None


class VoiceCommandRead(VoiceCommandBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VoiceTranscribeResponse(BaseModel):
    transcript: str
    provider: str
    duration_seconds: float = 0.0
    confidence: Optional[float] = None
    status: str = "completed"
    error_message: Optional[str] = None


class VoiceParseResponse(BaseModel):
    command_id: int
    raw_text: str
    domain: str
    intent: str
    params: Dict[str, Any]
    needs_approval: bool
    preview_message: str
    risk_level: str = "low"
    confidence: float = 1.0
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    suggestions: List[str] = []


class VoiceExecuteResponse(BaseModel):
    success: bool
    message: str
    external_id: Optional[int] = None
    requires_approval: bool = False


class AvailableCommand(BaseModel):
    category: str
    examples: List[str]
    description: str


class VoiceHistoryResponse(BaseModel):
    commands: List[VoiceCommandRead]


class STTStatusResponse(BaseModel):
    provider: str
    configured: bool
    cloud_allowed: bool
    max_seconds: int
    max_mb: int
    message: str
    demo_mode: bool
