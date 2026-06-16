"""Phase 19 — Pilot feedback service."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models.pilot_feedback import PilotFeedback

logger = logging.getLogger("officepilot.feedback")

FEEDBACK_TYPES = [
    "bug",
    "confusing_ux",
    "extraction_mistake",
    "missing_feature",
    "performance_issue",
    "security_concern",
    "general_feedback",
]

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]
FEEDBACK_STATUSES = ["open", "in_review", "acknowledged", "resolved", "closed"]


def create_feedback(
    db: Session,
    user_id: int,
    feedback_type: str,
    title: str,
    message: str,
    page_url: str | None = None,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
    severity: str = "medium",
) -> dict[str, Any]:
    if feedback_type not in FEEDBACK_TYPES:
        raise ValueError(f"Invalid feedback type: {feedback_type}. Must be one of {FEEDBACK_TYPES}")
    if severity not in SEVERITY_LEVELS:
        raise ValueError(f"Invalid severity: {severity}. Must be one of {SEVERITY_LEVELS}")

    fb = PilotFeedback(
        user_id=user_id,
        feedback_type=feedback_type,
        title=title,
        message=message,
        page_url=page_url,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        severity=severity,
        status="open",
    )
    db.add(fb)
    db.flush()
    db.commit()
    return _feedback_to_dict(fb)


def get_feedback(db: Session, feedback_id: int, user_id: int | None = None) -> dict[str, Any] | None:
    fb = db.query(PilotFeedback).filter(PilotFeedback.id == feedback_id).first()
    if fb is None:
        return None
    if user_id is not None and fb.user_id != user_id:
        return None
    return _feedback_to_dict(fb)


def list_feedback(
    db: Session,
    user_id: int | None = None,
    status_filter: str | None = None,
    feedback_type_filter: str | None = None,
    limit: int = 100,
    skip: int = 0,
) -> list[dict[str, Any]]:
    q = db.query(PilotFeedback)
    if user_id is not None:
        q = q.filter(PilotFeedback.user_id == user_id)
    if status_filter:
        q = q.filter(PilotFeedback.status == status_filter)
    if feedback_type_filter:
        q = q.filter(PilotFeedback.feedback_type == feedback_type_filter)
    q = q.order_by(PilotFeedback.created_at.desc()).offset(skip).limit(limit)
    return [_feedback_to_dict(fb) for fb in q.all()]


def update_feedback(
    db: Session,
    feedback_id: int,
    user_id: int | None = None,
    status: str | None = None,
    severity: str | None = None,
) -> dict[str, Any] | None:
    fb = db.query(PilotFeedback).filter(PilotFeedback.id == feedback_id).first()
    if fb is None:
        return None
    if user_id is not None and fb.user_id != user_id:
        return None
    if status is not None:
        if status not in FEEDBACK_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        fb.status = status
    if severity is not None:
        if severity not in SEVERITY_LEVELS:
            raise ValueError(f"Invalid severity: {severity}")
        fb.severity = severity
    fb.updated_at = datetime.utcnow()
    db.flush()
    db.commit()
    return _feedback_to_dict(fb)


def _feedback_to_dict(fb: PilotFeedback) -> dict[str, Any]:
    return {
        "id": fb.id,
        "user_id": fb.user_id,
        "feedback_type": fb.feedback_type,
        "title": fb.title,
        "message": fb.message,
        "page_url": fb.page_url,
        "related_entity_type": fb.related_entity_type,
        "related_entity_id": fb.related_entity_id,
        "severity": fb.severity,
        "status": fb.status,
        "created_at": fb.created_at.isoformat(),
        "updated_at": fb.updated_at.isoformat(),
    }
