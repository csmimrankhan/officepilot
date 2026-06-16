"""Tests for the validator."""

from app.config import get_settings
from app.models.invoice import InvoiceStatus
from app.services.parser import parse_invoice_text
from app.services.validator import validate_parsed
from tests.conftest import SAMPLE_NO_TOTAL, SAMPLE_TEXT_INVOICE


def test_full_invoice_becomes_ready_for_approval_not_approved():
    settings = get_settings()
    parsed = parse_invoice_text(SAMPLE_TEXT_INVOICE)
    res = validate_parsed(parsed, settings)
    assert res.status == InvoiceStatus.READY_FOR_APPROVAL
    assert res.confidence_score >= 0.9
    assert res.warnings == []


def test_missing_total_marks_needs_review():
    settings = get_settings()
    parsed = parse_invoice_text(SAMPLE_NO_TOTAL)
    res = validate_parsed(parsed, settings)
    assert res.status == InvoiceStatus.NEEDS_REVIEW
    assert any("total_amount" in w for w in res.warnings)


def test_low_confidence_marks_needs_review():
    settings = get_settings()
    # Force confidence under threshold by stripping required fields.
    from app.services.parser import ParsedInvoice
    parsed = ParsedInvoice(vendor_name="X", confidence=0.1, warnings=[])
    res = validate_parsed(parsed, settings)
    assert res.status == InvoiceStatus.NEEDS_REVIEW


def test_validator_never_sets_approved_or_rejected():
    """Approved/rejected are *user* actions; the validator must not set them."""
    settings = get_settings()
    parsed = parse_invoice_text(SAMPLE_TEXT_INVOICE)
    res = validate_parsed(parsed, settings)
    assert res.status not in (InvoiceStatus.APPROVED, InvoiceStatus.REJECTED, InvoiceStatus.DUPLICATE)
