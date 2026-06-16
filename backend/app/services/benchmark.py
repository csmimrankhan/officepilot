"""Phase 5 parser benchmark.

Given a list of (engine, golden_invoice) pairs, run each engine on
each invoice and compute per-field accuracy metrics. Output is a
JSON-friendly dict suitable for the API endpoint and the frontend
table, plus an optional CSV summary.

Metrics
-------
For each field we report:

- ``match``             — boolean: did the engine's value match the
                          expected value?
- ``expected``          — the expected value
- ``actual``            — the engine's value
- ``score``             — 1.0 (exact) / 0.5 (fuzzy) / 0.0 (mismatch/missing)

We also report:

- ``runtime_ms``        — wall-clock runtime for the engine call
- ``used_ocr``          — whether OCR was used
- ``text_source``       — what the engine reported as the text source
- ``warnings``          — list of warnings emitted by the engine
- ``confidence``        — per-field confidence from the engine
- ``notes``             — free-form notes (e.g. "docling not installed")
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from .engines import EngineResult
from .engines.registry import AVAILABLE_ENGINES, get_engine

logger = logging.getLogger(__name__)


@dataclass
class FieldScore:
    expected: Any
    actual: Any
    match: bool
    score: float  # 0.0 / 0.5 / 1.0
    note: str = ""


@dataclass
class InvoiceRunResult:
    name: str
    file: str
    parser_engine: str
    runtime_ms: float
    used_ocr: bool
    text_source: str
    confidence: dict
    warnings: list[str]
    notes: list[str]
    fields: dict[str, FieldScore] = field(default_factory=dict)
    line_item_count: int = 0
    line_item_count_match: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fields"] = {k: asdict(v) for k, v in self.fields.items()}
        return d


# ----------------------------------------------------------- comparison helpers


def _norm_string(s: Any) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def _compare_string(expected: Any, actual: Any) -> tuple[bool, float, str]:
    e = _norm_string(expected)
    a = _norm_string(actual)
    if not e and not a:
        return True, 1.0, "both empty (treated as match)"
    if not e or not a:
        return False, 0.0, "missing"
    if e == a:
        return True, 1.0, "exact"
    if e in a or a in e:
        return True, 0.5, "fuzzy (substring match)"
    return False, 0.0, "mismatch"


def _compare_number(expected: Any, actual: Any, *, atol: float = 0.01) -> tuple[bool, float, str]:
    if expected is None and actual is None:
        return True, 1.0, "both null (match)"
    if expected is None or actual is None:
        return False, 0.0, "missing"
    try:
        e = float(expected)
        a = float(actual)
    except (TypeError, ValueError):
        return _compare_string(expected, actual)
    if abs(e - a) <= atol:
        return True, 1.0, "exact"
    if abs(e - a) <= max(0.05, atol * 10):  # within 5 cents
        return True, 0.5, "fuzzy (within 5 cents)"
    return False, 0.0, f"mismatch (Δ={round(a - e, 4)})"


def _compare_line_items(expected: list, actual: list) -> tuple[bool, int, str]:
    if not expected and not actual:
        return True, 0, "no line items expected or returned"
    if not expected or not actual:
        return False, len(actual), "missing"
    return len(expected) == len(actual), len(actual), f"expected {len(expected)}, got {len(actual)}"


# ----------------------------------------------------------- benchmark runner


def _golden_dir() -> Path:
    """Path to ``backend/tests/golden_invoices/``."""
    return Path(__file__).resolve().parents[2] / "tests" / "golden_invoices"


def _ensure_golden_fixtures() -> None:
    """Make sure the golden PDFs and ``golden.json`` exist on disk.

    The benchmark works on synthetic PDFs; if they're missing (fresh
    clone), we render them on demand via the same builder used in
    CI. We do this via subprocess so the benchmark module does not
    have to depend on the test-tree as a package.
    """
    import subprocess
    import sys

    golden = _golden_dir()
    if (golden / "golden.json").exists() and any((golden / f).exists() for f in (
        "alpha_office_supplies.pdf",
        "beta_logistics.pdf",
        "gamma_consulting.pdf",
    )):
        return
    script = golden / "build_golden.py"
    if not script.exists():
        raise FileNotFoundError(f"golden fixture builder missing: {script}")
    subprocess.run([sys.executable, str(script)], check=True)


def run_benchmark(
    settings,
    engines: Optional[Iterable[str]] = None,
    fixtures: Optional[list[dict]] = None,
) -> dict:
    """Run the benchmark for the requested engines on the golden set.

    ``engines`` is an iterable of engine names. ``None`` means "all".
    ``fixtures`` is an iterable of expected dicts; ``None`` reads
    ``tests/golden_invoices/golden.json`` (and rebuilds it if missing).
    """
    if fixtures is None:
        _ensure_golden_fixtures()
        golden_path = _golden_dir() / "golden.json"
        fixtures = list(json.loads(golden_path.read_text(encoding="utf-8")).values())
    if engines is None:
        engines = list(AVAILABLE_ENGINES.keys())

    fixtures_dir = _golden_dir()

    runs: list[InvoiceRunResult] = []
    for engine_name in engines:
        try:
            engine = get_engine(engine_name, settings)
        except Exception as exc:
            logger.warning("could not instantiate %s: %s", engine_name, exc)
            continue
        for fixture in fixtures:
            pdf_path = fixtures_dir / fixture["file"]
            if not pdf_path.exists():
                _ensure_golden_fixtures()
            run_result = _run_one(engine, fixture, pdf_path)
            runs.append(run_result)

    engines_used = sorted({r.parser_engine for r in runs})
    summary: dict[str, dict] = {}
    for eng in engines_used:
        eng_runs = [r for r in runs if r.parser_engine == eng]
        summary[eng] = _summarize(eng, eng_runs)

    return {
        "engines": engines_used,
        "summary": summary,
        "runs": [r.to_dict() for r in runs],
    }


def _run_one(engine, fixture: dict, pdf_path: Path) -> InvoiceRunResult:
    mime = fixture.get("mime_type") or "application/pdf"
    er: EngineResult = engine.extract_structure(pdf_path, mime)
    p = er.parsed

    fields: dict[str, FieldScore] = {}

    for fld, expected in [
        ("vendor_name", fixture.get("vendor_name")),
        ("invoice_number", fixture.get("invoice_number")),
        ("invoice_date", fixture.get("invoice_date")),
        ("due_date", fixture.get("due_date")),
        ("currency", fixture.get("currency")),
        ("subtotal", fixture.get("subtotal")),
        ("tax", fixture.get("tax")),
        ("total_amount", fixture.get("total_amount")),
    ]:
        actual = getattr(p, fld, None)
        if fld in ("subtotal", "tax", "total_amount"):
            ok, score, note = _compare_number(expected, actual)
        else:
            ok, score, note = _compare_string(expected, actual)
        fields[fld] = FieldScore(expected=expected, actual=actual, match=ok, score=score, note=note)

    li_match, li_count, li_note = _compare_line_items(
        fixture.get("line_items") or [],
        [li.__dict__ for li in p.line_items],
    )

    conf_dict = er.confidence.as_dict() if hasattr(er.confidence, "as_dict") else {}

    return InvoiceRunResult(
        name=Path(fixture["file"]).stem,
        file=fixture["file"],
        parser_engine=engine.name,
        runtime_ms=er.runtime_ms,
        used_ocr=er.used_ocr,
        text_source=er.text_source,
        confidence=conf_dict,
        warnings=list(er.warnings),
        notes=list(er.notes),
        fields=fields,
        line_item_count=li_count,
        line_item_count_match=li_match,
    )


def _summarize(engine: str, runs: list[InvoiceRunResult]) -> dict:
    if not runs:
        return {"engine": engine, "runs": 0}
    field_keys = list(runs[0].fields.keys())
    per_field: dict[str, dict] = {}
    for k in field_keys:
        scores = [r.fields[k].score for r in runs if k in r.fields]
        matches = sum(1 for r in runs if r.fields[k].match)
        per_field[k] = {
            "accuracy": round(matches / max(1, len(runs)), 3),
            "avg_score": round(sum(scores) / max(1, len(scores)), 3),
        }
    line_counts = [r.line_item_count_match for r in runs]
    runtimes = [r.runtime_ms for r in runs]
    ocr_runs = sum(1 for r in runs if r.used_ocr)
    warnings_flat = sum(len(r.warnings) for r in runs)
    return {
        "engine": engine,
        "runs": len(runs),
        "field_accuracy": per_field,
        "line_item_count_accuracy": round(sum(line_counts) / max(1, len(runs)), 3),
        "avg_runtime_ms": round(sum(runtimes) / max(1, len(runtimes)), 2),
        "ocr_used_pct": round(ocr_runs / max(1, len(runs)), 3),
        "total_warnings": warnings_flat,
    }


# ----------------------------------------------------------- CSV export


def to_csv(report: dict) -> str:
    """Render the benchmark report as a flat CSV, one row per
    (engine, invoice) pair, with each field's match as its own
    column. The summary is appended as a second block."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "engine",
            "fixture",
            "file",
            "runtime_ms",
            "used_ocr",
            "text_source",
            "vendor_match",
            "invoice_number_match",
            "invoice_date_match",
            "due_date_match",
            "currency_match",
            "subtotal_match",
            "tax_match",
            "total_amount_match",
            "line_item_count",
            "line_item_count_match",
            "warnings",
        ]
    )
    for r in report.get("runs", []):
        writer.writerow(
            [
                r["parser_engine"],
                r["name"],
                r["file"],
                r["runtime_ms"],
                r["used_ocr"],
                r["text_source"],
                r["fields"].get("vendor_name", {}).get("match"),
                r["fields"].get("invoice_number", {}).get("match"),
                r["fields"].get("invoice_date", {}).get("match"),
                r["fields"].get("due_date", {}).get("match"),
                r["fields"].get("currency", {}).get("match"),
                r["fields"].get("subtotal", {}).get("match"),
                r["fields"].get("tax", {}).get("match"),
                r["fields"].get("total_amount", {}).get("match"),
                r["line_item_count"],
                r["line_item_count_match"],
                "; ".join(r.get("warnings", [])),
            ]
        )
    writer.writerow([])
    writer.writerow(["# Per-engine summary"])
    writer.writerow(
        [
            "engine",
            "runs",
            "line_item_count_accuracy",
            "avg_runtime_ms",
            "ocr_used_pct",
            "total_warnings",
        ]
    )
    for eng, s in report.get("summary", {}).items():
        writer.writerow(
            [
                eng,
                s.get("runs"),
                s.get("line_item_count_accuracy"),
                s.get("avg_runtime_ms"),
                s.get("ocr_used_pct"),
                s.get("total_warnings"),
            ]
        )
    return buf.getvalue()
