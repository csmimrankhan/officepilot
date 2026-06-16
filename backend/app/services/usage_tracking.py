"""Phase 19 — Local usage tracking service."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.usage_event import UsageEvent

logger = logging.getLogger("officepilot.usage_tracking")


def is_tracking_enabled() -> bool:
    return get_settings().usage_tracking_enabled


def record_event(
    db: Session,
    user_id: int,
    event_type: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    metadata: dict | None = None,
) -> dict[str, Any] | None:
    if not is_tracking_enabled():
        return None
    ev = UsageEvent(
        user_id=user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(ev)
    db.flush()
    db.commit()
    return {
        "id": ev.id,
        "user_id": ev.user_id,
        "event_type": ev.event_type,
        "created_at": ev.created_at.isoformat(),
    }


def get_usage_summary(
    db: Session,
    user_id: int | None = None,
    days: int = 30,
) -> dict[str, Any]:
    if not is_tracking_enabled():
        return {"tracking_enabled": False, "events_total": 0, "by_type": {}, "errors": 0}

    q = db.query(UsageEvent)
    if user_id is not None:
        q = q.filter(UsageEvent.user_id == user_id)

    cutoff = datetime.utcnow().timestamp() - days * 86400
    cutoff_dt = datetime.utcfromtimestamp(cutoff)
    q = q.filter(UsageEvent.created_at >= cutoff_dt)

    events = q.all()
    by_type: dict[str, int] = {}
    errors = 0
    top_features: list[dict[str, Any]] = []

    type_counts: Counter = Counter()
    for ev in events:
        type_counts[ev.event_type] += 1
        if "error" in ev.event_type.lower():
            errors += 1

    by_type = dict(type_counts.most_common())
    top_features = [
        {"event_type": evt, "count": cnt}
        for evt, cnt in type_counts.most_common(10)
    ]

    return {
        "tracking_enabled": True,
        "events_total": len(events),
        "days": days,
        "by_type": by_type,
        "top_features": top_features,
        "error_count": errors,
    }


def list_usage_events(
    db: Session,
    user_id: int | None = None,
    event_type_filter: str | None = None,
    limit: int = 100,
    skip: int = 0,
) -> list[dict[str, Any]]:
    if not is_tracking_enabled():
        return []
    q = db.query(UsageEvent)
    if user_id is not None:
        q = q.filter(UsageEvent.user_id == user_id)
    if event_type_filter:
        q = q.filter(UsageEvent.event_type == event_type_filter)
    q = q.order_by(UsageEvent.created_at.desc()).offset(skip).limit(limit)
    return [
        {
            "id": ev.id,
            "user_id": ev.user_id,
            "event_type": ev.event_type,
            "entity_type": ev.entity_type,
            "entity_id": ev.entity_id,
            "metadata": json.loads(ev.metadata_json) if ev.metadata_json else None,
            "created_at": ev.created_at.isoformat(),
        }
        for ev in q.all()
    ]
