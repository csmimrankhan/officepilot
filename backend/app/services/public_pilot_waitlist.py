"""Phase 20 — Public pilot waitlist service.

Handles waitlist signup, admin list/update/summary, CSV export,
and public page event recording.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Optional

from fastapi import Depends
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.pilot_waitlist import PilotWaitlist
from ..models.public_page_event import PublicPageEvent


def submit_waitlist(
    *,
    name: str,
    email: str,
    company: Optional[str] = None,
    role: Optional[str] = None,
    invoice_volume: Optional[str] = None,
    current_workflow: Optional[str] = None,
    interested_features_json: Optional[str] = None,
    country: Optional[str] = None,
    notes: Optional[str] = None,
    db: Session,
) -> PilotWaitlist:
    norm_email = email.strip().lower()
    existing = db.query(PilotWaitlist).filter(PilotWaitlist.email == norm_email).first()
    if existing:
        return existing

    entry = PilotWaitlist(
        name=name.strip(),
        email=norm_email,
        company=company.strip() if company else None,
        role=role.strip() if role else None,
        invoice_volume=invoice_volume,
        current_workflow=current_workflow,
        interested_features_json=interested_features_json,
        country=country.strip() if country else None,
        notes=notes.strip() if notes else None,
        status="new",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_waitlist(
    db: Session,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[PilotWaitlist]:
    q = db.query(PilotWaitlist)
    if status:
        q = q.filter(PilotWaitlist.status == status)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (PilotWaitlist.name.ilike(pattern))
            | (PilotWaitlist.email.ilike(pattern))
            | (PilotWaitlist.company.ilike(pattern))
        )
    q = q.order_by(PilotWaitlist.created_at.desc()).offset(skip).limit(limit)
    return q.all()


def update_waitlist_status(
    entry_id: int,
    status: str,
    db: Session,
) -> Optional[PilotWaitlist]:
    entry = db.query(PilotWaitlist).filter(PilotWaitlist.id == entry_id).first()
    if not entry:
        return None
    allowed = {"new", "contacted", "demo_scheduled", "accepted", "rejected"}
    if status not in allowed:
        raise ValueError(f"Invalid status: {status}. Allowed: {', '.join(sorted(allowed))}")
    entry.status = status
    db.commit()
    db.refresh(entry)
    return entry


def get_waitlist_summary(db: Session) -> dict[str, Any]:
    total = db.query(sa_func.count(PilotWaitlist.id)).scalar() or 0

    by_role_rows = (
        db.query(PilotWaitlist.role, sa_func.count(PilotWaitlist.id))
        .group_by(PilotWaitlist.role)
        .all()
    )
    by_role = {r or "unknown": int(c) for r, c in by_role_rows}

    by_volume_rows = (
        db.query(PilotWaitlist.invoice_volume, sa_func.count(PilotWaitlist.id))
        .group_by(PilotWaitlist.invoice_volume)
        .all()
    )
    by_volume = {v or "unknown": int(c) for v, c in by_volume_rows}

    by_status_rows = (
        db.query(PilotWaitlist.status, sa_func.count(PilotWaitlist.id))
        .group_by(PilotWaitlist.status)
        .all()
    )
    by_status = {s: int(c) for s, c in by_status_rows}

    recent = (
        db.query(PilotWaitlist)
        .order_by(PilotWaitlist.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total": total,
        "by_role": by_role,
        "by_volume": by_volume,
        "by_status": by_status,
        "recent": [
            {
                "id": r.id,
                "name": r.name,
                "email": r.email,
                "company": r.company,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in recent
        ],
    }


def export_waitlist_csv(db: Session) -> str:
    entries = db.query(PilotWaitlist).order_by(PilotWaitlist.created_at.desc()).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ID", "Name", "Email", "Company", "Role",
        "Invoice Volume", "Current Workflow", "Interested Features",
        "Country", "Notes", "Status", "Created At", "Updated At",
    ])
    for e in entries:
        writer.writerow([
            e.id, e.name, e.email, e.company or "", e.role or "",
            e.invoice_volume or "", e.current_workflow or "",
            e.interested_features_json or "", e.country or "",
            e.notes or "", e.status,
            e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else "",
            e.updated_at.strftime("%Y-%m-%d %H:%M:%S") if e.updated_at else "",
        ])
    return buf.getvalue()


def record_page_event(
    *,
    event_type: str,
    page: Optional[str] = None,
    metadata_json: Optional[str] = None,
    db: Session,
) -> Optional[PublicPageEvent]:
    from ..config import get_settings as _get_settings

    if not _get_settings().public_analytics_enabled:
        return None
    evt = PublicPageEvent(
        event_type=event_type,
        page=page,
        metadata_json=metadata_json,
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt
