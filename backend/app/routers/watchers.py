from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.background_watcher import BackgroundWatcher
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.watcher_scheduler import WatcherScheduler

logger = logging.getLogger("officepilot.watchers_router")

router = APIRouter(prefix="/api/watchers", tags=["watchers"])


class WatcherCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    source_type: str = Field(..., pattern=r"^(gmail|drive|folder)$")
    config_json: dict = Field(default_factory=dict)
    schedule_minutes: int = Field(default=60, ge=1, le=1440)


class WatcherUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=255)
    config_json: dict | None = None
    schedule_minutes: int | None = Field(None, ge=1, le=1440)
    status: str | None = Field(None, pattern=r"^(active|paused)$")


def _watcher_to_dict(w: BackgroundWatcher) -> dict:
    return {
        "id": w.id,
        "user_id": w.user_id,
        "name": w.name,
        "source_type": w.source_type,
        "config_json": json.loads(w.config_json) if w.config_json else {},
        "schedule_minutes": w.schedule_minutes,
        "last_run_at": w.last_run_at.isoformat() if w.last_run_at else None,
        "status": w.status,
        "created_at": w.created_at.isoformat() if w.created_at else None,
        "updated_at": w.updated_at.isoformat() if w.updated_at else None,
    }


@router.get("/")
def list_watchers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    watchers = (
        db.query(BackgroundWatcher)
        .filter(BackgroundWatcher.user_id == current_user.id)
        .order_by(BackgroundWatcher.created_at.desc())
        .all()
    )
    return {"watchers": [_watcher_to_dict(w) for w in watchers]}


@router.post("/")
def create_watcher(
    body: WatcherCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    watcher = BackgroundWatcher(
        user_id=current_user.id,
        name=body.name,
        source_type=body.source_type,
        config_json=json.dumps(body.config_json),
        schedule_minutes=body.schedule_minutes,
        status="active",
    )
    db.add(watcher)
    db.commit()
    db.refresh(watcher)
    return _watcher_to_dict(watcher)


@router.patch("/{watcher_id}")
def update_watcher(
    watcher_id: int,
    body: WatcherUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    watcher = db.query(BackgroundWatcher).filter(BackgroundWatcher.id == watcher_id).first()
    if not watcher:
        raise HTTPException(status_code=404, detail="Watcher not found")
    if watcher.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if body.name is not None:
        watcher.name = body.name
    if body.config_json is not None:
        watcher.config_json = json.dumps(body.config_json)
    if body.schedule_minutes is not None:
        watcher.schedule_minutes = body.schedule_minutes
    if body.status is not None:
        watcher.status = body.status
    watcher.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(watcher)
    return _watcher_to_dict(watcher)


@router.delete("/{watcher_id}")
def delete_watcher(
    watcher_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    watcher = db.query(BackgroundWatcher).filter(BackgroundWatcher.id == watcher_id).first()
    if not watcher:
        raise HTTPException(status_code=404, detail="Watcher not found")
    if watcher.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db.delete(watcher)
    db.commit()
    return {"deleted": True}


@router.post("/{watcher_id}/run-now")
def run_watcher_now(
    watcher_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    watcher = db.query(BackgroundWatcher).filter(BackgroundWatcher.id == watcher_id).first()
    if not watcher:
        raise HTTPException(status_code=404, detail="Watcher not found")
    if watcher.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    scheduler = WatcherScheduler.get_instance()
    scheduler.run_watcher_now(watcher_id)
    return {"message": f"Watcher '{watcher.name}' triggered", "watcher_id": watcher.id}
