"""Docling parser engine (Phase 5).

Docling is the Phase 5 upgrade path noted in
:mod:`research.toolkit-spikes`. Its layout-aware model is significantly
better than regex on dense tables, but the install footprint is large
(PyTorch + a layout-model checkpoint). This engine degrades gracefully:

- If ``docling`` is importable, run the real :class:`DocumentConverter`
  pipeline and feed the result through the same regex parser.
- If it is not importable, fall back to the existing engine's text
  extraction and emit a clear warning.

The engine never breaks Phase 1-3 behavior. If Docling fails, the
:class:`app.services.validator` marks the invoice as
``needs_review``, exactly like the existing pipeline would.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..parser import ParsedInvoice, parse_invoice_text
from . import EngineResult, InvoiceParserEngine, ParserConfidence, time_call

logger = logging.getLogger(__name__)


class DoclingParserEngine:
    """Docling-backed parser. Falls back gracefully when Docling is missing."""

    name = "docling"

    _SUPPORTED = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}

    def __init__(self, settings) -> None:
        self._settings = settings
        self._last_confidence: dict = {}
        self._docling_available: Optional[bool] = None

    # ----------------------------------------------------------- detection

    def _have_docling(self) -> bool:
        if self._docling_available is not None:
            return self._docling_available
        try:
            import docling.document_converter  # noqa: F401
            self._docling_available = True
        except Exception:
            self._docling_available = False
        return self._docling_available

    # ----------------------------------------------------------- protocol

    def supports(self, file_type: str) -> bool:
        return (file_type or "").lower() in self._SUPPORTED

    def extract_text(self, file_path: Path, mime_type: str) -> str:
        text, _ = self._docling_text(file_path, mime_type)
        return text

    def extract_structure(self, file_path: Path, mime_type: str) -> EngineResult:
        import time as _time

        notes: list[str] = []
        warnings: list[str] = []
        started = _time.perf_counter()
        text, used_fallback = self._docling_text(Path(file_path), mime_type, notes, warnings)
        runtime_ms = (_time.perf_counter() - started) * 1000.0

        parsed, _parse_ms = time_call(parse_invoice_text, text)
        conf = ParserConfidence(
            vendor_name=0.95 if parsed.vendor_name else 0.0,
            invoice_number=0.95 if parsed.invoice_number else 0.0,
            invoice_date=0.9 if parsed.invoice_date else 0.0,
            due_date=0.9 if parsed.due_date else 0.0,
            currency=0.95 if parsed.currency else 0.0,
            subtotal=0.95 if parsed.subtotal is not None else 0.0,
            tax=0.9 if parsed.tax is not None else 0.0,
            total_amount=0.95 if parsed.total_amount is not None else 0.0,
            line_items=0.95 if parsed.line_items else 0.0,
        )
        warnings.extend(parsed.warnings)
        if used_fallback:
            warnings.append("Docling not installed; fell back to existing pipeline")

        self._last_confidence = conf.as_dict()
        return EngineResult(
            parsed=parsed,
            confidence=conf,
            runtime_ms=round(runtime_ms, 2),
            used_ocr=False,
            text_source="docling" if not used_fallback else "fallback",
            raw_text=text,
            notes=notes,
            warnings=warnings,
        )

    def extract_invoice_fields(self, file_path: Path, mime_type: str) -> ParsedInvoice:
        return self.extract_structure(file_path, mime_type).parsed

    def confidence_report(self) -> dict:
        return {
            "engine": self.name,
            "docling_available": self._have_docling(),
            "per_field": self._last_confidence or {},
        }

    # ----------------------------------------------------------- internals

    def _docling_text(
        self,
        file_path: Path,
        mime_type: str,
        notes: list | None = None,
        warnings: list | None = None,
    ) -> tuple[str, bool]:
        """Return ``(text, used_fallback)``."""
        if notes is None:
            notes = []
        if warnings is None:
            warnings = []

        if not self._have_docling():
            # Fall back to the existing engine's text extraction so the
            # parse path is still exercised.
            from .. import text_extraction
            ext = text_extraction.extract_text(file_path, mime_type, self._settings)
            notes.append(f"docling fallback to {ext.source}")
            return ext.text, True

        try:
            from docling.document_converter import DocumentConverter  # type: ignore
            converter = DocumentConverter()
            result = converter.convert(str(file_path))
            doc = result.document
            text = doc.export_to_text() if hasattr(doc, "export_to_text") else ""
            if not text.strip():
                notes.append("docling returned empty text; falling back")
                from .. import text_extraction
                ext = text_extraction.extract_text(file_path, mime_type, self._settings)
                return ext.text, True
            return text, False
        except Exception as exc:
            warnings.append(f"docling failed: {exc}")
            from .. import text_extraction
            ext = text_extraction.extract_text(file_path, mime_type, self._settings)
            return ext.text, True
