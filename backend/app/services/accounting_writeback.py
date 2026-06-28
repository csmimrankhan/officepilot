from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger("officepilot.accounting_writeback")


def _is_real_mode(provider: str) -> bool:
    env = os.environ.get(f"{provider.upper()}_ENV", "mock").lower()
    return env == "production"


def _build_mock_response(provider: str, vendor_name: str, total_amount: float) -> dict:
    bill_id = f"mock-{provider}-{uuid.uuid4().hex[:8]}"
    provider_title = provider.capitalize()
    return {
        "status": "success",
        "bill_id": bill_id,
        "url": f"https://mock.{provider}.com/bill/{bill_id}",
        "provider": provider,
        "vendor_name": vendor_name,
        "total_amount": total_amount,
        "bill_date": datetime.utcnow().isoformat(),
    }


def _build_qb_real_payload(vendor_name: str, line_items: list[dict], total_amount: float, due_date: str) -> dict:
    return {
        "Bill": {
            "VendorRef": {"name": vendor_name},
            "Line": [
                {
                    "DetailType": "AccountBasedExpenseLineDetail",
                    "Amount": item.get("amount", 0),
                    "Description": item.get("description", ""),
                    "AccountBasedExpenseLineDetail": {
                        "AccountRef": {"name": item.get("account", "Office Supplies")},
                    },
                }
                for item in line_items
            ],
            "TotalAmt": total_amount,
            "DueDate": due_date,
            "TxnDate": datetime.utcnow().strftime("%Y-%m-%d"),
        },
    }


def _build_xero_real_payload(vendor_name: str, line_items: list[dict], total_amount: float, due_date: str) -> dict:
    return {
        "Invoices": [
            {
                "Type": "ACCPAY",
                "Contact": {"Name": vendor_name},
                "LineItems": [
                    {
                        "Description": item.get("description", ""),
                        "Quantity": item.get("quantity", 1),
                        "UnitAmount": item.get("unit_amount", item.get("amount", 0)),
                        "AccountCode": item.get("account_code", "400"),
                    }
                    for item in line_items
                ],
                "Total": total_amount,
                "DueDate": due_date,
                "Date": datetime.utcnow().strftime("%Y-%m-%d"),
            }
        ],
    }


class QuickBooksWritebackAdapter:
    MOCK_MODE: bool = True

    def __init__(self) -> None:
        self.MOCK_MODE = not _is_real_mode("quickbooks")

    def create_bill(
        self,
        vendor_name: str,
        line_items: list[dict[str, Any]] | None = None,
        total_amount: float = 0.0,
        due_date: str | None = None,
    ) -> dict:
        if line_items is None:
            line_items = []
        due = due_date or datetime.utcnow().strftime("%Y-%m-%d")

        if self.MOCK_MODE:
            logger.info("QuickBooks mock: created bill for %s ($%.2f)", vendor_name, total_amount)
            return _build_mock_response("quickbooks", vendor_name, total_amount)

        payload = _build_qb_real_payload(vendor_name, line_items, total_amount, due)
        logger.info("QuickBooks real payload prepared for %s", vendor_name)
        return {
            "status": "real_mode_payload",
            "message": "QuickBooks API request prepared (OAuth flow not yet connected)",
            "payload": payload,
        }


class XeroWritebackAdapter:
    MOCK_MODE: bool = True

    def __init__(self) -> None:
        self.MOCK_MODE = not _is_real_mode("xero")

    def create_bill(
        self,
        vendor_name: str,
        line_items: list[dict[str, Any]] | None = None,
        total_amount: float = 0.0,
        due_date: str | None = None,
    ) -> dict:
        if line_items is None:
            line_items = []
        due = due_date or datetime.utcnow().strftime("%Y-%m-%d")

        if self.MOCK_MODE:
            logger.info("Xero mock: created bill for %s ($%.2f)", vendor_name, total_amount)
            return _build_mock_response("xero", vendor_name, total_amount)

        payload = _build_xero_real_payload(vendor_name, line_items, total_amount, due)
        logger.info("Xero real payload prepared for %s", vendor_name)
        return {
            "status": "real_mode_payload",
            "message": "Xero API request prepared (OAuth flow not yet connected)",
            "payload": payload,
        }
