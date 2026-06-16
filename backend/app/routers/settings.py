"""Settings HTTP API (Phase 3: folder rules + general key/value settings)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.audit_log import AuditLog
from ..schemas.settings import FolderRulesAuditEntry, FolderRulesRead, FolderRulesUpdate
from ..services import settings as settings_svc
from ..services import versioning as versioning_svc
from ..services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/folder-rules", response_model=FolderRulesRead)
def get_folder_rules(db: Session = Depends(get_db)):
    rules = settings_svc.get_setting(db, "folder_rules", default=settings_svc.DEFAULT_FOLDER_RULES)
    return FolderRulesRead(**rules)


@router.patch("/folder-rules", response_model=FolderRulesRead)
def update_folder_rules(
    payload: FolderRulesUpdate,
    actor: str = Query("user"),
    db: Session = Depends(get_db),
):
    before = settings_svc.get_setting(db, "folder_rules", default=settings_svc.DEFAULT_FOLDER_RULES)
    # Merge: only the fields explicitly set in the payload are updated; the
    # rest stay at their current value.
    patch = payload.model_dump(exclude_unset=True)
    new = {**before, **patch}
    settings_svc.set_setting(db, "folder_rules", new)
    diff = settings_svc.diff_dicts(before, new)
    log_action(
        db,
        actor=actor,
        action="settings.folder_rules.update",
        entity_type="setting",
        entity_id=None,
        details="Updated folder rules",
        before_data=before,
        after_data=new,
    )
    # Phase 10: snapshot the new folder rules in entity_versions
    # so the user can review / restore prior rule sets from the
    # Version History tab. ``entity_id`` is a stable key
    # ("folder_rules") so versions accumulate across updates.
    versioning_svc.capture_version(
        db,
        entity_type="settings",
        entity_id="folder_rules",
        snapshot=new,
        source_action="user.settings",
        created_by=actor,
        change_summary=(
            f"Folder rules updated ({len(diff)} field(s))"
            if diff
            else "Folder rules updated (no field changes detected)"
        ),
    )
    db.commit()
    return FolderRulesRead(**new)


@router.get("/folder-rules/audit", response_model=list[FolderRulesAuditEntry])
def folder_rules_audit(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return a flat timeline of folder-rule changes derived from the
    general audit log."""
    q = (
        db.query(AuditLog)
        .filter(AuditLog.action == "settings.folder_rules.update")
        .order_by(AuditLog.id.desc())
        .limit(limit)
    )
    out: list[FolderRulesAuditEntry] = []
    for r in q.all():
        try:
            out.append(
                FolderRulesAuditEntry(
                    id=r.id,
                    actor=r.actor,
                    created_at=r.timestamp,
                    before=FolderRulesRead(**(r.before_data_json or {})) if r.before_data_json else None,
                    after=FolderRulesRead(**(r.after_data_json or {})) if r.after_data_json else None,
                )
            )
        except ValidationError:
            # Skip rows that don't validate (older shapes or external
            # tampering). Don't break the endpoint.
            continue
    return out
