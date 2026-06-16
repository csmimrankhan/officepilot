"""Phase 38.6 Task 2 — Read-only QuickBooks data sync.

Fetches chart of accounts, customers, and invoices from QuickBooks
Online via the QuickBooks API. Returns mock data in sandbox/mock mode.
All data is stored read-only (no write operations to QuickBooks).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import requests
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.accounting_connection import AccountingConnection
from ..models.quickbooks_sync_state import QuickBooksSyncState
from ..services.accounting import decrypt_token

logger = logging.getLogger(__name__)

QB_BASE_URLS = {
    "production": "https://quickbooks.api.intuit.com",
    "sandbox": "https://sandbox-quickbooks.api.intuit.com",
    "mock": None,
}


def _get_connection(db: Session) -> Optional[AccountingConnection]:
    return (
        db.query(AccountingConnection)
        .filter(
            AccountingConnection.provider == "quickbooks",
            AccountingConnection.status == "active",
        )
        .order_by(AccountingConnection.id.desc())
        .first()
    )


def _get_or_create_state(db: Session, connection_id: int) -> QuickBooksSyncState:
    state = db.query(QuickBooksSyncState).filter(
        QuickBooksSyncState.connection_id == connection_id
    ).first()
    if state is None:
        state = QuickBooksSyncState(connection_id=connection_id)
        db.add(state)
        db.flush()
    return state


def _fetch_qb_data(endpoint: str, access_token: str, realm_id: str, base_url: str) -> list[dict]:
    url = f"{base_url}/v3/company/{realm_id}/{endpoint}?minorversion=73"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 401:
        raise PermissionError("QuickBooks token expired — reconnect required")
    resp.raise_for_status()
    data = resp.json()
    key = endpoint.split("/")[0].lower()
    query_response = data.get("QueryResponse", {})
    return query_response.get(key, [])


def _mock_accounts() -> list[dict]:
    return [
        {"Id": f"mock_acct_{i}", "Name": name, "AccountType": typ, "Classification": cls, "CurrentBalance": bal}
        for i, (name, typ, cls, bal) in enumerate([
            ("Accounts Receivable", "Accounts Receivable", "Asset", 15000.00),
            ("Office Supplies", "Expense", "Expense", 0.00),
            ("Professional Services", "Expense", "Expense", 0.00),
            ("Travel", "Expense", "Expense", 0.00),
            ("Utilities", "Expense", "Expense", 0.00),
            ("Equipment", "Other Current Asset", "Asset", 5000.00),
            ("Bank Charges", "Expense", "Expense", 0.00),
            ("Consulting Income", "Income", "Revenue", 25000.00),
            ("Sales", "Income", "Revenue", 45000.00),
            ("Accounts Payable", "Accounts Payable", "Liability", 8000.00),
        ])
    ]


def _mock_customers() -> list[dict]:
    return [
        {"Id": f"mock_cust_{i}", "DisplayName": name, "GivenName": given, "PrimaryEmailAddr": {"Address": email}, "Active": True}
        for i, (name, given, email) in enumerate([
            ("Acme Office Supplies", "Acme", "billing@acme.com"),
            ("Beta Logistics Inc.", "Beta", "ap@betalogistics.com"),
            ("Global Tech Solutions", "Global", "invoices@globaltech.com"),
            ("Prime Distributors", "Prime", "accounting@primedist.com"),
            ("Summit Partners LLC", "Summit", "payables@summitpartners.com"),
        ])
    ]


def _mock_invoices() -> list[dict]:
    return [
        {
            "Id": f"mock_inv_{i}",
            "DocNumber": f"INV-{1000 + i}",
            "TxnDate": f"2026-0{(i % 9) + 1:02d}-15",
            "TotalAmt": amt,
            "CurrencyRef": {"value": "USD"},
            "CustomerRef": {"name": cust},
            "DueDate": f"2026-0{(i % 9) + 2:02d}-15",
            "Balance": round(amt * 0.3, 2),
        }
        for i, (amt, cust) in enumerate([
            (1250.00, "Acme Office Supplies"),
            (3400.50, "Beta Logistics Inc."),
            (780.25, "Global Tech Solutions"),
            (5600.00, "Prime Distributors"),
            (2200.00, "Summit Partners LLC"),
            (890.75, "Acme Office Supplies"),
            (4100.00, "Beta Logistics Inc."),
            (1650.00, "Global Tech Solutions"),
        ])
    ]


def run_sync(db: Session, connection_id: int) -> dict[str, Any]:
    conn = db.get(AccountingConnection, connection_id)
    if conn is None:
        return {"status": "failed", "error": "Connection not found"}
    if conn.provider != "quickbooks":
        return {"status": "failed", "error": "Not a QuickBooks connection"}

    settings = get_settings()
    state = _get_or_create_state(db, connection_id)

    try:
        if settings.quickbooks_env == "mock":
            accounts = _mock_accounts()
            customers = _mock_customers()
            invoices = _mock_invoices()
        else:
            base_url = QB_BASE_URLS.get(settings.quickbooks_env) or QB_BASE_URLS["sandbox"]
            access_token = decrypt_token(conn.access_token_encrypted, settings)
            realm_id = conn.realm_id or ""

            accounts = _fetch_qb_data("query?query=select * from Account", access_token, realm_id, base_url)
            customers = _fetch_qb_data("query?query=select * from Customer", access_token, realm_id, base_url)
            invoices = _fetch_qb_data("query?query=select * from Invoice", access_token, realm_id, base_url)

        state.accounts_count = len(accounts)
        state.customers_count = len(customers)
        state.invoices_count = len(invoices)
        state.accounts_json = json.dumps(accounts)
        state.customers_json = json.dumps(customers)
        state.invoices_json = json.dumps(invoices)
        state.last_sync_at = datetime.utcnow()
        state.last_error = None
        state.status = "success"
        state.updated_at = datetime.utcnow()
        db.flush()
        db.commit()

        return {
            "status": "success",
            "accounts_count": len(accounts),
            "customers_count": len(customers),
            "invoices_count": len(invoices),
            "last_sync_at": state.last_sync_at.isoformat() if state.last_sync_at else None,
        }
    except Exception as exc:
        error_msg = str(exc)
        state.status = "failed"
        state.last_error = error_msg
        state.updated_at = datetime.utcnow()
        db.flush()
        db.commit()
        logger.error("QuickBooks sync failed for connection %s: %s", connection_id, error_msg)
        return {"status": "failed", "error": error_msg}


def get_sync_status(db: Session) -> dict[str, Any]:
    conn = _get_connection(db)
    if conn is None:
        return {"connected": False, "synced": False}

    state = db.query(QuickBooksSyncState).filter(
        QuickBooksSyncState.connection_id == conn.id
    ).first()

    return {
        "connected": True,
        "connection_id": conn.id,
        "realm_id": conn.realm_id,
        "company_name": conn.company_name,
        "environment": conn.environment,
        "synced": state is not None and state.status == "success",
        "accounts_count": state.accounts_count if state else 0,
        "customers_count": state.customers_count if state else 0,
        "invoices_count": state.invoices_count if state else 0,
        "last_sync_at": state.last_sync_at.isoformat() if state and state.last_sync_at else None,
        "last_error": state.last_error if state else None,
        "status": state.status if state else "never",
    }
