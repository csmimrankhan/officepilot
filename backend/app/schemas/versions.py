"""Phase 10 — Pydantic schemas for version history, file snapshots, and restore.

These mirror the response models defined in :mod:`app.routers.versions`.
Most clients (frontend) use the response models returned by the router
directly. This module exists for clients that want to validate payloads
*before* sending (e.g. test fixtures, programmatic API clients)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class VersionSummary(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    version_number: int
    change_summary: Optional[str] = None
    source_action: str
    created_by: str
    restored_from_version: Optional[int] = None
    created_at: Optional[str] = None


class VersionRead(VersionSummary):
    snapshot: dict = Field(default_factory=dict)


class VersionDiff(BaseModel):
    field: str
    before: Any
    after: Any


class VersionDiffRead(BaseModel):
    entity_type: str
    entity_id: str
    from_version: int
    to_version: int
    diffs: list[VersionDiff] = Field(default_factory=list)


class RestoreRequest(BaseModel):
    actor: str = "user"
    reason: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Free-text reason for the restore. Recorded in the audit log.",
    )


class FileSnapshotRead(BaseModel):
    id: int
    file_type: str
    original_path: str
    snapshot_path: str
    action_type: str
    file_hash_before: Optional[str] = None
    file_hash_after: Optional[str] = None
    size_bytes: Optional[int] = None
    created_by: str
    created_at: Optional[str] = None
    restored_at: Optional[str] = None
    restore_count: int = 0
    restore_status: str = "active"
    notes: Optional[str] = None


class WorkflowVersionRead(BaseModel):
    id: int
    workflow_id: int
    workflow_name: str
    version_number: int
    workflow: dict = Field(default_factory=dict)
    change_summary: Optional[str] = None
    source_action: str
    created_by: str
    restored_from_version: Optional[int] = None
    created_at: Optional[str] = None


class RestoreLogRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    target_id: Optional[str] = None
    restored_from_version: Optional[int] = None
    restored_to_version: Optional[int] = None
    reason: Optional[str] = None
    restored_by: str
    restored_at: Optional[str] = None
