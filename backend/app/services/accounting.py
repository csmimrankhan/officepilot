"""Phase 13 — accounting sync service (QuickBooks + Xero API).

Handles OAuth flows, token management, vendor/contact lookups,
account/category mappings, sync preview building, bill/purchase
invoice creation in draft mode, read-back validation, and
request/response redaction for audit logging.

Operates in mock mode by default — no real API calls are made
unless the environment is explicitly set to "production" and
valid OAuth credentials are present.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from ..config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token encryption (simple Fernet-like with cryptography if available)
# ---------------------------------------------------------------------------

try:
    from cryptography.fernet import Fernet as _FernetLib
    _HAS_FERNET = True
except ImportError:
    _HAS_FERNET = False


def _get_fernet_key(settings=None) -> bytes:
    if settings is None:
        settings = get_settings()
    raw = getattr(settings, "gmail_token_key", "") or ""
    if not raw:
        raw = _derive_key(settings)
    key = raw.encode("utf-8") if isinstance(raw, str) else raw
    try:
        base64.urlsafe_b64decode(key)
        return key
    except Exception:
        pass
    import hashlib
    return base64.urlsafe_b64encode(hashlib.sha256(key).digest())


def _derive_key(settings) -> str:
    raw = str(settings.data_dir) + "::officepilot_accounting_v1"
    import hashlib
    return base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest()).decode()


def encrypt_token(plain: str, settings=None) -> str:
    if not plain:
        return ""
    if _HAS_FERNET:
        k = _get_fernet_key(settings)
        try:
            f = _FernetLib(k)
            return f.encrypt(plain.encode()).decode()
        except Exception:
            pass
    return _simple_encrypt(plain, settings)


def decrypt_token(encrypted: str, settings=None) -> str:
    if not encrypted:
        return ""
    if _HAS_FERNET:
        k = _get_fernet_key(settings)
        try:
            f = _FernetLib(k)
            return f.decrypt(encrypted.encode()).decode()
        except Exception:
            pass
    return _simple_decrypt(encrypted, settings)


def _simple_encrypt(plain: str, settings=None) -> str:
    if settings is None:
        settings = get_settings()
    salt = str(settings.data_dir)
    result = base64.urlsafe_b64encode(
        bytes([b ^ ord(salt[i % len(salt)]) for i, b in enumerate(plain.encode("utf-8"))])
    ).decode()
    return f"acct_{result}"


def _simple_decrypt(encrypted: str, settings=None) -> str:
    if not encrypted.startswith("acct_"):
        return encrypted
    if settings is None:
        settings = get_settings()
    salt = str(settings.data_dir)
    raw = base64.urlsafe_b64decode(encrypted[5:] + "===")
    return "".join(chr(b ^ ord(salt[i % len(salt)])) for i, b in enumerate(raw))


# ---------------------------------------------------------------------------
# OAuth helpers
# ---------------------------------------------------------------------------


QUICKBOOKS_SCOPES = [
    "com.intuit.quickbooks.accounting",
    "openid",
    "profile",
    "email",
]

XERO_SCOPES = [
    "openid",
    "profile",
    "email",
    "accounting.contacts",
    "accounting.transactions",
    "accounting.settings",
]


class AccountingOAuthError(Exception):
    pass


def quickbooks_authorization_url(settings) -> dict:
    state = uuid.uuid4().hex[:16]
    client_id = settings.quickbooks_client_id or "mock_client_id"
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": " ".join(QUICKBOOKS_SCOPES),
        "redirect_uri": settings.quickbooks_redirect_uri,
        "state": state,
    }
    base = (
        "https://appcenter.intuit.com/connect/oauth2"
        if settings.quickbooks_env == "production"
        else "https://appcenter.intuit.com/connect/oauth2"
    )
    url = f"{base}?{urlencode(params)}"
    return {"authorization_url": url, "state": state, "provider": "quickbooks"}


def quickbooks_exchange_code(settings, code: str, redirect_uri: str) -> dict:
    if settings.quickbooks_env == "mock":
        return _mock_exchange("quickbooks")
    url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    auth = base64.b64encode(
        f"{settings.quickbooks_client_id}:{settings.quickbooks_client_secret}".encode()
    ).decode()
    resp = requests.post(
        url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise AccountingOAuthError(f"QuickBooks token exchange failed: {resp.text}")
    data = resp.json()
    return {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", ""),
        "realm_id": data.get("realmId", ""),
        "expires_in": data.get("expires_in", 3600),
        "x_refresh_token_expires_in": data.get("x_refresh_token_expires_in", 87213600),
    }


def quickbooks_refresh_token(settings, refresh_token: str) -> dict:
    if settings.quickbooks_env == "mock":
        return _mock_exchange("quickbooks")
    url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    auth = base64.b64encode(
        f"{settings.quickbooks_client_id}:{settings.quickbooks_client_secret}".encode()
    ).decode()
    resp = requests.post(
        url,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise AccountingOAuthError(f"QuickBooks token refresh failed: {resp.text}")
    return resp.json()


def xero_authorization_url(settings) -> dict:
    state = uuid.uuid4().hex[:16]
    client_id = settings.xero_client_id or "mock_client_id"
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": " ".join(XERO_SCOPES),
        "redirect_uri": settings.xero_redirect_uri,
        "state": state,
    }
    base = "https://login.xero.com/identity/connect/authorize"
    url = f"{base}?{urlencode(params)}"
    return {"authorization_url": url, "state": state, "provider": "xero"}


def xero_exchange_code(settings, code: str, redirect_uri: str) -> dict:
    if settings.xero_env == "mock":
        return _mock_exchange("xero")
    url = "https://identity.xero.com/connect/token"
    resp = requests.post(
        url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={
            "Authorization": f"Basic {base64.b64encode(f'{settings.xero_client_id}:{settings.xero_client_secret}'.encode()).decode()}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise AccountingOAuthError(f"Xero token exchange failed: {resp.text}")
    data = resp.json()
    return {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", ""),
        "id_token": data.get("id_token", ""),
        "expires_in": data.get("expires_in", 3600),
    }


def xero_refresh_token(settings, refresh_token: str) -> dict:
    if settings.xero_env == "mock":
        return _mock_exchange("xero")
    url = "https://identity.xero.com/connect/token"
    resp = requests.post(
        url,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={
            "Authorization": f"Basic {base64.b64encode(f'{settings.xero_client_id}:{settings.xero_client_secret}'.encode()).decode()}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise AccountingOAuthError(f"Xero token refresh failed: {resp.text}")
    return resp.json()


def _mock_exchange(provider: str) -> dict:
    return {
        "access_token": f"mock_{provider}_access_token_{uuid.uuid4().hex[:12]}",
        "refresh_token": f"mock_{provider}_refresh_token_{uuid.uuid4().hex[:12]}",
        "realm_id": f"mock_realm_{uuid.uuid4().hex[:8]}" if provider == "quickbooks" else "",
        "tenant_id": f"mock_tenant_{uuid.uuid4().hex[:8]}" if provider == "xero" else "",
        "expires_in": 3600,
        "x_refresh_token_expires_in": 87213600,
        "id_token": "mock_id_token" if provider == "xero" else "",
        "mock": True,
    }


# ---------------------------------------------------------------------------
# Invoice eligibility
# ---------------------------------------------------------------------------


REQUIRED_SYNC_FIELDS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "total_amount",
    "currency",
]


def check_invoice_eligibility(invoice) -> dict:
    blockers: list[str] = []
    warnings: list[str] = []
    if invoice is None:
        return {"eligible": False, "blockers": ["Invoice not found"], "warnings": []}
    status = getattr(invoice, "status", "")
    if status != "approved":
        blockers.append(f"Invoice status is '{status}'; must be 'approved'")
    for field in REQUIRED_SYNC_FIELDS:
        val = getattr(invoice, field, None)
        if val is None or (isinstance(val, str) and not val.strip()) or val == "":
            blockers.append(f"Missing required field: {field}")
    if hasattr(invoice, "total_amount") and invoice.total_amount is not None:
        try:
            if float(invoice.total_amount) <= 0:
                blockers.append("Total amount must be positive")
        except (ValueError, TypeError):
            blockers.append("Total amount is not a valid number")
    if blockers:
        return {"eligible": False, "blockers": blockers, "warnings": warnings}
    return {"eligible": True, "blockers": [], "warnings": warnings}


def check_duplicate_sync(db, invoice_id: int, provider: str) -> bool:
    from ..models.accounting_sync_log import AccountingSyncLog
    existing = (
        db.query(AccountingSyncLog)
        .filter(
            AccountingSyncLog.invoice_id == invoice_id,
            AccountingSyncLog.provider == provider,
            AccountingSyncLog.status == "success",
        )
        .first()
    )
    return existing is not None


def check_connection_active(db, provider: str) -> Optional[dict]:
    from ..models.accounting_connection import AccountingConnection
    conn = (
        db.query(AccountingConnection)
        .filter(
            AccountingConnection.provider == provider,
            AccountingConnection.status == "active",
        )
        .order_by(AccountingConnection.id.desc())
        .first()
    )
    if conn is None:
        return None
    return {
        "id": conn.id,
        "provider": conn.provider,
        "status": conn.status,
        "realm_id": conn.realm_id,
        "tenant_id": conn.tenant_id,
        "environment": conn.environment,
    }


def check_vendor_mapping(db, provider: str, vendor_name: str) -> Optional[dict]:
    from ..models.accounting_vendor_mapping import AccountingVendorMapping
    mapping = (
        db.query(AccountingVendorMapping)
        .filter(
            AccountingVendorMapping.provider == provider,
            AccountingVendorMapping.local_vendor_name.ilike(vendor_name.strip()),
        )
        .first()
    )
    if mapping is None:
        return None
    return {
        "id": mapping.id,
        "local_vendor_name": mapping.local_vendor_name,
        "external_contact_id": mapping.external_contact_id,
        "external_contact_name": mapping.external_contact_name,
    }


def check_category_mapping(db, provider: str, category: str = "") -> Optional[dict]:
    from ..models.accounting_category_mapping import AccountingCategoryMapping
    q = db.query(AccountingCategoryMapping).filter(
        AccountingCategoryMapping.provider == provider,
        AccountingCategoryMapping.enabled == True,
    )
    if category:
        q = q.filter(AccountingCategoryMapping.local_category.ilike(category.strip()))
    mapping = q.first()
    if mapping is None:
        return None
    return {
        "id": mapping.id,
        "local_category": mapping.local_category,
        "external_account_id": mapping.external_account_id,
        "external_account_name": mapping.external_account_name,
        "external_tax_code": mapping.external_tax_code,
    }


# ---------------------------------------------------------------------------
# Preview builder
# ---------------------------------------------------------------------------


def build_sync_preview(db, invoice, provider: str) -> dict:
    settings = get_settings()
    eligibility = check_invoice_eligibility(invoice)
    blockers = list(eligibility["blockers"])
    warnings = list(eligibility["warnings"])
    connection = check_connection_active(db, provider)
    if connection is None:
        blockers.append(f"{provider.title()} is not connected. Connect a {provider.title()} account first.")
    else:
        if connection.get("environment") in ("sandbox", "mock", "demo"):
            warnings.append(f"Connected to {provider.title()} in {connection['environment']} mode.")
    vendor_name = getattr(invoice, "vendor_name", "") or ""
    vendor_mapping = check_vendor_mapping(db, provider, vendor_name) if vendor_name else None
    if vendor_mapping is None:
        blockers.append(f"Vendor '{vendor_name}' is not mapped to a {provider.title()} contact. Map it in Accounting Mappings.")
    category_mapping = check_category_mapping(db, provider)
    if category_mapping is None:
        warnings.append(f"No category/account mapping found for {provider.title()}. Default account will be used.")

    duplicate = check_duplicate_sync(db, invoice.id, provider)
    if duplicate:
        blockers.append(f"This invoice has already been synced to {provider.title()}. Duplicate sync blocked.")

    invoice_data = _invoice_to_preview_dict(invoice)
    mapped = _build_mapped_payload(invoice_data, vendor_mapping, category_mapping, provider)
    preview = {
        "provider": provider,
        "invoice_id": invoice.id,
        "invoice": invoice_data,
        "mapping": mapped,
        "connection": connection,
    }
    risk_level = "high" if blockers else "medium"
    return {
        "preview": preview,
        "blockers": blockers,
        "warnings": warnings,
        "risk_level": risk_level,
        "eligible": len(blockers) == 0,
    }


def _invoice_to_preview_dict(invoice) -> dict:
    return {
        "id": invoice.id,
        "vendor_name": getattr(invoice, "vendor_name", "") or "",
        "invoice_number": getattr(invoice, "invoice_number", "") or "",
        "invoice_date": str(getattr(invoice, "invoice_date", "") or ""),
        "due_date": str(getattr(invoice, "due_date", "") or ""),
        "currency": getattr(invoice, "currency", "") or "",
        "subtotal": _to_float(getattr(invoice, "subtotal", None)),
        "tax": _to_float(getattr(invoice, "tax", None)),
        "total_amount": _to_float(getattr(invoice, "total_amount", None)),
        "line_items": _line_items_to_list(getattr(invoice, "line_items", [])),
        "notes": getattr(invoice, "notes", "") or "",
    }


def _to_float(val):
    if val is None:
        return None
    try:
        return round(float(val), 2)
    except (ValueError, TypeError):
        return None


def _line_items_to_list(line_items) -> list[dict]:
    if not line_items:
        return []
    items = []
    for li in line_items:
        items.append({
            "description": getattr(li, "description", "") or "",
            "quantity": _to_float(getattr(li, "quantity", None)),
            "unit_price": _to_float(getattr(li, "unit_price", None)),
            "line_total": _to_float(getattr(li, "line_total", None)),
        })
    return items


def _build_mapped_payload(invoice_data: dict, vendor_mapping: Optional[dict], category_mapping: Optional[dict], provider: str) -> dict:
    mapped = {
        "vendor": {
            "local": invoice_data.get("vendor_name", ""),
            "external_id": vendor_mapping["external_contact_id"] if vendor_mapping else "",
            "external_name": vendor_mapping["external_contact_name"] if vendor_mapping else "",
            "mapped": vendor_mapping is not None,
        },
        "account": {
            "external_id": category_mapping["external_account_id"] if category_mapping else "",
            "external_name": category_mapping["external_account_name"] if category_mapping else "",
            "tax_code": category_mapping["external_tax_code"] if category_mapping else "",
            "mapped": category_mapping is not None,
        },
        "fields": [
            {"local_field": "invoice_number", "local_value": invoice_data.get("invoice_number", ""), "external_field": "DocNumber", "external_value": invoice_data.get("invoice_number", ""), "mapped": True},
            {"local_field": "invoice_date", "local_value": invoice_data.get("invoice_date", ""), "external_field": "TxnDate", "external_value": invoice_data.get("invoice_date", ""), "mapped": True},
            {"local_field": "due_date", "local_value": invoice_data.get("due_date", ""), "external_field": "DueDate", "external_value": invoice_data.get("due_date", ""), "mapped": bool(invoice_data.get("due_date"))},
            {"local_field": "currency", "local_value": invoice_data.get("currency", ""), "external_field": "CurrencyRef", "external_value": invoice_data.get("currency", ""), "mapped": True},
            {"local_field": "subtotal", "local_value": str(invoice_data.get("subtotal", "") or ""), "external_field": "Line/Amount", "external_value": str(invoice_data.get("subtotal", "") or ""), "mapped": True},
            {"local_field": "tax", "local_value": str(invoice_data.get("tax", "") or ""), "external_field": "TxnTaxDetail", "external_value": str(invoice_data.get("tax", "") or ""), "mapped": True},
            {"local_field": "total_amount", "local_value": str(invoice_data.get("total_amount", "") or ""), "external_field": "TotalAmt", "external_value": str(invoice_data.get("total_amount", "") or ""), "mapped": True},
        ],
    }
    if provider == "xero":
        for f in mapped["fields"]:
            if f["local_field"] == "invoice_number":
                f["external_field"] = "InvoiceNumber"
            elif f["local_field"] == "invoice_date":
                f["external_field"] = "Date"
            elif f["local_field"] == "due_date":
                f["external_field"] = "DueDate"
            elif f["local_field"] == "currency":
                f["external_field"] = "CurrencyCode"
            elif f["local_field"] == "subtotal":
                f["external_field"] = "SubTotal"
            elif f["local_field"] == "tax":
                f["external_field"] = "TotalTax"
            elif f["local_field"] == "total_amount":
                f["external_field"] = "Total"
    return mapped


# ---------------------------------------------------------------------------
# Sync execution (mock by default)
# ---------------------------------------------------------------------------


def _get_active_access_token(db, provider: str) -> Optional[str]:
    from ..models.accounting_connection import AccountingConnection
    conn = (
        db.query(AccountingConnection)
        .filter(
            AccountingConnection.provider == provider,
            AccountingConnection.status == "active",
        )
        .order_by(AccountingConnection.id.desc())
        .first()
    )
    if conn is None:
        return None
    return decrypt_token(conn.access_token_encrypted)


def execute_sync(db, preview_id: int, provider: str, actor: str = "user") -> dict:
    from ..models.accounting_sync_preview import AccountingSyncPreview
    from ..models.accounting_sync_log import AccountingSyncLog
    from ..models.accounting_connection import AccountingConnection
    from ..models.invoice import Invoice

    preview = db.get(AccountingSyncPreview, preview_id)
    if preview is None:
        return {"status": "failed", "error_message": "Preview not found"}
    if preview.status != "approved":
        return {"status": "failed", "error_message": f"Preview status is '{preview.status}'; must be 'approved'"}
    invoice = db.get(Invoice, preview.invoice_id)
    if invoice is None:
        return {"status": "failed", "error_message": "Invoice not found"}
    conn = (
        db.query(AccountingConnection)
        .filter(
            AccountingConnection.provider == provider,
            AccountingConnection.status == "active",
        )
        .order_by(AccountingConnection.id.desc())
        .first()
    )
    if conn is None:
        return {"status": "failed", "error_message": f"No active {provider.title()} connection"}
    settings = get_settings()
    env = settings.quickbooks_env if provider == "quickbooks" else settings.xero_env
    mock_result = env == "mock" or not settings.accounting_sync_enabled
    invoice_data = _invoice_to_preview_dict(invoice)
    vendor_mapping = check_vendor_mapping(db, provider, invoice_data.get("vendor_name", ""))
    category_mapping = check_category_mapping(db, provider)

    if mock_result:
        external_id = f"mock_{provider}_bill_{uuid.uuid4().hex[:10]}"
        external_type = "Bill" if provider == "quickbooks" else "PurchaseOrder"
        request_payload = _build_mock_request(invoice_data, vendor_mapping, category_mapping, provider)
        response_payload = {
            "id": external_id,
            "status": "draft" if settings.accounting_draft_only else "submitted",
            "provider": provider,
            "mock": True,
        }
    else:
        access_token = _get_active_access_token(db, provider)
        if not access_token:
            return {"status": "failed", "error_message": "No access token available"}
        try:
            result = _call_provider_api(provider, access_token, conn, invoice_data, vendor_mapping, category_mapping, settings)
            external_id = result.get("id", "")
            external_type = result.get("type", "Bill")
            request_payload = result.get("request", {})
            response_payload = result.get("response", {})
        except Exception as exc:
            sync_log = AccountingSyncLog(
                provider=provider,
                invoice_id=invoice.id,
                connection_id=conn.id,
                preview_id=preview.id,
                status="failed",
                error_message=str(exc),
                request_json_redacted={},
                response_json_redacted={},
            )
            db.add(sync_log)
            preview.status = "failed"
            db.commit()
            return {"status": "failed", "error_message": str(exc)}

    sync_log = AccountingSyncLog(
        provider=provider,
        invoice_id=invoice.id,
        connection_id=conn.id,
        preview_id=preview.id,
        external_record_id=external_id,
        external_record_type=external_type,
        request_json_redacted=_redact_payload(request_payload),
        response_json_redacted=_redact_payload(response_payload),
        status="success",
    )
    db.add(sync_log)
    preview.status = "synced"
    from ..services.audit import log_action
    log_action(
        db,
        actor=actor,
        action=f"accounting.{provider}.sync",
        entity_type="invoice",
        entity_id=invoice.id,
        details=f"Synced invoice #{invoice.id} to {provider.title()} as {external_type} #{external_id}",
        after_data={
            "provider": provider,
            "external_id": external_id,
            "external_type": external_type,
            "sync_log_id": sync_log.id,
        },
    )
    db.commit()
    db.refresh(sync_log)
    return {
        "status": "success",
        "sync_log_id": sync_log.id,
        "provider": provider,
        "invoice_id": invoice.id,
        "external_record_id": external_id,
        "external_record_type": external_type,
        "mock": mock_result,
    }


def _build_mock_request(invoice_data, vendor_mapping, category_mapping, provider):
    return {
        "provider": provider,
        "vendor_id": vendor_mapping["external_contact_id"] if vendor_mapping else "",
        "vendor_name": vendor_mapping["external_contact_name"] if vendor_mapping else invoice_data.get("vendor_name", ""),
        "account_id": category_mapping["external_account_id"] if category_mapping else "",
        "doc_number": invoice_data.get("invoice_number", ""),
        "txn_date": invoice_data.get("invoice_date", ""),
        "due_date": invoice_data.get("due_date", ""),
        "currency": invoice_data.get("currency", "USD"),
        "total_amount": invoice_data.get("total_amount", 0),
        "line_items": invoice_data.get("line_items", []),
        "draft": True,
    }


def _call_provider_api(provider, access_token, conn, invoice_data, vendor_mapping, category_mapping, settings) -> dict:
    raise NotImplementedError(
        f"Real {provider.title()} API calls require the provider SDK. "
        "Set the provider env to 'mock' for testing."
    )


def _redact_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"_redacted": str(payload)[:200]}
    redacted = {}
    SENSITIVE_KEYS = {"access_token", "refresh_token", "token", "secret", "password", "authorization"}
    for k, v in payload.items():
        if k.lower() in SENSITIVE_KEYS:
            redacted[k] = "[REDACTED]"
        elif isinstance(v, dict):
            redacted[k] = _redact_payload(v)
        elif isinstance(v, list):
            redacted[k] = [_redact_payload(i) if isinstance(i, dict) else i for i in v]
        else:
            redacted[k] = v
    return redacted


# ---------------------------------------------------------------------------
# Read-back validation
# ---------------------------------------------------------------------------


def validate_sync_result(db, sync_log_id: int) -> dict:
    from ..models.accounting_sync_log import AccountingSyncLog
    from ..models.accounting_entry_validation import AccountingEntryValidation
    from ..models.invoice import Invoice

    sync_log = db.get(AccountingSyncLog, sync_log_id)
    if sync_log is None:
        return {"validation_status": "failed", "error_message": "Sync log not found"}
    invoice = db.get(Invoice, sync_log.invoice_id)
    if invoice is None:
        return {"validation_status": "failed", "error_message": "Invoice not found"}
    settings = get_settings()
    env = settings.quickbooks_env if sync_log.provider == "quickbooks" else settings.xero_env

    source = _invoice_to_preview_dict(invoice)
    if env == "mock" or not settings.accounting_sync_enabled:
        accounting = _mock_read_back(source, sync_log.provider)
    else:
        accounting = _real_read_back(sync_log)
    differences = _compare_source_to_accounting(source, accounting)
    validation_status = "validated"
    if differences:
        validation_status = "mismatch" if any(d["match"] is False for d in differences) else "validated"
    validation = AccountingEntryValidation(
        provider=sync_log.provider,
        invoice_id=invoice.id,
        sync_log_id=sync_log.id,
        external_record_id=sync_log.external_record_id or "",
        source_json=source,
        accounting_json=accounting,
        differences_json=differences,
        validation_status=validation_status,
    )
    db.add(validation)
    if validation_status == "mismatch":
        sync_log.status = "needs_review"
    from ..services.audit import log_action
    log_action(
        db,
        actor="system",
        action=f"accounting.{sync_log.provider}.validate",
        entity_type="invoice",
        entity_id=invoice.id,
        details=f"Validation {validation_status} for sync_log #{sync_log_id}",
        after_data={"validation_id": validation.id, "differences": differences},
    )
    db.commit()
    db.refresh(validation)
    return {
        "validation_id": validation.id,
        "provider": sync_log.provider,
        "invoice_id": invoice.id,
        "sync_log_id": sync_log.id,
        "external_record_id": sync_log.external_record_id or "",
        "differences": differences,
        "validation_status": validation_status,
    }


def _mock_read_back(source: dict, provider: str) -> dict:
    result = dict(source)
    result["_mock_read_back"] = True
    result["_provider"] = provider
    if provider == "quickbooks":
        result["invoice_number"] = source.get("invoice_number", "") + ""
        result["currency"] = source.get("currency", "USD")
    else:
        result["invoice_number"] = source.get("invoice_number", "") + ""
        result["currency"] = source.get("currency", "USD")
    result["external_record_type"] = "Bill" if provider == "quickbooks" else "PurchaseOrder"
    return result


def _real_read_back(sync_log) -> dict:
    raise NotImplementedError("Real read-back requires the provider API.")


def _compare_source_to_accounting(source: dict, accounting: dict) -> list[dict]:
    FIELDS = [
        ("vendor_name", "vendor_name"),
        ("invoice_number", "invoice_number"),
        ("invoice_date", "invoice_date"),
        ("due_date", "due_date"),
        ("currency", "currency"),
        ("subtotal", "subtotal"),
        ("tax", "tax"),
        ("total_amount", "total_amount"),
    ]
    differences = []
    for src_key, acct_key in FIELDS:
        sv = str(source.get(src_key, "") or "")
        av = str(accounting.get(acct_key, "") or "")
        match = sv.strip().lower() == av.strip().lower()
        if not match:
            differences.append({
                "field": src_key,
                "source_value": sv,
                "accounting_value": av,
                "match": False,
            })
        else:
            differences.append({
                "field": src_key,
                "source_value": sv,
                "accounting_value": av,
                "match": True,
            })
    return differences


# ---------------------------------------------------------------------------
# Voice intent stubs
# ---------------------------------------------------------------------------


ACCOUNTING_VOICE_INTENTS = {
    "export_this_invoice_to_quickbooks": {
        "provider": "quickbooks",
        "action": "preview_sync",
        "needs_approval": True,
    },
    "export_this_invoice_to_xero": {
        "provider": "xero",
        "action": "preview_sync",
        "needs_approval": True,
    },
    "sync_approved_invoices_to_quickbooks": {
        "provider": "quickbooks",
        "action": "preview_sync",
        "needs_approval": True,
    },
    "sync_approved_invoices_to_xero": {
        "provider": "xero",
        "action": "preview_sync",
        "needs_approval": True,
    },
    "validate_quickbooks_entry": {
        "provider": "quickbooks",
        "action": "validate",
        "needs_approval": False,
    },
    "validate_xero_entry": {
        "provider": "xero",
        "action": "validate",
        "needs_approval": False,
    },
    "show_failed_accounting_syncs": {
        "provider": "",
        "action": "list_failed",
        "needs_approval": False,
    },
}


def voice_intent_preview(provider: str, intent: str, invoice_id: Optional[int] = None) -> dict:
    spec = ACCOUNTING_VOICE_INTENTS.get(intent)
    if spec is None:
        return {"blocked": True, "message": f"Unknown voice intent: {intent!r}"}
    if spec.get("provider") and provider and spec["provider"] != provider:
        return {"blocked": True, "message": f"Intent {intent!r} is for {spec['provider']}, not {provider}"}
    return {
        "blocked": False,
        "intent": intent,
        "provider": provider or spec.get("provider", ""),
        "action": spec.get("action", ""),
        "needs_approval": spec.get("needs_approval", True),
        "invoice_id": invoice_id,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


__all__ = [
    "QUICKBOOKS_SCOPES",
    "XERO_SCOPES",
    "AccountingOAuthError",
    "ACCOUNTING_VOICE_INTENTS",
    "build_sync_preview",
    "check_connection_active",
    "check_duplicate_sync",
    "check_invoice_eligibility",
    "check_vendor_mapping",
    "check_category_mapping",
    "decrypt_token",
    "encrypt_token",
    "execute_sync",
    "quickbooks_authorization_url",
    "quickbooks_exchange_code",
    "quickbooks_refresh_token",
    "validate_sync_result",
    "voice_intent_preview",
    "xero_authorization_url",
    "xero_exchange_code",
    "xero_refresh_token",
]
