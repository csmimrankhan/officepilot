"""Tests for the Phase 5 cross-field validator (subtotal + tax ≈ total)."""

from __future__ import annotations

from app.config import get_settings
from app.models.invoice import InvoiceStatus
from app.services.parser import ParsedInvoice
from app.services.validator import validate_parsed


def _mk(subtotal, tax, total):
    return ParsedInvoice(
        vendor_name="V",
        invoice_number="X-1",
        invoice_date="2026-01-01",
        subtotal=subtotal,
        tax=tax,
        total_amount=total,
        confidence=0.9,
    )


def test_subtotal_tax_match_no_warning():
    s = get_settings()
    p = _mk(100.0, 10.0, 110.0)
    res = validate_parsed(p, s)
    # No mismatch warning expected.
    assert not any("Subtotal+tax" in w and "mismatch" in w for w in res.warnings)


def test_subtotal_tax_close_but_within_tolerance():
    s = get_settings()
    p = _mk(100.0, 10.0, 110.04)
    res = validate_parsed(p, s)
    # 4 cents is well under the 0.5% tolerance.
    assert not any("does not match" in w for w in res.warnings)


def test_subtotal_tax_far_off_emits_mismatch_warning():
    s = get_settings()
    p = _mk(100.0, 10.0, 200.0)
    res = validate_parsed(p, s)
    assert any("Subtotal+tax" in w and "does not match" in w for w in res.warnings)


def test_subtotal_tax_missing_values_no_check():
    s = get_settings()
    p = ParsedInvoice(
        vendor_name="V",
        invoice_number="X-1",
        invoice_date="2026-01-01",
        subtotal=None,
        tax=None,
        total_amount=100.0,
        confidence=0.9,
    )
    res = validate_parsed(p, s)
    # No cross-field check should fire when any of the three are missing.
    assert not any("Subtotal+tax" in w for w in res.warnings)


def test_missing_invoice_number_marks_needs_review():
    s = get_settings()
    p = ParsedInvoice(
        vendor_name="V",
        invoice_number="",
        invoice_date="2026-01-01",
        total_amount=100.0,
        confidence=0.9,
    )
    res = validate_parsed(p, s)
    assert res.status == InvoiceStatus.NEEDS_REVIEW
    assert any("invoice_number" in w for w in res.warnings)
