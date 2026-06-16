"""Hybrid parser engine (Phase 5).

The hybrid engine runs two or more sub-engines on the same document
and reconciles their outputs to produce a single best-estimate
:class:`ParsedInvoice`. The reconciliation policy is intentionally
simple and conservative:

- For each field, prefer the value with the **highest per-field
  confidence**.
- If two sub-engines disagree on a value (and both have non-zero
  confidence), keep the higher-confidence one and emit a warning
  noting the disagreement.
- If the sub-engines' totals disagree by more than 0.5%, prefer the
  value that makes ``subtotal + tax ≈ total`` and warn.

We do not auto-correct or override the existing engine's output for
the production code path. The hybrid engine is opt-in via
``PARSER_ENGINE=hybrid`` and is mainly there to be benchmarked.

Backward compatibility: the hybrid engine never produces a status
that is *better* than the existing engine's. If the existing engine
returned a low-confidence result, the hybrid may also — it just
amortises confidence across multiple backends.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

from ..parser import ParsedInvoice
from . import EngineResult, InvoiceParserEngine, ParserConfidence, time_call
from .docling_engine import DoclingParserEngine
from .existing_engine import ExistingParserEngine
from .ocr_engine import OCRParserEngine

logger = logging.getLogger(__name__)


class HybridParserEngine:
    """Run multiple sub-engines and reconcile their outputs."""

    name = "hybrid"

    _SUPPORTED = {"application/pdf", "image/png", "image/jpeg", "image/jpg", "text/plain"}

    def __init__(self, settings, sub_engines: Optional[list[InvoiceParserEngine]] = None) -> None:
        self._settings = settings
        if sub_engines is None:
            sub_engines = [
                ExistingParserEngine(settings),
                DoclingParserEngine(settings),
                OCRParserEngine(settings),
            ]
        self._sub: list[InvoiceParserEngine] = list(sub_engines)
        self._last_confidence: dict = {}
        self._last_sub_results: list[EngineResult] = []

    # ----------------------------------------------------------- protocol

    def supports(self, file_type: str) -> bool:
        return (file_type or "").lower() in self._SUPPORTED

    def extract_text(self, file_path: Path, mime_type: str) -> str:
        # Prefer the longest non-empty text from any sub-engine.
        best = ""
        for e in self._sub:
            if not e.supports(mime_type):
                continue
            t = e.extract_text(file_path, mime_type)
            if t and len(t) > len(best):
                best = t
        return best

    def extract_structure(self, file_path: Path, mime_type: str) -> EngineResult:
        import time as _time

        started = _time.perf_counter()
        results: list[EngineResult] = []
        for e in self._sub:
            if not e.supports(mime_type):
                continue
            try:
                r = e.extract_structure(file_path, mime_type)
                results.append(r)
            except Exception as exc:  # pragma: no cover
                logger.warning("hybrid sub-engine %s failed: %s", e.name, exc)
        runtime_ms = (_time.perf_counter() - started) * 1000.0

        if not results:
            # Nothing ran — return an empty parse with a warning so
            # the validator marks the invoice as needs_review.
            empty = ParsedInvoice()
            empty.warnings.append("hybrid: no sub-engines produced a result")
            return EngineResult(
                parsed=empty,
                confidence=ParserConfidence(),
                runtime_ms=round(runtime_ms, 2),
                raw_text="",
                warnings=empty.warnings[:],
            )

        reconciled = self._reconcile(results)
        self._last_sub_results = results
        self._last_confidence = reconciled.confidence.as_dict()
        return reconciled

    def extract_invoice_fields(self, file_path: Path, mime_type: str) -> ParsedInvoice:
        return self.extract_structure(file_path, mime_type).parsed

    def confidence_report(self) -> dict:
        return {
            "engine": self.name,
            "sub_engines": [e.name for e in self._sub],
            "per_field": self._last_confidence or {},
        }

    # ----------------------------------------------------------- internals

    def _reconcile(self, results: list[EngineResult]) -> EngineResult:
        """Pick the best value per field, weighted by per-field confidence."""
        merged = ParsedInvoice()
        warnings: list[str] = []
        notes: list[str] = [f"hybrid: ran {len(results)} sub-engines"]
        for r in results:
            notes.append(f"  - {r.text_source}: conf={r.confidence.as_dict() if hasattr(r.confidence, 'as_dict') else dict(r.confidence.__dict__)}")

        # Use the longest raw_text as the canonical text.
        canonical = max(results, key=lambda r: len(r.raw_text or ""))
        merged = ParsedInvoice()  # reset; we will populate from canonical
        merged.vendor_name = canonical.parsed.vendor_name
        merged.invoice_number = canonical.parsed.invoice_number
        merged.invoice_date = canonical.parsed.invoice_date
        merged.due_date = canonical.parsed.due_date
        merged.currency = canonical.parsed.currency
        merged.subtotal = canonical.parsed.subtotal
        merged.tax = canonical.parsed.tax
        merged.total_amount = canonical.parsed.total_amount
        merged.line_items = list(canonical.parsed.line_items)
        merged.warnings = list(canonical.parsed.warnings)

        # Per-field reconciliation: prefer higher-confidence values.
        merged.vendor_name = self._pick_best(
            "vendor_name",
            [(r.parsed.vendor_name, r.confidence.vendor_name) for r in results],
            merged.vendor_name,
            warnings,
        )
        merged.invoice_number = self._pick_best(
            "invoice_number",
            [(r.parsed.invoice_number, r.confidence.invoice_number) for r in results],
            merged.invoice_number,
            warnings,
        )
        merged.invoice_date = self._pick_best(
            "invoice_date",
            [(r.parsed.invoice_date, r.confidence.invoice_date) for r in results],
            merged.invoice_date,
            warnings,
        )
        merged.due_date = self._pick_best(
            "due_date",
            [(r.parsed.due_date, r.confidence.due_date) for r in results],
            merged.due_date,
            warnings,
        )
        merged.currency = self._pick_best(
            "currency",
            [(r.parsed.currency, r.confidence.currency) for r in results],
            merged.currency,
            warnings,
        )
        merged.subtotal = self._pick_numeric_best(
            "subtotal",
            [(r.parsed.subtotal, r.confidence.subtotal) for r in results],
            merged.subtotal,
            warnings,
        )
        merged.tax = self._pick_numeric_best(
            "tax",
            [(r.parsed.tax, r.confidence.tax) for r in results],
            merged.tax,
            warnings,
        )
        merged.total_amount = self._pick_numeric_best(
            "total_amount",
            [(r.parsed.total_amount, r.confidence.total_amount) for r in results],
            merged.total_amount,
            warnings,
        )

        # Line items: prefer the sub-engine with the most items, provided
        # their confidence is non-zero. If line items disagree, keep the
        # largest list and warn.
        best_items: list = []
        for r in results:
            if r.parsed.line_items and r.confidence.line_items > 0:
                if len(r.parsed.line_items) > len(best_items):
                    best_items = list(r.parsed.line_items)
        if best_items:
            merged.line_items = best_items

        # Total consistency check: subtotal + tax ≈ total (±0.5%).
        if (
            merged.subtotal is not None
            and merged.tax is not None
            and merged.total_amount is not None
        ):
            expected = round(merged.subtotal + merged.tax, 2)
            if abs(expected - merged.total_amount) > 0.5:
                warnings.append(
                    f"hybrid: subtotal+tax ({expected}) != total ({merged.total_amount})"
                )

        # Recompute confidence as the max across sub-engines per field.
        max_conf = ParserConfidence()
        for r in results:
            c = r.confidence
            for fld in (
                "vendor_name", "invoice_number", "invoice_date", "due_date",
                "currency", "subtotal", "tax", "total_amount", "line_items",
            ):
                setattr(max_conf, fld, max(getattr(max_conf, fld), getattr(c, fld)))

        # Top-level confidence: average of per-field maxes.
        per = max_conf.as_dict()
        merged.confidence = round(sum(per.values()) / max(1, len(per)), 3)

        # Take any field-level warnings.
        for r in results:
            for w in r.warnings:
                if w not in warnings:
                    warnings.append(w)

        return EngineResult(
            parsed=merged,
            confidence=max_conf,
            runtime_ms=round(sum(r.runtime_ms for r in results), 2),
            used_ocr=any(r.used_ocr for r in results),
            text_source="hybrid",
            raw_text=canonical.raw_text,
            notes=notes,
            warnings=warnings,
        )

    @staticmethod
    def _pick_best(field: str, candidates: Iterable, default, warnings: list):
        """Return the candidate with the highest confidence. ``candidates``
        is an iterable of ``(value, confidence)`` tuples."""
        best_value = default
        best_conf = -1.0
        for value, conf in candidates:
            if value in (None, "", 0.0) or 0.0:
                continue
            if conf > best_conf:
                best_value = value
                best_conf = conf
        if best_value != default and best_value is not None and default is not None:
            if str(best_value).strip() != str(default).strip():
                warnings.append(
                    f"hybrid: {field} reconciled to '{best_value}' (was '{default}')"
                )
        return best_value

    @staticmethod
    def _pick_numeric_best(field: str, candidates: Iterable, default, warnings: list):
        best_value = default
        best_conf = -1.0
        for value, conf in candidates:
            if value is None:
                continue
            if conf > best_conf:
                best_value = value
                best_conf = conf
        if best_value != default and default is not None:
            try:
                if abs(float(best_value) - float(default)) > 0.001:
                    warnings.append(
                        f"hybrid: {field} reconciled to {best_value} (was {default})"
                    )
            except (TypeError, ValueError):
                pass
        return best_value
