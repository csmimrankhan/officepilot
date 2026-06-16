"""Phase 13 — Pydantic schemas for accounting sync API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AccountingConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    display_name: str
    company_name: str
    tenant_id: Optional[str] = None
    realm_id: Optional[str] = None
    status: str
    environment: str
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    created_at: datetime


class AccountingConnectionStatus(BaseModel):
    quickbooks_configured: bool = False
    quickbooks_connected: bool = False
    quickbooks_connection: Optional[AccountingConnectionRead] = None
    xero_configured: bool = False
    xero_connected: bool = False
    xero_connection: Optional[AccountingConnectionRead] = None
    sync_enabled: bool = False


class AccountingFieldMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    local_field: str
    external_field: str
    mapping_config_json: dict = Field(default_factory=dict)
    enabled: bool


class AccountingFieldMappingUpdate(BaseModel):
    mappings: list[dict[str, Any]] = Field(default_factory=list)


class AccountingVendorMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    local_vendor_name: str
    external_contact_id: str
    external_contact_name: str
    confidence_score: float


class AccountingVendorSearchResult(BaseModel):
    id: str
    name: str
    provider: str


class AccountingVendorMapRequest(BaseModel):
    provider: str
    local_vendor_name: str
    external_contact_id: str
    external_contact_name: str = ""
    confidence_score: float = 1.0


class AccountingCategoryRead(BaseModel):
    id: str
    name: str
    provider: str


class AccountingCategoryMapRequest(BaseModel):
    provider: str
    local_category: str
    external_account_id: str
    external_account_name: str = ""
    external_tax_code: str = ""


class AccountingCategoryMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    local_category: str
    external_account_id: str
    external_account_name: str
    external_tax_code: str
    enabled: bool


class AccountingPreviewField(BaseModel):
    local_field: str
    local_value: str = ""
    external_field: str = ""
    external_value: str = ""
    mapped: bool = False


class AccountingSyncPreviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    invoice_id: int
    preview_json: dict = Field(default_factory=dict)
    warnings_json: list = Field(default_factory=list)
    blockers_json: list = Field(default_factory=list)
    risk_level: str = "medium"
    approval_required: bool = True
    status: str = "pending"
    created_at: datetime
    updated_at: Optional[datetime] = None


class AccountingSyncPreviewResponse(BaseModel):
    preview_id: int
    provider: str
    invoice_id: int
    preview: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    risk_level: str
    approval_required: bool
    eligible: bool


class AccountingSyncLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    invoice_id: int
    connection_id: int
    preview_id: Optional[int] = None
    external_record_id: Optional[str] = None
    external_record_type: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AccountingSyncLogDetail(BaseModel):
    id: int
    provider: str
    invoice_id: int
    connection_id: int
    preview_id: Optional[int] = None
    external_record_id: Optional[str] = None
    external_record_type: str
    request_json_redacted: dict = Field(default_factory=dict)
    response_json_redacted: dict = Field(default_factory=dict)
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AccountingValidationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    invoice_id: int
    sync_log_id: int
    external_record_id: str
    source_json: dict = Field(default_factory=dict)
    accounting_json: dict = Field(default_factory=dict)
    differences_json: list = Field(default_factory=list)
    validation_status: str
    created_at: datetime


class AccountingValidationResponse(BaseModel):
    validation_id: int
    provider: str
    invoice_id: int
    sync_log_id: int
    external_record_id: str
    differences: list[dict] = Field(default_factory=list)
    validation_status: str


class AccountingVoicePreviewRequest(BaseModel):
    provider: str
    intent: str
    invoice_id: Optional[int] = None
    actor: str = "voice"


class AccountingVoicePreviewResponse(BaseModel):
    provider: str
    intent: str
    preview_id: Optional[int] = None
    preview: Optional[AccountingSyncPreviewRead] = None
    blocked: bool = False
    message: str = ""


class AccountingApprovalRequest(BaseModel):
    actor: str = "user"
    reason: str = "Reviewed and approved for accounting sync."


class AccountingRejectRequest(BaseModel):
    actor: str = "user"
    reason: str = "Rejected accounting sync."


class AccountingConnectResponse(BaseModel):
    authorization_url: str
    state: str


class AccountingDisconnectResponse(BaseModel):
    disconnected: bool
    provider: str
    account_id: Optional[int] = None


class AccountingSyncResult(BaseModel):
    sync_log_id: int
    provider: str
    invoice_id: int
    external_record_id: Optional[str] = None
    external_record_type: str
    status: str
    error_message: Optional[str] = None
