"""Build the golden invoice fixtures used by Phase 5 benchmarks.

We generate three synthetic PDF invoices plus their expected
JSON. The PDFs are *synthetic* (no real vendor, customer, or
financial data) and the directory is gitignored so the files are
never committed.

The expected JSON lives in a single file, ``golden.json``, with one
entry per invoice keyed by basename. Each entry has:

- ``file``:           basename of the PDF
- ``mime_type``:      the file's MIME type
- ``vendor_name``:    expected vendor string (case-insensitive match)
- ``invoice_number``: expected invoice number (exact match)
- ``invoice_date``:   expected invoice date (ISO 8601)
- ``due_date``:       expected due date (ISO 8601, or null)
- ``currency``:       expected currency code
- ``subtotal``:       expected subtotal
- ``tax``:            expected tax
- ``total_amount``:   expected grand total
- ``line_items``:     list of {description, quantity, unit_price, line_total}
- ``notes``:          free-form notes for the benchmark report

The benchmark runner compares each engine's output to this file and
emits a per-field accuracy report. Field-level comparisons are
case-insensitive and tolerate whitespace differences.
"""

from __future__ import annotations

import json
from pathlib import Path

import fitz  # PyMuPDF

HERE = Path(__file__).resolve().parent
GOLDEN_JSON = HERE / "golden.json"


INVOICES: list[dict] = [
    {
        "name": "alpha_office_supplies",
        "title": "Alpha Office Supplies",
        "vendor_name": "Alpha Office Supplies",
        "address": [
            "123 Industrial Way",
            "Springfield, IL 62704",
        ],
        "invoice_number": "GOLDEN-2026-0001",
        "invoice_date": "2026-05-12",
        "due_date": "2026-06-11",
        "bill_to": [
            "Globex Manufacturing",
            "5000 Client Plaza",
            "Shelbyville, TN",
        ],
        "currency": "USD",
        "line_items": [
            ("Printer Paper A4", 10, 4.50, 45.00),
            ("Toner Cartridge HP 26X", 4, 89.00, 356.00),
            ("Stapler Heavy Duty", 2, 14.75, 29.50),
        ],
        "subtotal": 430.50,
        "tax": 30.14,
        "total_amount": 460.64,
    },
    {
        "name": "beta_logistics",
        "title": "Beta Logistics LLC",
        "vendor_name": "Beta Logistics LLC",
        "address": [
            "42 Harbor Drive",
            "Norfolk, VA 23510",
        ],
        "invoice_number": "BL-2026-0777",
        "invoice_date": "2026-04-22",
        "due_date": "2026-05-22",
        "bill_to": [
            "Initech",
            "12 Corporate Blvd",
            "Austin, TX 78701",
        ],
        "currency": "EUR",
        "line_items": [
            ("Sea Freight - TEU", 3, 250.00, 750.00),
            ("Port Handling Fee", 1, 120.00, 120.00),
        ],
        "subtotal": 870.00,
        "tax": 191.40,
        "total_amount": 1061.40,
    },
    {
        "name": "gamma_consulting",
        "title": "Gamma Consulting",
        "vendor_name": "Gamma Consulting",
        "address": [
            "7 Rue de l'Innovation",
            "Paris, France",
        ],
        "invoice_number": "GC-INV-26-99",
        "invoice_date": "2026-03-01",
        "due_date": "2026-03-31",
        "bill_to": [
            "Hooli, Inc.",
            "1 Amphitheatre Pkwy",
            "Mountain View, CA",
        ],
        "currency": "USD",
        "line_items": [
            ("Strategy workshop", 1, 4500.00, 4500.00),
            ("Follow-up report", 1, 1200.00, 1200.00),
        ],
        "subtotal": 5700.00,
        "tax": 399.00,
        "total_amount": 6099.00,
    },
]


def _render_pdf(spec: dict) -> str:
    """Render a single-page PDF from the spec."""
    text_lines = [spec["title"], ""]
    text_lines.extend(spec["address"])
    text_lines.append("")
    text_lines.append("INVOICE")
    text_lines.append("")
    text_lines.append(f"Invoice Number: {spec['invoice_number']}")
    text_lines.append(f"Invoice Date: {spec['invoice_date']}")
    text_lines.append(f"Due Date: {spec['due_date']}")
    text_lines.append("")
    text_lines.append("Bill To:")
    text_lines.extend(spec["bill_to"])
    text_lines.append("")
    text_lines.append("Description                  Qty    Unit Price    Line Total")
    for desc, qty, unit, total in spec["line_items"]:
        text_lines.append(
            f"{desc:<28} {qty:>3}   {unit:>10.2f}   {total:>10.2f}"
        )
    text_lines.append("")
    text_lines.append(f"Subtotal: {spec['subtotal']:.2f}")
    text_lines.append(f"Tax (22%): {spec['tax']:.2f}")
    # Use a plain numeric total (with optional $) so the regex parser
    # can find it. We can't use € or £ in PyMuPDF's default font; the
    # *expected* currency in golden.json is the source of truth.
    text_lines.append(f"Total: {spec['total_amount']:.2f}")
    text_lines.append("")
    text_lines.append("Payment Terms: Net 30")
    text_lines.append("")
    text_lines.append("NOTE: Synthetic golden invoice. No real data.")

    text = "\n".join(text_lines)
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Insert text line by line so the layout is predictable.
    y = 60
    for line in text.splitlines():
        page.insert_text((50, y), line, fontsize=10)
        y += 14
    out = HERE / f"{spec['name']}.pdf"
    doc.save(str(out))
    doc.close()
    return out.name


def _build_expected(spec: dict, file_name: str) -> dict:
    return {
        "file": file_name,
        "mime_type": "application/pdf",
        "vendor_name": spec["vendor_name"],
        "invoice_number": spec["invoice_number"],
        "invoice_date": spec["invoice_date"],
        "due_date": spec["due_date"],
        "currency": spec["currency"],
        "subtotal": spec["subtotal"],
        "tax": spec["tax"],
        "total_amount": spec["total_amount"],
        "line_items": [
            {
                "description": desc,
                "quantity": qty,
                "unit_price": unit,
                "line_total": total,
            }
            for desc, qty, unit, total in spec["line_items"]
        ],
        "notes": "synthetic golden fixture (no real client data)",
    }


def build() -> dict:
    """Render all PDFs and write golden.json. Idempotent."""
    golden: dict[str, dict] = {}
    for spec in INVOICES:
        file_name = _render_pdf(spec)
        golden[spec["name"]] = _build_expected(spec, file_name)
    GOLDEN_JSON.write_text(
        json.dumps(golden, indent=2, sort_keys=True), encoding="utf-8"
    )
    return golden


if __name__ == "__main__":
    out = build()
    print(f"Wrote {GOLDEN_JSON}")
    for k, v in out.items():
        print(f"  - {k}: {v['file']}")
