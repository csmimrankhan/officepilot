"""Phase 35 — Desktop update checking, device registration, in-app notifications."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..services.app_update import (
    check_update,
    get_notifications,
    get_release_notes,
    mark_notification_seen,
    register_device,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/app", tags=["app"])


class RegisterDeviceRequest(BaseModel):
    device_id: str
    device_name: str | None = None
    platform: str | None = "windows"
    app_version: str | None = None


class CheckUpdateRequest(BaseModel):
    app_version: str
    platform: str = "windows"
    channel: str = "stable"
    device_id: str | None = None


@router.post("/register-device")
def register_device_endpoint(
    body: RegisterDeviceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = register_device(
        db,
        user_id=current_user.id,
        device_id=body.device_id,
        device_name=body.device_name,
        platform=body.platform,
        app_version=body.app_version,
    )
    return {
        "ok": True,
        "device_id": device.device_id,
        "last_seen_at": device.last_seen_at.isoformat(),
    }


@router.post("/check-update")
def check_update_endpoint(
    body: CheckUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.device_id:
        register_device(
            db,
            user_id=current_user.id,
            device_id=body.device_id,
            platform=body.platform,
            app_version=body.app_version,
        )
    result = check_update(db, body.app_version, body.platform, body.channel)
    return result


@router.get("/releases/latest")
def latest_release(
    platform: str = "windows",
    channel: str = "stable",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    release = get_release_notes(db, platform, channel)
    if not release:
        return {"release": None, "message": "No releases found"}
    return {
        "release": {
            "version": release.version,
            "platform": release.platform,
            "channel": release.channel,
            "download_url": release.download_url,
            "release_notes": release.release_notes,
            "minimum_required_version": release.minimum_required_version,
            "is_critical": release.is_critical,
            "created_at": release.created_at.isoformat(),
        }
    }


@router.get("/updater/windows/stable")
def tauri_updater_endpoint(
    db: Session = Depends(get_db),
):
    """Tauri-compatible updater manifest endpoint."""
    logger.info("Tauri updater check requested")
    release = get_release_notes(db, "windows", "stable")
    if not release:
        return {
            "version": "0.0.0",
            "notes": "",
            "pub_date": "",
            "platforms": {},
        }
    return {
        "version": release.version,
        "notes": release.release_notes or "",
        "pub_date": release.pub_date or release.created_at.isoformat(),
        "platforms": {
            release.target or "windows-x86_64": {
                "signature": release.updater_signature or "",
                "url": release.updater_artifact_url or release.download_url,
            }
        },
    }


@router.get("/notifications")
def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifications = get_notifications(db, current_user.id)
    return {"notifications": notifications}


@router.post("/notifications/{notification_id}/seen")
def mark_seen(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok = mark_notification_seen(db, notification_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"ok": True}
