"""Phase 20 — Public waitlist + page event router.

Public endpoints (no auth required):
  POST /api/public/waitlist
  POST /api/public/page-event

Admin endpoints (owner/admin only):
  GET    /api/admin/waitlist
  PATCH  /api/admin/waitlist/{entry_id}
  GET    /api/admin/waitlist/summary
  GET    /api/admin/waitlist/export.csv
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User as UserModel
from ..routers.auth import get_current_user
from ..services.public_pilot_waitlist import (
    export_waitlist_csv,
    get_waitlist_summary,
    list_waitlist,
    record_page_event,
    submit_waitlist,
    update_waitlist_status,
)
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["phase20"])


# ── Schemas ──────────────────────────────────────────────────────────────────


class WaitlistSubmitRequest(BaseModel):
    name: str
    email: str
    company: Optional[str] = None
    role: Optional[str] = None
    invoice_volume: Optional[str] = None
    current_workflow: Optional[str] = None
    interested_features_json: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None


class WaitlistEntryResponse(BaseModel):
    id: int
    name: str
    email: str
    company: Optional[str] = None
    role: Optional[str] = None
    invoice_volume: Optional[str] = None
    current_workflow: Optional[str] = None
    interested_features_json: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class WaitlistStatusUpdateRequest(BaseModel):
    status: str


class PageEventRequest(BaseModel):
    event_type: str
    page: Optional[str] = None
    metadata_json: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────────


def _require_admin(current_user: UserModel) -> None:
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Requires owner or admin role")


def _entry_to_dict(e) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "email": e.email,
        "company": e.company,
        "role": e.role,
        "invoice_volume": e.invoice_volume,
        "current_workflow": e.current_workflow,
        "interested_features_json": e.interested_features_json,
        "country": e.country,
        "notes": e.notes,
        "status": e.status,
        "created_at": e.created_at.isoformat() if e.created_at else "",
        "updated_at": e.updated_at.isoformat() if e.updated_at else "",
    }


# ── Public endpoints ─────────────────────────────────────────────────────────


@router.post("/api/public/waitlist", response_model=WaitlistEntryResponse)
def public_submit_waitlist(
    body: WaitlistSubmitRequest,
    db: Session = Depends(get_db),
):
    entry = submit_waitlist(
        name=body.name,
        email=body.email,
        company=body.company,
        role=body.role,
        invoice_volume=body.invoice_volume,
        current_workflow=body.current_workflow,
        interested_features_json=body.interested_features_json,
        country=body.country,
        notes=body.notes,
        db=db,
    )
    return _entry_to_dict(entry)


@router.post("/api/public/page-event")
def public_record_page_event(
    body: PageEventRequest,
    db: Session = Depends(get_db),
):
    evt = record_page_event(
        event_type=body.event_type,
        page=body.page,
        metadata_json=body.metadata_json,
        db=db,
    )
    if evt is None:
        return {"recorded": False, "reason": "analytics_disabled"}
    return {"recorded": True, "id": evt.id}


# ── Admin endpoints ──────────────────────────────────────────────────────────


@router.get("/api/admin/waitlist")
def admin_list_waitlist(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    entries = list_waitlist(db=db, status=status, search=search, skip=skip, limit=limit)
    return [_entry_to_dict(e) for e in entries]


@router.patch("/api/admin/waitlist/{entry_id}")
def admin_update_waitlist_status(
    entry_id: int,
    body: WaitlistStatusUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    try:
        entry = update_waitlist_status(entry_id=entry_id, status=body.status, db=db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    return _entry_to_dict(entry)


@router.get("/api/admin/waitlist/summary")
def admin_waitlist_summary(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    return get_waitlist_summary(db=db)


@router.get("/api/admin/waitlist/export.csv", response_class=PlainTextResponse)
def admin_export_waitlist_csv(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_admin(current_user)
    csv_content = export_waitlist_csv(db=db)
    from fastapi.responses import Response

    headers = {"Content-Disposition": "attachment; filename=pilot_waitlist_export.csv"}
    return Response(content=csv_content, media_type="text/csv", headers=headers)
