"""Phase 13 — accounting sync HTTP API (QuickBooks + Xero).

Endpoints (all under ``/api/accounting``):

* ``GET    /status``
* ``GET    /connections``
* ``GET    /quickbooks/connect``
* ``GET    /quickbooks/callback``
* ``GET    /xero/connect``
* ``GET    /xero/callback``
* ``POST   /connections/{id}/disconnect``
* ``GET    /mappings``
* ``PATCH  /mappings``
* ``GET    /vendors/search``
* ``POST   /vendors/map``
* ``GET    /categories``
* ``POST   /categories/map``
* ``POST   /invoices/{invoice_id}/preview-sync``
* ``GET    /previews/{preview_id}``
* ``POST   /previews/{preview_id}/approve``
* ``POST   /previews/{preview_id}/reject``
* ``POST   /previews/{preview_id}/sync``
* ``POST   /sync-logs/{sync_log_id}/validate``
* ``GET    /validations/{invoice_id}``
* ``GET    /failed-syncs``
* ``GET    /sync-logs``
* ``POST   /voice/preview``
* ``POST   /voice/approve-sync``
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.invoice import Invoice
from ..models.accounting_connection import AccountingConnection
from ..models.accounting_sync_preview import AccountingSyncPreview
from ..models.accounting_sync_log import AccountingSyncLog
from ..models.accounting_entry_validation import AccountingEntryValidation
from ..models.accounting_vendor_mapping import AccountingVendorMapping
from ..models.accounting_category_mapping import AccountingCategoryMapping
from ..models.accounting_field_mapping import AccountingFieldMapping
from ..schemas.accounting import (
    AccountingApprovalRequest,
    AccountingCategoryMapRequest,
    AccountingConnectResponse,
    AccountingConnectionRead,
    AccountingConnectionStatus,
    AccountingDisconnectResponse,
    AccountingRejectRequest,
    AccountingSyncLogDetail,
    AccountingSyncLogRead,
    AccountingSyncPreviewRead,
    AccountingSyncPreviewResponse,
    AccountingSyncResult,
    AccountingValidationRead,
    AccountingValidationResponse,
    AccountingVendorMapRequest,
    AccountingVendorSearchResult,
    AccountingVoicePreviewRequest,
    AccountingVoicePreviewResponse,
    AccountingCategoryRead,
    AccountingCategoryMappingRead,
    AccountingVendorMappingRead,
    AccountingFieldMappingRead,
    AccountingFieldMappingUpdate,
)
from ..services.accounting import (
    build_sync_preview,
    check_connection_active,
    check_duplicate_sync,
    check_invoice_eligibility,
    check_vendor_mapping,
    execute_sync,
    quickbooks_authorization_url,
    quickbooks_exchange_code,
    xero_authorization_url,
    xero_exchange_code,
    validate_sync_result,
    voice_intent_preview,
    encrypt_token,
    decrypt_token,
    AccountingOAuthError,
)
from ..services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


def _get_active_connection(db: Session, provider: str) -> Optional[AccountingConnection]:
    return (
        db.query(AccountingConnection)
        .filter(
            AccountingConnection.provider == provider,
            AccountingConnection.status == "active",
        )
        .order_by(AccountingConnection.id.desc())
        .first()
    )


def _connection_to_read(conn: AccountingConnection) -> dict:
    return {
        "id": conn.id,
        "provider": conn.provider,
        "display_name": conn.display_name,
        "company_name": conn.company_name,
        "tenant_id": conn.tenant_id,
        "realm_id": conn.realm_id,
        "status": conn.status,
        "environment": conn.environment,
        "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
        "disconnected_at": conn.disconnected_at.isoformat() if conn.disconnected_at else None,
        "created_at": conn.created_at.isoformat() if conn.created_at else None,
    }


@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    settings = get_settings()
    qb_conn = _get_active_connection(db, "quickbooks")
    xero_conn = _get_active_connection(db, "xero")
    return {
        "quickbooks_configured": bool(settings.quickbooks_client_id),
        "quickbooks_connected": qb_conn is not None,
        "quickbooks_connection": _connection_to_read(qb_conn) if qb_conn else None,
        "quickbooks_env": settings.quickbooks_env,
        "xero_configured": bool(settings.xero_client_id),
        "xero_connected": xero_conn is not None,
        "xero_connection": _connection_to_read(xero_conn) if xero_conn else None,
        "xero_env": settings.xero_env,
        "sync_enabled": settings.accounting_sync_enabled,
        "draft_only": settings.accounting_draft_only,
        "block_duplicates": settings.accounting_block_duplicates,
    }


@router.get("/connections")
def list_connections(db: Session = Depends(get_db)):
    rows = db.query(AccountingConnection).order_by(AccountingConnection.id.desc()).all()
    return [_connection_to_read(r) for r in rows]


@router.get("/quickbooks/connect")
def quickbooks_connect(db: Session = Depends(get_db)):
    settings = get_settings()
    result = quickbooks_authorization_url(settings)
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    log_action(
        db,
        actor="user",
        action="accounting.quickbooks.oauth.start",
        entity_type="accounting_connection",
        entity_id=None,
        details="Started QuickBooks OAuth flow.",
    )
    db.commit()
    return AccountingConnectResponse(
        authorization_url=result["authorization_url"],
        state=result["state"],
    )


@router.get("/quickbooks/callback")
def quickbooks_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    realm_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if error:
        log_action(db, actor="system", action="accounting.quickbooks.oauth.error", entity_type="accounting_connection", entity_id=None, details=f"OAuth error: {error}")
        db.commit()
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    settings = get_settings()
    try:
        token_data = quickbooks_exchange_code(settings, code, settings.quickbooks_redirect_uri)
    except AccountingOAuthError as exc:
        log_action(db, actor="user", action="accounting.quickbooks.oauth.error", entity_type="accounting_connection", entity_id=None, details=str(exc))
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc))
    qb_realm = realm_id or token_data.get("realm_id", "")
    company_name = f"QuickBooks ({qb_realm[:12]}...)" if qb_realm else "QuickBooks Sandbox"
    conn = AccountingConnection(
        provider="quickbooks",
        display_name="QuickBooks",
        company_name=company_name,
        realm_id=qb_realm,
        access_token_encrypted=encrypt_token(token_data.get("access_token", "")),
        refresh_token_encrypted=encrypt_token(token_data.get("refresh_token", "")),
        scopes_json=json.dumps(settings.quickbooks_scopes),
        status="active",
        environment=settings.quickbooks_env,
    )
    db.add(conn)
    db.flush()
    log_action(
        db,
        actor="user",
        action="accounting.quickbooks.oauth.connected",
        entity_type="accounting_connection",
        entity_id=conn.id,
        details=f"Connected QuickBooks (realm={qb_realm[:20]}...)",
        after_data={"provider": "quickbooks", "realm_id": qb_realm, "environment": settings.quickbooks_env},
    )
    db.commit()
    origin = (settings.cors_origin_list or ["http://127.0.0.1:5173"])[0]
    return RedirectResponse(url=f"{origin}/accounting/integrations?quickbooks=connected", status_code=302)


@router.get("/xero/connect")
def xero_connect(db: Session = Depends(get_db)):
    settings = get_settings()
    result = xero_authorization_url(settings)
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    log_action(
        db,
        actor="user",
        action="accounting.xero.oauth.start",
        entity_type="accounting_connection",
        entity_id=None,
        details="Started Xero OAuth flow.",
    )
    db.commit()
    return AccountingConnectResponse(
        authorization_url=result["authorization_url"],
        state=result["state"],
    )


@router.get("/xero/callback")
def xero_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if error:
        log_action(db, actor="system", action="accounting.xero.oauth.error", entity_type="accounting_connection", entity_id=None, details=f"OAuth error: {error}")
        db.commit()
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    settings = get_settings()
    try:
        token_data = xero_exchange_code(settings, code, settings.xero_redirect_uri)
    except AccountingOAuthError as exc:
        log_action(db, actor="user", action="accounting.xero.oauth.error", entity_type="accounting_connection", entity_id=None, details=str(exc))
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc))
    conn = AccountingConnection(
        provider="xero",
        display_name="Xero",
        company_name="Xero Demo Company",
        tenant_id=token_data.get("tenant_id", ""),
        access_token_encrypted=encrypt_token(token_data.get("access_token", "")),
        refresh_token_encrypted=encrypt_token(token_data.get("refresh_token", "")),
        scopes_json=json.dumps(settings.xero_scopes),
        status="active",
        environment=settings.xero_env,
    )
    db.add(conn)
    db.flush()
    log_action(
        db,
        actor="user",
        action="accounting.xero.oauth.connected",
        entity_type="accounting_connection",
        entity_id=conn.id,
        details=f"Connected Xero (tenant={token_data.get('tenant_id', '')[:20]}...)",
        after_data={"provider": "xero", "environment": settings.xero_env},
    )
    db.commit()
    origin = (settings.cors_origin_list or ["http://127.0.0.1:5173"])[0]
    return RedirectResponse(url=f"{origin}/accounting/integrations?xero=connected", status_code=302)


@router.post("/connections/{connection_id}/disconnect")
def disconnect_connection(connection_id: int, db: Session = Depends(get_db)):
    conn = db.get(AccountingConnection, connection_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    conn.status = "disconnected"
    conn.disconnected_at = datetime.utcnow()
    log_action(
        db,
        actor="user",
        action=f"accounting.{conn.provider}.disconnected",
        entity_type="accounting_connection",
        entity_id=conn.id,
        details=f"Disconnected {conn.provider.title()} connection #{conn.id}",
    )
    db.commit()
    return AccountingDisconnectResponse(
        disconnected=True,
        provider=conn.provider,
        account_id=conn.id,
    )


@router.get("/mappings", response_model=list[AccountingFieldMappingRead])
def list_mappings(provider: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(AccountingFieldMapping)
    if provider:
        q = q.filter(AccountingFieldMapping.provider == provider)
    return q.order_by(AccountingFieldMapping.provider, AccountingFieldMapping.local_field).all()


@router.patch("/mappings")
def update_mappings(payload: AccountingFieldMappingUpdate, db: Session = Depends(get_db)):
    results = []
    for m in payload.mappings:
        existing = db.get(AccountingFieldMapping, m.get("id"))
        if existing:
            for key in ("external_field", "mapping_config_json", "enabled"):
                if key in m:
                    setattr(existing, key, m[key])
            existing.updated_at = datetime.utcnow()
            results.append(existing)
        elif m.get("local_field") and m.get("external_field"):
            fm = AccountingFieldMapping(
                provider=m.get("provider", ""),
                local_field=m["local_field"],
                external_field=m["external_field"],
                mapping_config_json=m.get("mapping_config_json", {}),
                enabled=m.get("enabled", True),
            )
            db.add(fm)
            db.flush()
            results.append(fm)
    log_action(
        db, actor="user", action="accounting.mappings.update",
        entity_type="accounting_mappings",
        entity_id=None,
        details=f"Updated {len(results)} field mappings",
    )
    db.commit()
    return results


@router.get("/vendors/search")
def search_vendors(
    provider: str = Query(...),
    query: str = Query(""),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    conn = _get_active_connection(db, provider)
    if conn is None:
        raise HTTPException(status_code=409, detail=f"{provider.title()} is not connected")
    env = settings.quickbooks_env if provider == "quickbooks" else settings.xero_env
    if env == "mock" or not settings.accounting_sync_enabled:
        mock_results = [
            {"id": f"mock_{provider}_contact_1", "name": "Acme Office Supplies", "provider": provider},
            {"id": f"mock_{provider}_contact_2", "name": "Beta Logistics Inc.", "provider": provider},
            {"id": f"mock_{provider}_contact_3", "name": "Global Tech Solutions", "provider": provider},
        ]
        if query:
            mock_results = [r for r in mock_results if query.lower() in r["name"].lower()]
        return mock_results
    raise HTTPException(status_code=501, detail=f"Real {provider.title()} vendor search requires the provider SDK")


@router.post("/vendors/map", response_model=AccountingVendorMappingRead)
def map_vendor(payload: AccountingVendorMapRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(AccountingVendorMapping)
        .filter(
            AccountingVendorMapping.provider == payload.provider,
            AccountingVendorMapping.local_vendor_name.ilike(payload.local_vendor_name.strip()),
        )
        .first()
    )
    if existing:
        existing.external_contact_id = payload.external_contact_id
        existing.external_contact_name = payload.external_contact_name or ""
        existing.confidence_score = payload.confidence_score
        existing.updated_at = datetime.utcnow()
        mapping = existing
    else:
        mapping = AccountingVendorMapping(
            provider=payload.provider,
            local_vendor_name=payload.local_vendor_name.strip(),
            external_contact_id=payload.external_contact_id,
            external_contact_name=payload.external_contact_name or "",
            confidence_score=payload.confidence_score,
        )
        db.add(mapping)
    db.flush()
    log_action(
        db, actor="user", action=f"accounting.{payload.provider}.vendor.map",
        entity_type="accounting_vendor_mapping",
        entity_id=mapping.id,
        details=f"Mapped vendor '{payload.local_vendor_name}' -> '{payload.external_contact_name}' ({payload.provider})",
    )
    db.commit()
    db.refresh(mapping)
    return mapping


@router.get("/categories")
def list_categories(
    provider: str = Query(...),
    query: str = Query(""),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    conn = _get_active_connection(db, provider)
    if conn is None:
        raise HTTPException(status_code=409, detail=f"{provider.title()} is not connected")
    env = settings.quickbooks_env if provider == "quickbooks" else settings.xero_env
    if env == "mock" or not settings.accounting_sync_enabled:
        mock_categories = [
            {"id": f"mock_{provider}_acct_1", "name": "Office Supplies", "provider": provider},
            {"id": f"mock_{provider}_acct_2", "name": "Professional Services", "provider": provider},
            {"id": f"mock_{provider}_acct_3", "name": "Travel Expenses", "provider": provider},
            {"id": f"mock_{provider}_acct_4", "name": "Utilities", "provider": provider},
            {"id": f"mock_{provider}_acct_5", "name": "Equipment", "provider": provider},
        ]
        if query:
            mock_categories = [c for c in mock_categories if query.lower() in c["name"].lower()]
        return mock_categories
    raise HTTPException(status_code=501, detail=f"Real {provider.title()} category search requires the provider SDK")


@router.get("/vendor-mappings", response_model=list[AccountingVendorMappingRead])
def list_vendor_mappings(provider: str = Query(...), db: Session = Depends(get_db)):
    return (
        db.query(AccountingVendorMapping)
        .filter(AccountingVendorMapping.provider == provider)
        .order_by(AccountingVendorMapping.updated_at.desc())
        .all()
    )


@router.get("/category-mappings", response_model=list[AccountingCategoryMappingRead])
def list_category_mappings(provider: str = Query(...), db: Session = Depends(get_db)):
    return (
        db.query(AccountingCategoryMapping)
        .filter(AccountingCategoryMapping.provider == provider)
        .order_by(AccountingCategoryMapping.updated_at.desc())
        .all()
    )


@router.post("/categories/map", response_model=AccountingCategoryMappingRead)
def map_category(payload: AccountingCategoryMapRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(AccountingCategoryMapping)
        .filter(
            AccountingCategoryMapping.provider == payload.provider,
            AccountingCategoryMapping.local_category.ilike(payload.local_category.strip()),
        )
        .first()
    )
    if existing:
        existing.external_account_id = payload.external_account_id
        existing.external_account_name = payload.external_account_name or ""
        existing.external_tax_code = payload.external_tax_code or ""
        existing.enabled = True
        existing.updated_at = datetime.utcnow()
        mapping = existing
    else:
        mapping = AccountingCategoryMapping(
            provider=payload.provider,
            local_category=payload.local_category.strip(),
            external_account_id=payload.external_account_id,
            external_account_name=payload.external_account_name or "",
            external_tax_code=payload.external_tax_code or "",
        )
        db.add(mapping)
    db.flush()
    log_action(
        db, actor="user", action=f"accounting.{payload.provider}.category.map",
        entity_type="accounting_category_mapping",
        entity_id=mapping.id,
        details=f"Mapped category '{payload.local_category}' -> '{payload.external_account_name}' ({payload.provider})",
    )
    db.commit()
    db.refresh(mapping)
    return mapping


@router.post("/invoices/{invoice_id}/preview-sync")
def preview_sync(
    invoice_id: int,
    provider: str = Query(...),
    db: Session = Depends(get_db),
):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    result = build_sync_preview(db, invoice, provider)
    preview = AccountingSyncPreview(
        provider=provider,
        invoice_id=invoice.id,
        preview_json=result["preview"],
        warnings_json=result["warnings"],
        blockers_json=result["blockers"],
        risk_level=result["risk_level"],
        approval_required=result["eligible"],
        status="pending",
    )
    db.add(preview)
    db.flush()
    log_action(
        db,
        actor="user",
        action=f"accounting.{provider}.preview",
        entity_type="invoice",
        entity_id=invoice.id,
        details=f"Built {provider.title()} sync preview for invoice #{invoice.id}",
        after_data={"preview_id": preview.id, "eligible": result["eligible"]},
    )
    db.commit()
    db.refresh(preview)
    return AccountingSyncPreviewResponse(
        preview_id=preview.id,
        provider=provider,
        invoice_id=invoice.id,
        preview=result["preview"],
        warnings=result["warnings"],
        blockers=result["blockers"],
        risk_level=result["risk_level"],
        approval_required=result["eligible"],
        eligible=result["eligible"],
    )


@router.get("/previews/{preview_id}")
def get_preview(preview_id: int, db: Session = Depends(get_db)):
    preview = db.get(AccountingSyncPreview, preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="Preview not found")
    return preview


@router.post("/previews/{preview_id}/approve")
def approve_preview(
    preview_id: int,
    payload: AccountingApprovalRequest,
    db: Session = Depends(get_db),
):
    preview = db.get(AccountingSyncPreview, preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="Preview not found")
    if preview.status != "pending":
        raise HTTPException(status_code=409, detail=f"Preview status is '{preview.status}'; must be 'pending'")
    preview.status = "approved"
    preview.updated_at = datetime.utcnow()
    log_action(
        db,
        actor=payload.actor,
        action=f"accounting.{preview.provider}.preview.approve",
        entity_type="invoice",
        entity_id=preview.invoice_id,
        details=payload.reason or f"Approved {preview.provider.title()} sync for invoice #{preview.invoice_id}",
    )
    db.commit()
    db.refresh(preview)
    return {"preview_id": preview.id, "status": "approved", "provider": preview.provider, "invoice_id": preview.invoice_id}


@router.post("/previews/{preview_id}/reject")
def reject_preview(
    preview_id: int,
    payload: AccountingRejectRequest,
    db: Session = Depends(get_db),
):
    preview = db.get(AccountingSyncPreview, preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="Preview not found")
    if preview.status != "pending":
        raise HTTPException(status_code=409, detail=f"Preview status is '{preview.status}'; must be 'pending'")
    preview.status = "rejected"
    preview.updated_at = datetime.utcnow()
    log_action(
        db,
        actor=payload.actor,
        action=f"accounting.{preview.provider}.preview.reject",
        entity_type="invoice",
        entity_id=preview.invoice_id,
        details=payload.reason or f"Rejected {preview.provider.title()} sync for invoice #{preview.invoice_id}",
    )
    db.commit()
    return {"preview_id": preview.id, "status": "rejected", "provider": preview.provider, "invoice_id": preview.invoice_id}


@router.post("/previews/{preview_id}/sync")
def sync_preview(
    preview_id: int,
    db: Session = Depends(get_db),
    actor: str = Query("user"),
):
    preview = db.get(AccountingSyncPreview, preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="Preview not found")
    if preview.status != "approved":
        raise HTTPException(status_code=409, detail=f"Preview status is '{preview.status}'; must be 'approved' before sync")
    if not preview.blockers_json:
        preview_refresh = build_sync_preview(db, db.get(Invoice, preview.invoice_id), preview.provider)
        if not preview_refresh["eligible"]:
            raise HTTPException(status_code=409, detail=f"Sync is no longer eligible: {'; '.join(preview_refresh['blockers'])}")
    result = execute_sync(db, preview_id=preview.id, provider=preview.provider, actor=actor)
    if result["status"] == "failed":
        raise HTTPException(status_code=502, detail=result.get("error_message", "Sync failed"))
    return AccountingSyncResult(
        sync_log_id=result["sync_log_id"],
        provider=result["provider"],
        invoice_id=result["invoice_id"],
        external_record_id=result.get("external_record_id"),
        external_record_type=result.get("external_record_type", ""),
        status=result["status"],
        error_message=result.get("error_message"),
    )


@router.post("/sync-logs/{sync_log_id}/validate")
def validate_sync(sync_log_id: int, db: Session = Depends(get_db)):
    result = validate_sync_result(db, sync_log_id)
    return AccountingValidationResponse(
        validation_id=result["validation_id"],
        provider=result["provider"],
        invoice_id=result["invoice_id"],
        sync_log_id=result["sync_log_id"],
        external_record_id=result.get("external_record_id", ""),
        differences=result["differences"],
        validation_status=result["validation_status"],
    )


@router.get("/validations/{invoice_id}")
def get_validations(invoice_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(AccountingEntryValidation)
        .filter(AccountingEntryValidation.invoice_id == invoice_id)
        .order_by(AccountingEntryValidation.id.desc())
        .all()
    )
    return rows


@router.get("/sync-logs")
def list_sync_logs(
    limit: int = Query(50, ge=1, le=500),
    provider: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    invoice_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(AccountingSyncLog).order_by(AccountingSyncLog.id.desc())
    if provider:
        q = q.filter(AccountingSyncLog.provider == provider)
    if status:
        q = q.filter(AccountingSyncLog.status == status)
    if invoice_id:
        q = q.filter(AccountingSyncLog.invoice_id == invoice_id)
    return q.limit(limit).all()


@router.get("/failed-syncs")
def list_failed_syncs(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    return (
        db.query(AccountingSyncLog)
        .filter(AccountingSyncLog.status.in_(["failed", "needs_review"]))
        .order_by(AccountingSyncLog.id.desc())
        .limit(limit)
        .all()
    )


@router.post("/voice/preview")
def voice_preview(payload: AccountingVoicePreviewRequest, db: Session = Depends(get_db)):
    result = voice_intent_preview(payload.provider, payload.intent, payload.invoice_id)
    if result.get("blocked"):
        return AccountingVoicePreviewResponse(
            provider=payload.provider,
            intent=payload.intent,
            blocked=True,
            message=result.get("message", "Voice intent is blocked"),
        )
    if payload.invoice_id:
        invoice = db.get(Invoice, payload.invoice_id)
        if invoice is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        preview_result = build_sync_preview(db, invoice, payload.provider)
        preview = AccountingSyncPreview(
            provider=payload.provider,
            invoice_id=invoice.id,
            preview_json=preview_result["preview"],
            warnings_json=preview_result["warnings"],
            blockers_json=preview_result["blockers"],
            risk_level=preview_result["risk_level"],
            approval_required=preview_result["eligible"],
            status="pending",
        )
        db.add(preview)
        db.flush()
        log_action(
            db,
            actor=payload.actor,
            action=f"accounting.{payload.provider}.voice.preview",
            entity_type="invoice",
            entity_id=invoice.id,
            details=f"Voice intent '{payload.intent}' built {payload.provider.title()} sync preview",
        )
        db.commit()
        db.refresh(preview)
        return AccountingVoicePreviewResponse(
            provider=payload.provider,
            intent=payload.intent,
            preview_id=preview.id,
            preview=preview,
            blocked=False,
            message=f"Preview created; requires approval before sync.",
        )
    return AccountingVoicePreviewResponse(
        provider=payload.provider,
        intent=payload.intent,
        blocked=False,
        message=f"Voice intent '{payload.intent}' routed to {payload.provider}.",
    )
