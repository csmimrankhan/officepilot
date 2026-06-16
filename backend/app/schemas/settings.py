"""Pydantic schemas for application settings (Phase 3)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


ConflictStrategy = Literal["suffix", "skip", "overwrite"]


class FolderRulesRead(BaseModel):
    enabled: bool = True
    pattern: str = "Invoices/{year}/{month}/{vendor}_{invoice_number}_{total}_{currency}.{ext}"
    conflict_strategy: ConflictStrategy = "suffix"
    move_on_approve: bool = True


class FolderRulesUpdate(BaseModel):
    enabled: Optional[bool] = None
    pattern: Optional[str] = None
    conflict_strategy: Optional[ConflictStrategy] = None
    move_on_approve: Optional[bool] = None


class FolderRulesAuditEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    created_at: datetime
    before: Optional[FolderRulesRead] = None
    after: Optional[FolderRulesRead] = None
