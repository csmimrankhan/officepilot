from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.correction_rule import AccountingCorrectionRule
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.learning_loop import delete_rule, get_active_rules, record_correction

logger = logging.getLogger("officepilot.learning_router")

router = APIRouter(prefix="/api/agent", tags=["agent"])


class CorrectionCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trigger_vendor: str
    wrong_category: str | None = None
    correct_category: str = ""
    notes: str | None = None


class CorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    trigger_vendor_pattern: str
    wrong_category: str | None
    correct_category: str
    notes: str | None
    created_at: str

    @classmethod
    def from_orm(cls, rule: AccountingCorrectionRule) -> CorrectionResponse:
        return cls(
            id=rule.id,
            user_id=rule.user_id,
            trigger_vendor_pattern=rule.trigger_vendor_pattern,
            wrong_category=rule.wrong_category,
            correct_category=rule.correct_category,
            notes=rule.notes,
            created_at=rule.created_at.isoformat() if rule.created_at else "",
        )


@router.post("/correct", response_model=dict)
def create_correction(
    body: CorrectionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rule = record_correction(
        db=db,
        user_id=current_user.id,
        trigger_vendor=body.trigger_vendor,
        wrong_category=body.wrong_category,
        correct_category=body.correct_category or body.trigger_vendor,
        notes=body.notes,
    )
    return {
        "status": "ok",
        "rule_id": rule.id,
        "message": f"Correction rule saved. Agent will remember that '{rule.trigger_vendor_pattern}' → '{rule.correct_category}'.",
    }


@router.get("/corrections", response_model=list[dict])
def list_corrections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    rules = get_active_rules(db=db, user_id=current_user.id)
    return [CorrectionResponse.from_orm(r).model_dump() for r in rules]


@router.delete("/corrections/{rule_id}", response_model=dict)
def remove_correction(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ok = delete_rule(db=db, rule_id=rule_id, user_id=current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Correction rule not found")
    return {"status": "ok", "message": "Correction rule deleted."}
