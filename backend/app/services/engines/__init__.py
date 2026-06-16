"""Parser engine protocol and shared types (Phase 5).

The :class:`InvoiceParserEngine` Protocol defines a uniform interface that
multiple backends (regex, Docling, OCR, hybrid) implement. The default
production behavior is still the regex/PyMuPDF/pdfplumber pipeline; the
new engines are introduced behind a ``PARSER_ENGINE`` setting so that we
can A/B compare them on the same set of golden invoices.

This file is intentionally tiny. Concrete engines live in
:mod:`app.services.engines`.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from ..parser import ParsedInvoice

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------- shared types


@dataclass
class ParserConfidence:
    """Per-field confidence reported by an engine.

    Used by the hybrid engine for reconciliation and by the benchmark
    to score each parser's outputs.
    """

    vendor_name: float = 0.0
    invoice_number: float = 0.0
    invoice_date: float = 0.0
    due_date: float = 0.0
    currency: float = 0.0
    subtotal: float = 0.0
    tax: float = 0.0
    total_amount: float = 0.0
    line_items: float = 0.0

    def as_dict(self) -> dict:
        return {
            "vendor_name": round(self.vendor_name, 3),
            "invoice_number": round(self.invoice_number, 3),
            "invoice_date": round(self.invoice_date, 3),
            "due_date": round(self.due_date, 3),
            "currency": round(self.currency, 3),
            "subtotal": round(self.subtotal, 3),
            "tax": round(self.tax, 3),
            "total_amount": round(self.total_amount, 3),
            "line_items": round(self.line_items, 3),
        }


@dataclass
class EngineResult:
    """The output of a single engine invocation.

    The engine fills in :attr:`parsed` and ideally :attr:`confidence`. The
    surrounding :func:`app.services.extraction.extract_and_persist` is
    responsible for the rest (validation, persistence, audit log).
    """

    parsed: ParsedInvoice
    confidence: ParserConfidence = field(default_factory=ParserConfidence)
    runtime_ms: float = 0.0
    used_ocr: bool = False
    text_source: str = "unknown"
    raw_text: str = ""
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ----------------------------------------------------------------- engine protocol


@runtime_checkable
class InvoiceParserEngine(Protocol):
    """Uniform interface for invoice-parsing backends.

    Every engine must be a callable object that takes a file path and
    returns an :class:`EngineResult`. The interface is intentionally
    minimal so that adding a new backend (e.g. a hosted LLM) is a
    one-class change.
    """

    name: str

    def supports(self, file_type: str) -> bool:
        """Return True if this engine can handle ``file_type``.

        ``file_type`` is the lowercase MIME type (e.g. ``"application/pdf"``,
        ``"image/jpeg"``). Engines that work on raw text should accept
        ``"text/plain"``.
        """
        ...

    def extract_text(self, file_path: Path, mime_type: str) -> str:
        """Return the raw text extracted from the document.

        Used by the hybrid engine to feed downstream parsers, and by
        the benchmark to compute character-level metrics.
        """
        ...

    def extract_structure(self, file_path: Path, mime_type: str) -> EngineResult:
        """Run the engine's full pipeline and return a populated
        :class:`EngineResult` with raw text, parsed fields, confidence,
        and timing.

        The hybrid engine uses this to compare multiple engines'
        outputs.
        """
        ...

    def extract_invoice_fields(self, file_path: Path, mime_type: str) -> ParsedInvoice:
        """Convenience wrapper for the production path: extract and
        return only the :class:`ParsedInvoice`."""
        ...

    def confidence_report(self) -> dict:
        """Return a small JSON-serialisable summary of the engine's
        last run. Used by the benchmark."""
        ...


# ----------------------------------------------------------------- helpers


def time_call(fn, *args, **kwargs) -> tuple[object, float]:
    """Run ``fn(*args, **kwargs)`` and return ``(result, elapsed_ms)``."""
    started = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = (time.perf_counter() - started) * 1000.0
    return result, elapsed


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0
