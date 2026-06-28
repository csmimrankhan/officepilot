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
from pydantic import BaseModel, ConfigDict, EmailStr
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
from fastapi.responses import HTMLResponse, PlainTextResponse

router = APIRouter(tags=["admin"])


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

    model_config = ConfigDict(from_attributes=True)


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


_LAUNCH_EMAIL_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>OfficePilot v1.0.0 Launch</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f7fa;padding:32px;margin:0">
<table role="presentation" style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)">
<tr><td style="background:linear-gradient(135deg,#1f4e78,#163a5a);padding:40px 32px;text-align:center">
<h1 style="color:#fff;margin:0 0 8px;font-size:24px;">🚀 OfficePilot v1.0.0 is here</h1>
<p style="color:rgba(255,255,255,.85);margin:0;font-size:16px;">Your Autonomous AI Accountant</p>
</td></tr>
<tr><td style="padding:32px">
<p style="color:#333;font-size:16px;line-height:1.6">Hello {name},</p>
<p style="color:#555;font-size:15px;line-height:1.6">We are thrilled to announce the official release of <strong>OfficePilot v1.0.0</strong> — our biggest update yet, bringing enterprise-grade automation to your accounting workflow.</p>
<h2 style="color:#1f4e78;font-size:18px;margin:28px 0 16px">What's New in v1.0.0</h2>
<table role="presentation" style="width:100%;border-collapse:collapse">
<tr><td style="padding:12px 16px;background:#f8faff;border-radius:8px;margin-bottom:10px;display:block">
<strong style="color:#1f4e78;display:block;margin-bottom:4px">🤖 Multi-Agent Swarm Architecture</strong>
<span style="color:#666;font-size:14px">Three specialist AI agents — Auditor, Tax, Data Entry — each focused on their domain, working together to handle every accounting task.</span>
</td></tr>
<tr><td style="padding:12px 16px;background:#f8faff;border-radius:8px;margin-bottom:10px;display:block">
<strong style="color:#1f4e78;display:block;margin-bottom:4px">⚖️ Semantic Bank Reconciliation</strong>
<span style="color:#666;font-size:14px">Conceptually match vague bank transactions to your invoices using local vector memory, with color-coded Excel reports and three confidence tiers.</span>
</td></tr>
<tr><td style="padding:12px 16px;background:#f8faff;border-radius:8px;margin-bottom:10px;display:block">
<strong style="color:#1f4e78;display:block;margin-bottom:4px">🎤 Live Voice-Driven Excel Editing</strong>
<span style="color:#666;font-size:14px">Connect directly to your open Excel window via COM automation. Format, pivot, chart, and calculate by voice — with safety undo snapshots.</span>
</td></tr>
<tr><td style="padding:12px 16px;background:#f8faff;border-radius:8px;margin-bottom:10px;display:block">
<strong style="color:#1f4e78;display:block;margin-bottom:4px">👁️ Autonomous Background Watchers</strong>
<span style="color:#666;font-size:14px">Always-on monitors for Gmail, Google Drive, and local folders — silently scanning for invoices and extracting data while you work.</span>
</td></tr>
<tr><td style="padding:12px 16px;background:#f8faff;border-radius:8px;display:block">
<strong style="color:#1f4e78;display:block;margin-bottom:4px">🧠 Ollama Local LLM Brain</strong>
<span style="color:#666;font-size:14px">Private on-device AI with zero cloud dependency. Your data never leaves your machine.</span>
</td></tr>
</table>
<div style="text-align:center;margin:32px 0 8px">
<a href="https://officepilot.ai/download" style="display:inline-block;padding:14px 36px;background:#1f4e78;color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:16px">Download OfficePilot v1.0.0</a>
</div>
<p style="color:#888;font-size:13px;text-align:center;margin-top:24px">Questions? Reply to this email or visit our <a href="https://github.com/anomalyco/officepilot" style="color:#1f4e78">GitHub</a>.\nThe OfficePilot Team</p>
</td></tr>
</table>
</body>
</html>"""


@router.get("/api/admin/waitlist/launch-email", response_class=HTMLResponse)
def admin_launch_email(
    name: str = Query("there", min_length=1),
    current_user: UserModel = Depends(get_current_user),
):
    _require_admin(current_user)
    return _LAUNCH_EMAIL_TEMPLATE.replace("{name}", name)


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
