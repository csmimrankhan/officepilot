"""Tests for the file organizer (Phase 3 trust layer)."""

from __future__ import annotations

import io
import os
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_file import InvoiceFile
from app.services import organizer


def _seed_invoice(db: Session, tmp_path: Path, *, source: str = "upload", name: str = "scan.pdf") -> tuple[Invoice, str]:
    """Create an invoice and a real file on disk. Returns (invoice, file_path)."""
    file_path = tmp_path / "raw" / name
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"%PDF-1.4 fake")

    file_row = InvoiceFile(
        original_filename=name,
        stored_path=str(file_path),
        current_path=str(file_path),
        file_hash="deadbeef" * 8,
        mime_type="application/pdf",
        size=file_path.stat().st_size,
        source=source,
    )
    db.add(file_row)
    db.flush()

    inv = Invoice(
        vendor_name="ACME Office",
        invoice_number="INV-2026-0042",
        invoice_date="2026-05-12",
        currency="USD",
        total_amount=460.64,
        subtotal=430.50,
        tax=30.14,
        status=InvoiceStatus.READY_FOR_APPROVAL,
        confidence_score=0.92,
        warnings_json=[],
        file_id=file_row.id,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv, str(file_path)


def test_sanitize_replaces_invalid_chars():
    # Trailing dot/space is stripped during sanitization
    assert organizer._sanitize("ACME / Office: Co.") == "ACME _ Office_ Co"
    assert organizer._sanitize("Bad\\name|with*chars") == "Bad_name_with_chars"
    assert organizer._sanitize("   ") == "unknown"
    assert organizer._sanitize("") == "unknown"
    # Long names truncated
    assert len(organizer._sanitize("a" * 500)) == 80
    # Question marks and quotes also replaced
    assert organizer._sanitize('What? "Yes"') == "What_ _Yes_"


def test_money_two_decimals():
    assert organizer._money(100) == "100.00"
    assert organizer._money(99.5) == "99.50"
    assert organizer._money(None) == "0.00"
    assert organizer._money("not a number") == "0.00"


def test_date_parts_handles_common_formats():
    assert organizer._date_parts("2026-05-12") == ("2026", "05", "12")
    assert organizer._date_parts("2026/05/12") == ("2026", "05", "12")
    assert organizer._date_parts("12/05/2026") == ("2026", "05", "12")
    # Unknown format → today
    y, m, d = organizer._date_parts(None)
    today = datetime.utcnow()
    assert (y, m) == (f"{today.year:04d}", f"{today.month:02d}")


def test_build_target_path_substitutes_tokens(tmp_path):
    inv = Invoice(
        vendor_name="ACME Office",
        invoice_number="INV/2026/0042",
        invoice_date="2026-05-12",
        currency="USD",
        total_amount=460.64,
    )
    src = tmp_path / "raw" / "scan.pdf"
    target = organizer.build_target_path(
        tmp_path,
        inv,
        pattern="Invoices/{year}/{month}/{vendor}_{invoice_number}_{total}_{currency}.{ext}",
        source_path=str(src),
    )
    rel = target.relative_to(tmp_path).as_posix()
    assert rel == "Invoices/2026/05/ACME Office_INV_2026_0042_460.64_USD.pdf"
    assert target.name.endswith(".pdf")


def test_organize_moves_file_to_target(tmp_path):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        inv, src = _seed_invoice(db, tmp_path)
        result = organizer.organize(
            tmp_path,
            inv,
            source_path=src,
            pattern="Invoices/{year}/{month}/{vendor}_{invoice_number}.{ext}",
            conflict_strategy="suffix",
        )
        assert result.moved, result
        # Source should be gone
        assert not Path(src).exists()
        # Target should exist
        target = Path(result.target_path)
        assert target.exists()
        assert target.read_bytes() == b"%PDF-1.4 fake"
        # Year-month directory should be present
        assert (tmp_path / "Invoices" / "2026" / "05").is_dir()
    finally:
        db.close()


def test_organize_suffix_strategy_creates_unique_target(tmp_path):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        inv, src = _seed_invoice(db, tmp_path, name="first.pdf")
        # Manually create a file at the target path to force a collision
        (tmp_path / "Invoices" / "2026" / "05").mkdir(parents=True)
        (tmp_path / "Invoices" / "2026" / "05" / "ACME Office_INV-2026-0042.pdf").write_bytes(b"x")

        result = organizer.organize(
            tmp_path,
            inv,
            source_path=src,
            pattern="Invoices/{year}/{month}/{vendor}_{invoice_number}.{ext}",
            conflict_strategy="suffix",
        )
        assert result.moved
        assert result.target_path.endswith("ACME Office_INV-2026-0042_1.pdf")
    finally:
        db.close()


def test_organize_skip_strategy_returns_unchanged(tmp_path):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        inv, src = _seed_invoice(db, tmp_path)
        (tmp_path / "Invoices" / "2026" / "05").mkdir(parents=True)
        # Pre-create the exact target
        (tmp_path / "Invoices" / "2026" / "05" / "ACME Office_INV-2026-0042.pdf").write_bytes(b"old")

        result = organizer.organize(
            tmp_path,
            inv,
            source_path=src,
            pattern="Invoices/{year}/{month}/{vendor}_{invoice_number}.{ext}",
            conflict_strategy="skip",
        )
        assert not result.moved
        assert "skip" in (result.skipped_reason or "")
        # Source should still exist
        assert Path(src).exists()
    finally:
        db.close()


def test_organize_overwrite_strategy_replaces_existing(tmp_path):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        inv, src = _seed_invoice(db, tmp_path)
        (tmp_path / "Invoices" / "2026" / "05").mkdir(parents=True)
        target = (tmp_path / "Invoices" / "2026" / "05" / "ACME Office_INV-2026-0042.pdf")
        target.write_bytes(b"old")

        result = organizer.organize(
            tmp_path,
            inv,
            source_path=src,
            pattern="Invoices/{year}/{month}/{vendor}_{invoice_number}.{ext}",
            conflict_strategy="overwrite",
        )
        assert result.moved
        assert target.read_bytes() == b"%PDF-1.4 fake"
    finally:
        db.close()


def test_organize_missing_source_returns_skip(tmp_path):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        inv, _src = _seed_invoice(db, tmp_path)
        result = organizer.organize(
            tmp_path,
            inv,
            source_path=str(tmp_path / "nope.pdf"),
            pattern="Invoices/{vendor}.{ext}",
            conflict_strategy="suffix",
        )
        assert not result.moved
        assert "missing" in (result.skipped_reason or "")
    finally:
        db.close()


def test_organize_missing_fields_use_unknown_token(tmp_path):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        inv, src = _seed_invoice(db, tmp_path)
        inv.vendor_name = None
        inv.invoice_number = None
        db.commit()

        result = organizer.organize(
            tmp_path,
            inv,
            source_path=src,
            pattern="Invoices/{vendor}_{invoice_number}.{ext}",
            conflict_strategy="suffix",
        )
        assert result.moved
        # Both vendor and invoice_number are unknown
        assert Path(result.target_path).name == "unknown_unknown.pdf"
    finally:
        db.close()
