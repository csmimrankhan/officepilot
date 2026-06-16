"""Phase 16B — Pydantic schemas for safety, permissions, audit, readiness, backup."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Safety Policy ────────────────────────────────────────────────────


class SafetyPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cloud_ai_allowed: bool = False
    browser_automation_enabled: bool = False
    screen_control_enabled: bool = False
    workflow_recording_enabled: bool = False
    accounting_sync_enabled: bool = False
    voice_enabled: bool = False
    screenshots_enabled: bool = False
    ocr_enabled: bool = False
    require_approval_for_write: bool = True
    require_snapshot_for_file_changes: bool = True
    block_unknown_apps: bool = True
    block_unknown_domains: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SafetyPolicyUpdate(BaseModel):
    cloud_ai_allowed: Optional[bool] = None
    browser_automation_enabled: Optional[bool] = None
    screen_control_enabled: Optional[bool] = None
    workflow_recording_enabled: Optional[bool] = None
    accounting_sync_enabled: Optional[bool] = None
    voice_enabled: Optional[bool] = None
    screenshots_enabled: Optional[bool] = None
    ocr_enabled: Optional[bool] = None
    require_approval_for_write: Optional[bool] = None
    require_snapshot_for_file_changes: Optional[bool] = None
    block_unknown_apps: Optional[bool] = None
    block_unknown_domains: Optional[bool] = None


# ── Role Permissions ─────────────────────────────────────────────────


class PermissionEntry(BaseModel):
    permission_name: str
    enabled: bool = True


class RolePermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    permission_name: str
    enabled: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RolePermissionUpdateRequest(BaseModel):
    entries: list[PermissionEntry] = Field(default_factory=list)


class MyPermissionsRead(BaseModel):
    role: str = "staff"
    permissions: list[str] = Field(default_factory=list)


# ── Audit Exports ────────────────────────────────────────────────────


class AuditExportRequest(BaseModel):
    export_type: str = "json"
    date_from: str = ""
    date_to: str = ""
    log_types: list[str] = Field(default_factory=list)


class AuditExportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    export_type: str = "json"
    date_from: str = ""
    date_to: str = ""
    log_types_json: str = "[]"
    status: str = "pending"
    file_path: str = ""
    created_by: str = "user"
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: str = ""


class AuditExportStatusRead(BaseModel):
    id: int
    status: str
    file_path: str = ""
    error_message: str = ""
    completed_at: Optional[str] = None


# ── Kill Switch ──────────────────────────────────────────────────────


class KillSwitchResponse(BaseModel):
    active: bool
    disabled_services: list[str] = Field(default_factory=list)
    reason: str = ""


class AutomationStatusRead(BaseModel):
    kill_switch_active: bool = False
    browser_automation_enabled: bool = False
    screen_control_enabled: bool = False
    workflow_recording_enabled: bool = False
    accounting_sync_enabled: bool = False
    browser_automation_blocked: bool = False
    screen_control_blocked: bool = False
    workflow_recording_blocked: bool = False
    accounting_sync_blocked: bool = False


# ── System Readiness ─────────────────────────────────────────────────


class ReadinessItem(BaseModel):
    name: str
    status: str  # green | yellow | red
    message: str = ""


class ReadinessReport(BaseModel):
    overall: str  # green | yellow | red
    items: list[ReadinessItem] = Field(default_factory=list)


# ── Backup Status ────────────────────────────────────────────────────


class BackupStatusRead(BaseModel):
    database_path: str = ""
    snapshot_path: str = ""
    last_backup_time: Optional[str] = None
    last_restore_test_status: str = "unknown"
    disk_free_gb: float = 0.0
    disk_total_gb: float = 0.0
    disk_warning: bool = False


class BackupRunResponse(BaseModel):
    status: str
    message: str = ""
    file_path: str = ""


class RestoreTestResponse(BaseModel):
    status: str
    message: str = ""
