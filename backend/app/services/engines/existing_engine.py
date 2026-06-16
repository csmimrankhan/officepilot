"""Existing parser engine (Phase 1-3 pipeline).

This engine is the **default** in production. It wraps the
PyMuPDF/pdfplumber/OCR + regex pipeline that has shipped since Phase 1.
We are not modifying it; we are wrapping it so that it can be
benchmarked side-by-side with Docling, OCR-only, and Hybrid engines.

Backward compatibility: every existing test must still pass when
``PARSER_ENGINE=existing`` (the default).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..parser import ParsedInvoice, parse_invoice_text
from ..text_extraction import extract_text as text_extract
from .. import text_extraction
from . import EngineResult, InvoiceParserEngine, ParserConfidence, time_call

logger = logging.getLogger(__name__)


class ExistingParserEngine:
    """Wraps the Phase 1-3 pipeline as an :class:`InvoiceParserEngine`."""

    name = "existing"

    # MIME types this engine can handle.
    _SUPPORTED = {"application/pdf", "image/png", "image/jpeg", "image/jpg", "text/plain"}

    def __init__(self, settings) -> None:
        self._settings = settings
        self._last_confidence: dict = {}

    # ----------------------------------------------------------- protocol

    def supports(self, file_type: str) -> bool:
        return (file_type or "").lower() in self._SUPPORTED

    def extract_text(self, file_path: Path, mime_type: str) -> str:
        # For plain text, just read the file.
        if mime_type == "text/plain":
            try:
                return Path(file_path).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return ""
        result = text_extract(Path(file_path), mime_type, self._settings)
        return result.text

    def extract_structure(self, file_path: Path, mime_type: str) -> EngineResult:
        notes: list[str] = []
        warnings: list[str] = []
        started_perf = __import__("time").perf_counter()

        # 1) text extraction (PDFs / images via the existing pipeline)
        if mime_type == "text/plain":
            text = self.extract_text(file_path, mime_type)
            ext_source = "plain"
            used_ocr = False
        else:
            ext = text_extract(Path(file_path), mime_type, self._settings)
            text = ext.text
            ext_source = ext.source
            used_ocr = ext.used_ocr
            notes.extend(ext.notes)

        # 2) regex parser
        parsed, parse_ms = time_call(parse_invoice_text, text)
        runtime_ms = (__import__("time").perf_counter() - started_perf) * 1000.0

        # 3) per-field confidence — derived from parser.confidence
        c = parsed.confidence
        conf = ParserConfidence(
            vendor_name=0.9 if parsed.vendor_name else 0.0,
            invoice_number=0.95 if parsed.invoice_number else 0.0,
            invoice_date=0.9 if parsed.invoice_date else 0.0,
            due_date=0.85 if parsed.due_date else 0.0,
            currency=0.9 if parsed.currency else 0.0,
            subtotal=0.85 if parsed.subtotal is not None else 0.0,
            tax=0.85 if parsed.tax is not None else 0.0,
            total_amount=0.95 if parsed.total_amount is not None else 0.0,
            line_items=0.8 if parsed.line_items else 0.0,
        )
        warnings.extend(parsed.warnings)

        self._last_confidence = conf.as_dict()
        return EngineResult(
            parsed=parsed,
            confidence=conf,
            runtime_ms=round(runtime_ms, 2),
            used_ocr=used_ocr,
            text_source=ext_source,
            raw_text=text,
            notes=notes,
            warnings=warnings,
        )

    def extract_invoice_fields(self, file_path: Path, mime_type: str) -> ParsedInvoice:
        return self.extract_structure(file_path, mime_type).parsed

    def confidence_report(self) -> dict:
        return {
            "engine": self.name,
            "per_field": self._last_confidence or {},
        }
