"""Tests for the heuristic invoice parser."""

from app.services.parser import parse_invoice_text
from tests.conftest import SAMPLE_NO_TOTAL, SAMPLE_TEXT_INVOICE


def test_parse_full_invoice():
    p = parse_invoice_text(SAMPLE_TEXT_INVOICE)
    assert p.vendor_name and "ACME" in p.vendor_name.upper()
    assert p.invoice_number == "INV-2026-0042"
    assert p.invoice_date and p.invoice_date.startswith("2026-05-12")
    assert p.due_date and p.due_date.startswith("2026-06-11")
    assert p.currency == "USD"
    assert p.subtotal == 430.5
    assert p.tax == 30.14
    assert p.total_amount == 460.64
    assert len(p.line_items) == 3
    assert p.line_items[0].description.startswith("Printer Paper")
    assert p.confidence >= 0.9
    assert not any("missing" in w for w in p.warnings)


def test_parse_missing_total_marks_warning():
    p = parse_invoice_text(SAMPLE_NO_TOTAL)
    assert p.invoice_number == "BL-001"
    assert p.total_amount is None
    assert any("total_amount" in w for w in p.warnings)
    assert any("Missing required fields" in w or "total_amount missing" in w for w in p.warnings)


def test_parse_empty_text():
    p = parse_invoice_text("")
    assert p.warnings == ["No text to parse"]
    assert p.confidence == 0.0


def test_parse_handles_currency_symbol_only():
    text = "Vendor: X\nInvoice No: 1\nDate: 2026-01-01\nTotal: €1,234.50\n"
    p = parse_invoice_text(text)
    assert p.currency == "EUR"
    assert p.total_amount == 1234.50


def test_parse_warns_on_line_item_subtotal_mismatch():
    text = (
        "Vendor: X\nInvoice No: 1\nDate: 2026-01-01\n"
        "Item A 1 10.00 10.00\n"
        "Item B 1 10.00 10.00\n"
        "Subtotal: 50.00\nTotal: 50.00\n"
    )
    p = parse_invoice_text(text)
    assert p.subtotal == 50.0
    assert any("subtotal" in w for w in p.warnings)
