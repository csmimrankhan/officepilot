"""Synthetic invoice text used by toolkit spikes.

This is *not* a real client invoice. It is a contrived sample so that
Docling, PaddleOCR, LangGraph, and Browser-Use spikes can be exercised
without touching real data.
"""

SYNTHETIC_INVOICE = """\
ACME Office Supplies (Spike Fixture)
123 Industrial Way
Springfield, IL 62704

INVOICE

Invoice Number: SPIKE-2026-0001
Invoice Date: 2026-05-12
Due Date: 2026-06-11

Bill To:
Globex Manufacturing (Spike Fixture)
5000 Client Plaza
Shelbyville, TN

Description                  Qty    Unit Price    Line Total
Printer Paper A4            10     4.50          45.00
Toner Cartridge HP 26X      4      89.00         356.00
Stapler Heavy Duty          2      14.75         29.50

Subtotal: 430.50
Tax (7%): 30.14
Total: $460.64

Payment Terms: Net 30

NOTE: This is a synthetic invoice created for the Phase 4 toolkit
spikes. It contains no real vendor, customer, or financial data.
"""
