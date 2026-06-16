"""Tests for the Phase 5 parser benchmark runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import get_settings
from app.services.benchmark import (
    _compare_line_items,
    _compare_number,
    _compare_string,
    run_benchmark,
    to_csv,
)


# ----------------------------------------------------------------- comparison helpers


def test_compare_string_exact():
    ok, score, note = _compare_string("Alpha", "Alpha")
    assert ok and score == 1.0
    assert note == "exact"


def test_compare_string_case_insensitive():
    ok, score, _ = _compare_string("Alpha", "ALPHA")
    assert ok and score == 1.0


def test_compare_string_fuzzy_substring():
    ok, score, note = _compare_string("Alpha Office", "Alpha Office Supplies")
    assert ok and score == 0.5
    assert "substring" in note


def test_compare_string_mismatch():
    ok, score, _ = _compare_string("Foo", "Bar")
    assert not ok and score == 0.0


def test_compare_string_both_empty():
    ok, score, _ = _compare_string("", "")
    assert ok and score == 1.0


def test_compare_string_missing():
    ok, score, _ = _compare_string("Foo", None)
    assert not ok and score == 0.0


def test_compare_number_within_cent():
    ok, score, _ = _compare_number(100.00, 100.005)
    assert ok and score == 1.0


def test_compare_number_within_5_cents_fuzzy():
    ok, score, note = _compare_number(100.00, 100.04)
    assert ok and score == 0.5
    assert "fuzzy" in note


def test_compare_number_exceeds_tolerance():
    ok, score, note = _compare_number(100.00, 105.00)
    assert not ok and score == 0.0
    assert "mismatch" in note


def test_compare_line_items_match():
    ok, count, _ = _compare_line_items([1, 2, 3], ["a", "b", "c"])
    assert ok and count == 3


def test_compare_line_items_both_empty():
    ok, count, _ = _compare_line_items([], [])
    assert ok and count == 0


def test_compare_line_items_missing_actual():
    ok, count, _ = _compare_line_items([1], [])
    assert not ok and count == 0


# ----------------------------------------------------------------- benchmark runner


def test_run_benchmark_runs_existing_engine_on_golden_set():
    s = get_settings()
    r = run_benchmark(s, engines=["existing"])
    assert r["engines"] == ["existing"]
    assert len(r["runs"]) == 3
    assert "existing" in r["summary"]
    sm = r["summary"]["existing"]
    assert sm["runs"] == 3
    # On our golden set, the existing engine should achieve 100% on
    # the basic fields (vendor, invoice_number, total, etc.).
    fa = sm["field_accuracy"]
    assert fa["invoice_number"]["accuracy"] == 1.0
    assert fa["total_amount"]["accuracy"] == 1.0
    assert fa["subtotal"]["accuracy"] == 1.0
    assert fa["tax"]["accuracy"] == 1.0


def test_run_benchmark_hybrid_uses_sub_engines():
    s = get_settings()
    r = run_benchmark(s, engines=["hybrid"])
    assert r["engines"] == ["hybrid"]
    # Hybrid may emit cross-check warnings; we just assert the structure.
    for run in r["runs"]:
        assert "fields" in run
        assert "warnings" in run
        assert run["parser_engine"] == "hybrid"


def test_run_benchmark_ocr_handles_no_backend():
    s = get_settings()
    r = run_benchmark(s, engines=["ocr"])
    # OCR should still return a result, even with no backend.
    assert r["engines"] == ["ocr"]
    for run in r["runs"]:
        assert "warnings" in run


def test_run_benchmark_all_engines():
    s = get_settings()
    r = run_benchmark(s)
    # We should see all 4 engines in the report.
    for name in ("existing", "docling", "ocr", "hybrid"):
        assert name in r["summary"]


def test_run_benchmark_csv_is_well_formed():
    s = get_settings()
    r = run_benchmark(s, engines=["existing"])
    csv_text = to_csv(r)
    lines = csv_text.strip().splitlines()
    # Header + 3 runs + blank + summary header + summary header + 1 summary
    assert any("engine" in line and "fixture" in line for line in lines[:3])
    assert any("Per-engine summary" in line for line in lines)
    # The CSV should be importable as csv.
    import csv as csvmod
    import io
    rows = list(csvmod.reader(io.StringIO(csv_text)))
    assert rows[0][0] == "engine"
    assert rows[0][1] == "fixture"


def test_run_benchmark_uses_fixtures_argument_directly():
    """When fixtures are passed explicitly (not loaded from disk),
    the benchmark should not depend on the golden-invoice directory
    at all. We just check that the structure of the report is
    correct — even if the PDF doesn't exist, the engine must
    gracefully produce a degraded run for that fixture."""
    s = get_settings()
    fixtures = [
        {
            "file": "nonexistent.pdf",  # forces the engine to degrade
            "mime_type": "application/pdf",
            "vendor_name": "X",
            "invoice_number": "X-001",
            "invoice_date": "2026-01-01",
            "due_date": None,
            "currency": "USD",
            "subtotal": 10.0,
            "tax": 1.0,
            "total_amount": 11.0,
            "line_items": [],
        }
    ]
    r = run_benchmark(s, engines=["existing"], fixtures=fixtures)
    # We should still get a per-engine run, with field mismatches
    # flagged.
    assert "existing" in r["summary"]
    assert len(r["runs"]) == 1
    # And the missing-PDF case is reported as a warning.
    run = r["runs"][0]
    assert run["fields"]["total_amount"]["match"] is False
