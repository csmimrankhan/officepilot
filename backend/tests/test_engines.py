"""Tests for the Phase 5 parser engines."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.config import Settings, get_settings
from app.services.engines import EngineResult, InvoiceParserEngine, ParserConfidence
from app.services.engines.docling_engine import DoclingParserEngine
from app.services.engines.existing_engine import ExistingParserEngine
from app.services.engines.hybrid_engine import HybridParserEngine
from app.services.engines.ocr_engine import OCRParserEngine
from app.services.engines.registry import AVAILABLE_ENGINES, get_engine, list_engines


# ----------------------------------------------------------------- registry


def test_registry_has_expected_engines():
    assert set(AVAILABLE_ENGINES.keys()) == {"existing", "docling", "ocr", "hybrid"}


def test_list_engines_returns_serialisable_dicts():
    payload = list_engines()
    assert isinstance(payload, list)
    for entry in payload:
        assert "name" in entry
        assert "class" in entry
        assert entry["name"] in AVAILABLE_ENGINES


def test_get_engine_returns_typed_object():
    s = get_settings()
    for name in AVAILABLE_ENGINES:
        e = get_engine(name, s)
        assert isinstance(e, InvoiceParserEngine)
        assert e.name == name


def test_get_engine_unknown_name_falls_back_to_existing():
    s = get_settings()
    e = get_engine("not-a-real-engine", s)
    assert isinstance(e, ExistingParserEngine)


def test_default_parser_engine_setting_is_existing():
    s = get_settings()
    assert s.parser_engine == "existing"


def test_parser_engine_setting_can_be_overridden(monkeypatch):
    monkeypatch.setenv("OFFICEPILOT_PARSER_ENGINE", "docling")
    from app.config import _settings_singleton
    _settings_singleton.cache_clear()
    s = get_settings()
    assert s.parser_engine == "docling"
    _settings_singleton.cache_clear()


# ----------------------------------------------------------------- existing


def test_existing_engine_handles_pdf_golden(tmp_path, golden_pdf):
    s = get_settings()
    e = ExistingParserEngine(s)
    er = e.extract_structure(golden_pdf, "application/pdf")
    assert isinstance(er, EngineResult)
    assert er.parsed.vendor_name
    assert er.parsed.total_amount is not None
    assert er.runtime_ms >= 0
    assert er.text_source  # pymupdf / pdfplumber / ocr / etc.


def test_existing_engine_handles_text(tmp_path):
    s = get_settings()
    p = tmp_path / "inv.txt"
    p.write_text(
        "Acme\nINVOICE\nInvoice Number: INV-001\nInvoice Date: 2026-01-01\n"
        "Total: 100.00\n",
        encoding="utf-8",
    )
    e = ExistingParserEngine(s)
    er = e.extract_structure(p, "text/plain")
    assert er.parsed.invoice_number == "INV-001"
    assert er.parsed.total_amount == 100.0
    assert er.text_source == "plain"
    assert er.used_ocr is False


def test_existing_engine_supports_common_mime_types():
    s = get_settings()
    e = ExistingParserEngine(s)
    for mt in ("application/pdf", "image/png", "image/jpeg", "text/plain"):
        assert e.supports(mt)
    assert not e.supports("application/zip")


def test_existing_engine_confidence_report_after_run(golden_pdf):
    s = get_settings()
    e = ExistingParserEngine(s)
    e.extract_structure(golden_pdf, "application/pdf")
    report = e.confidence_report()
    assert report["engine"] == "existing"
    assert "per_field" in report


# ----------------------------------------------------------------- ocring


def test_ocr_engine_warns_when_no_backend(tmp_path, golden_pdf):
    """When neither PaddleOCR nor Tesseract is importable, the OCR
    engine should still return a result (degraded) with a warning
    rather than raising."""
    s = get_settings()
    e = OCRParserEngine(s)
    backend = e._detect_backend()
    er = e.extract_structure(golden_pdf, "application/pdf")
    # No OCR backend is guaranteed on a fresh machine; we should
    # at least see a warning and a valid EngineResult.
    assert isinstance(er, EngineResult)
    if backend == "unavailable":
        assert any("OCR" in w or "tesseract" in w.lower() or "paddle" in w.lower() or "unavailable" in w.lower() for w in er.warnings + er.notes)
        assert er.used_ocr is False


# ----------------------------------------------------------------- docling


def test_docling_engine_falls_back_gracefully(tmp_path, golden_pdf):
    """Docling is not installed in this env; the engine must fall
    back to the existing pipeline and emit a warning."""
    s = get_settings()
    e = DoclingParserEngine(s)
    have = e._have_docling()
    er = e.extract_structure(golden_pdf, "application/pdf")
    assert isinstance(er, EngineResult)
    # Either Docling produced a real result OR we fell back — both
    # are valid; the engine must not raise.
    if not have:
        assert any("docling" in w.lower() or "fallback" in w.lower() for w in er.warnings + er.notes)


# ----------------------------------------------------------------- hybrid


def test_hybrid_engine_returns_engine_result(tmp_path, golden_pdf):
    s = get_settings()
    e = HybridParserEngine(s)
    er = e.extract_structure(golden_pdf, "application/pdf")
    assert isinstance(er, EngineResult)
    # Hybrid always produces a parsed invoice.
    assert er.parsed is not None
    # And it must have a non-empty raw_text (used for line_count).
    assert er.raw_text


def test_hybrid_engine_reconciles_per_field(tmp_path):
    """The hybrid engine should pick the most plausible value when
    sub-engines disagree, by trusting the one with higher per-field
    confidence. We feed it two synthetic EngineResults by patching
    the sub-engine list."""
    from app.services.engines import EngineResult, ParserConfidence
    from app.services.parser import ParsedInvoice, ParsedLineItem

    class _FakeA:
        name = "fakeA"
        def __init__(self):
            self.last = None
        def supports(self, mt): return True
        def extract_text(self, p, mt): return "raw A"
        def extract_structure(self, p, mt):
            self.last = (p, mt)
            return EngineResult(
                parsed=ParsedInvoice(
                    vendor_name="Vendor A", invoice_number="INV-A",
                    total_amount=100.0, subtotal=80.0, tax=20.0,
                ),
                confidence=ParserConfidence(
                    vendor_name=0.9, invoice_number=0.9,
                    total_amount=0.9, subtotal=0.9, tax=0.9,
                ),
                raw_text="raw A", text_source="fakeA",
            )
        def extract_invoice_fields(self, p, mt):
            return self.extract_structure(p, mt).parsed
        def confidence_report(self): return {}

    class _FakeB:
        name = "fakeB"
        def __init__(self):
            self.last = None
        def supports(self, mt): return True
        def extract_text(self, p, mt): return "raw B"
        def extract_structure(self, p, mt):
            self.last = (p, mt)
            return EngineResult(
                parsed=ParsedInvoice(
                    vendor_name="Vendor B", invoice_number="INV-B",
                    total_amount=200.0, subtotal=180.0, tax=20.0,
                ),
                confidence=ParserConfidence(
                    vendor_name=0.5, invoice_number=0.5,
                    total_amount=0.5, subtotal=0.5, tax=0.5,
                ),
                raw_text="raw B", text_source="fakeB",
            )
        def extract_invoice_fields(self, p, mt):
            return self.extract_structure(p, mt).parsed
        def confidence_report(self): return {}

    s = get_settings()
    e = HybridParserEngine(s, sub_engines=[_FakeA(), _FakeB()])
    er = e.extract_structure(Path("dummy.pdf"), "application/pdf")
    # The hybrid should pick the value from the higher-confidence sub-engine (A).
    assert er.parsed.vendor_name == "Vendor A"
    assert er.parsed.total_amount == 100.0
    # And it should warn about the disagreement.
    assert any("disagreement" in w.lower() or "hybrid" in w.lower() for w in er.warnings + er.notes)


def test_hybrid_engine_warns_on_subtotal_tax_mismatch(tmp_path):
    from app.services.engines import EngineResult, ParserConfidence
    from app.services.parser import ParsedInvoice

    class _FakeOne:
        name = "fake1"
        def supports(self, mt): return True
        def extract_text(self, p, mt): return ""
        def extract_structure(self, p, mt):
            return EngineResult(
                parsed=ParsedInvoice(
                    subtotal=100.0, tax=10.0, total_amount=200.0,  # mismatch
                ),
                confidence=ParserConfidence(
                    subtotal=0.9, tax=0.9, total_amount=0.9,
                ),
                raw_text="", text_source="fake1",
            )
        def extract_invoice_fields(self, p, mt): return self.extract_structure(p, mt).parsed
        def confidence_report(self): return {}

    s = get_settings()
    e = HybridParserEngine(s, sub_engines=[_FakeOne()])
    er = e.extract_structure(Path("dummy.pdf"), "application/pdf")
    assert any("subtotal+tax" in w.lower() or "mismatch" in w.lower() for w in er.warnings)


# ----------------------------------------------------------------- fixtures


@pytest.fixture()
def golden_pdf():
    """Return a path to a freshly-rendered golden PDF, building it if
    necessary. The PDFs themselves are gitignored."""
    from tests.golden_invoices.build_golden import build
    from pathlib import Path
    fixtures_dir = Path(__file__).resolve().parent / "golden_invoices"
    pdf = fixtures_dir / "alpha_office_supplies.pdf"
    if not pdf.exists():
        build()
    return pdf
