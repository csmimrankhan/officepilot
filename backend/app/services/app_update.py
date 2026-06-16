"""Phase 35 — App update checking, device registration, license, feature gates."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.app_release import AppRelease
from ..models.user_device import UserDevice
from ..models.subscription import Subscription
from ..models.feature_entitlement import FeatureEntitlement
from ..models.in_app_notification import InAppNotification

logger = logging.getLogger("officepilot.app_update")

DEFAULT_FEATURES: dict[str, dict[str, Any]] = {
    "free": {
        "excel_automation": {"enabled": True, "limit_value": None},
        "browser_export": {"enabled": False, "limit_value": None},
        "gmail_readonly": {"enabled": True, "limit_value": None},
        "workflow_recorder": {"enabled": True, "limit_value": None},
        "advanced_skills": {"enabled": False, "limit_value": 5},
        "voice_shortcuts": {"enabled": False, "limit_value": None},
        "monthly_runs_limit": {"enabled": True, "limit_value": 50},
        "skills_limit": {"enabled": True, "limit_value": 5},
    },
    "pro": {
        "excel_automation": {"enabled": True, "limit_value": None},
        "browser_export": {"enabled": True, "limit_value": None},
        "gmail_readonly": {"enabled": True, "limit_value": None},
        "workflow_recorder": {"enabled": True, "limit_value": None},
        "advanced_skills": {"enabled": True, "limit_value": None},
        "voice_shortcuts": {"enabled": True, "limit_value": None},
        "monthly_runs_limit": {"enabled": True, "limit_value": 1000},
        "skills_limit": {"enabled": True, "limit_value": 50},
    },
    "trial": {
        "excel_automation": {"enabled": True, "limit_value": None},
        "browser_export": {"enabled": True, "limit_value": None},
        "gmail_readonly": {"enabled": True, "limit_value": None},
        "workflow_recorder": {"enabled": True, "limit_value": None},
        "advanced_skills": {"enabled": True, "limit_value": None},
        "voice_shortcuts": {"enabled": True, "limit_value": None},
        "monthly_runs_limit": {"enabled": True, "limit_value": 100},
        "skills_limit": {"enabled": True, "limit_value": 20},
    },
}


def register_device(
    db: Session,
    user_id: int,
    device_id: str,
    device_name: str | None = None,
    platform: str | None = None,
    app_version: str | None = None,
) -> UserDevice:
    existing = db.query(UserDevice).filter(
        UserDevice.user_id == user_id,
        UserDevice.device_id == device_id,
    ).first()
    if existing:
        existing.last_seen_at = datetime.utcnow()
        if app_version:
            existing.app_version = app_version
        if device_name:
            existing.device_name = device_name
        if platform:
            existing.platform = platform
        db.commit()
        db.refresh(existing)
        return existing
    device = UserDevice(
        user_id=user_id,
        device_id=device_id,
        device_name=device_name,
        platform=platform,
        app_version=app_version,
        last_seen_at=datetime.utcnow(),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def check_update(
    db: Session,
    app_version: str,
    platform: str = "windows",
    channel: str = "stable",
) -> dict:
    release = db.query(AppRelease).filter(
        AppRelease.platform == platform,
        AppRelease.channel == channel,
    ).order_by(AppRelease.created_at.desc()).first()
    if not release:
        return {
            "latest_version": app_version,
            "update_available": False,
            "critical": False,
            "download_url": None,
            "release_notes": None,
            "minimum_required_version": None,
        }
    latest = release.version
    is_newer = _version_compare(latest, app_version) > 0
    if not is_newer:
        return {
            "latest_version": latest,
            "update_available": False,
            "critical": False,
            "download_url": release.download_url,
            "release_notes": release.release_notes,
            "minimum_required_version": release.minimum_required_version,
        }
    if release.is_critical:
        return {
            "latest_version": latest,
            "update_available": True,
            "critical": True,
            "blocked": True,
            "message": "A required security update is available.",
            "download_url": release.download_url,
            "release_notes": release.release_notes,
            "minimum_required_version": release.minimum_required_version,
        }
    return {
        "latest_version": latest,
        "update_available": True,
        "critical": False,
        "download_url": release.download_url,
        "release_notes": release.release_notes,
        "minimum_required_version": release.minimum_required_version,
    }


def get_release_notes(db: Session, platform: str = "windows", channel: str = "stable") -> AppRelease | None:
    return db.query(AppRelease).filter(
        AppRelease.platform == platform,
        AppRelease.channel == channel,
    ).order_by(AppRelease.created_at.desc()).first()


def get_or_create_subscription(db: Session, user_id: int) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if not sub:
        sub = Subscription(
            user_id=user_id,
            provider="manual",
            plan="trial",
            status="active",
            trial_ends_at=datetime.utcnow() + timedelta(days=14),
            current_period_end=datetime.utcnow() + timedelta(days=14),
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


def get_license_status(db: Session, user_id: int) -> dict:
    settings = get_settings()
    if settings.allow_billing_bypass:
        return {
            "plan": "trial",
            "status": "active",
            "trial_ends_at": (datetime.utcnow() + timedelta(days=14)).isoformat(),
            "features": _build_features("trial"),
        }
    sub = get_or_create_subscription(db, user_id)
    now = datetime.utcnow()
    if sub.status == "active" and sub.current_period_end and sub.current_period_end > now:
        features = _build_features(sub.plan)
        trial_ends = sub.trial_ends_at.isoformat() if sub.trial_ends_at else None
        return {
            "plan": sub.plan,
            "status": sub.status,
            "trial_ends_at": trial_ends,
            "features": features,
        }
    return {
        "plan": sub.plan if sub else "trial",
        "status": "expired",
        "features": {
            "excel_automation": True,
            "browser_export": False,
            "gmail_readonly": False,
            "workflow_recorder": False,
            "advanced_skills": False,
            "voice_shortcuts": False,
            "monthly_runs_limit": 0,
            "skills_limit": 0,
        },
        "upgrade_required": True,
    }


def _build_features(plan: str) -> dict:
    plan_features = DEFAULT_FEATURES.get(plan, DEFAULT_FEATURES["free"])
    result = {}
    for key, cfg in plan_features.items():
        result[key] = cfg["limit_value"] if cfg["enabled"] and cfg["limit_value"] is not None else cfg["enabled"]
    return result


def require_feature(db: Session, user_id: int, feature_key: str) -> bool:
    settings = get_settings()
    if settings.allow_billing_bypass:
        return True
    status = get_license_status(db, user_id)
    if status["status"] == "expired":
        return False
    features = status.get("features", {})
    return bool(features.get(feature_key, False))


def get_plans() -> list[dict]:
    return [
        {
            "id": "free",
            "name": "Free",
            "price": 0,
            "features": _build_features("free"),
        },
        {
            "id": "pro",
            "name": "Pro",
            "price": 29,
            "features": _build_features("pro"),
        },
        {
            "id": "trial",
            "name": "Trial",
            "price": 0,
            "features": _build_features("trial"),
        },
    ]


def get_notifications(db: Session, user_id: int) -> list[dict]:
    rows = db.query(InAppNotification).filter(
        InAppNotification.user_id == user_id,
    ).order_by(InAppNotification.created_at.desc()).limit(50).all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "action_url": n.action_url,
            "seen": n.seen_at is not None,
            "seen_at": n.seen_at.isoformat() if n.seen_at else None,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]


def mark_notification_seen(db: Session, notification_id: int, user_id: int) -> bool:
    n = db.query(InAppNotification).filter(
        InAppNotification.id == notification_id,
        InAppNotification.user_id == user_id,
    ).first()
    if not n:
        return False
    n.seen_at = datetime.utcnow()
    db.commit()
    return True


def _version_compare(v1: str, v2: str) -> int:
    parts1 = [int(x) for x in v1.split(".")]
    parts2 = [int(x) for x in v2.split(".")]
    max_len = max(len(parts1), len(parts2))
    parts1 += [0] * (max_len - len(parts1))
    parts2 += [0] * (max_len - len(parts2))
    for a, b in zip(parts1, parts2):
        if a > b:
            return 1
        if a < b:
            return -1
    return 0
