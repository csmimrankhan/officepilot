"""Heuristic field parser: pulls vendor, dates, totals, currency, line items from raw text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# --- regex patterns -------------------------------------------------------------

_VENDOR_RE = re.compile(
    r"(?:^|\n)\s*([A-Z][A-Za-z0-9&.,'\- ]{2,80})\s*(?:\n|$)",
    flags=re.MULTILINE,
)

_INVOICE_NO_RE = re.compile(
    r"\b(?:invoice\s*(?:number|no\.?|#)|inv\.?\s*(?:no\.?|#)|bill\s*no\.?)\b"
    r"[:#\s]*([A-Za-z0-9][A-Za-z0-9\-_/]{2,30})"
    r"|\binvoice\s*[:#]\s*([A-Za-z0-9][A-Za-z0-9\-_/]{2,30})",
    flags=re.IGNORECASE,
)

_DATE_RE = re.compile(
    r"\b(\d{1,2}[\-/.]\d{1,2}[\-/.]\d{2,4}|\d{4}[\-/.]\d{1,2}[\-/.]\d{1,2}"
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4})\b"
)

_DUE_DATE_RE = re.compile(
    r"(?:due\s*date|due|payment\s*due)[:#\s]*([A-Za-z0-9,\-/.\s]{4,30})",
    flags=re.IGNORECASE,
)

_INVOICE_DATE_RE = re.compile(
    r"(?:invoice\s*date|date\s*of\s*invoice|issued)[:#\s]*([A-Za-z0-9,\-/.\s]{4,30})",
    flags=re.IGNORECASE,
)

_CURRENCY_RE = re.compile(r"\b(USD|EUR|GBP|INR|PKR|AED|SAR|CAD|AUD|JPY|CNY)\b|([\$€£₹¥])")

# Match an integer or decimal number with optional thousands separators.
# The first alternative handles "1,234.56" / "1 234.56" (thousands
# separated); the second handles bare integers and decimals such as
# "4500" or "4500.00".
_NUMBER_RE = r"-?\d{1,3}(?:[,\s]\d{3})+(?:\.\d{1,2})?|-?\d+(?:\.\d{1,2})?"

_TOTAL_RE = re.compile(
    r"\b(?:grand\s*total|amount\s*due|total\s*due|balance\s*due|total)\b[:#\s]*"
    r"([\$€£₹¥]?\s*(" + _NUMBER_RE + r"))",
    flags=re.IGNORECASE,
)

_SUBTOTAL_RE = re.compile(
    r"\bsub[\s\-_]?total\b[:#\s]*([\$€£₹¥]?\s*(" + _NUMBER_RE + r"))",
    flags=re.IGNORECASE,
)

_TAX_RE = re.compile(
    r"\b(?:tax|vat|gst|sales\s*tax)(?:\s*\([^)]*\))?\s*[:#]?\s*"
    r"([\$€£₹¥]?\s*(" + _NUMBER_RE + r"))",
    flags=re.IGNORECASE,
)

_LINE_ITEM_RE = re.compile(
    r"^(?P<desc>[A-Za-z][A-Za-z0-9 &/'\-.,]{2,60}?)\s+"
    r"(?P<qty>\d+(?:\.\d+)?)\s+"
    r"(?P<unit>[\$€£₹¥]?\s*(" + _NUMBER_RE + r"))\s+"
    r"(?P<total>[\$€£₹¥]?\s*(" + _NUMBER_RE + r"))\s*$"
)


# --- data containers ------------------------------------------------------------


@dataclass
class ParsedLineItem:
    description: str
    quantity: float
    unit_price: float
    line_total: float


@dataclass
class ParsedInvoice:
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    line_items: list[ParsedLineItem] = field(default_factory=list)
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)


# --- helpers --------------------------------------------------------------------


def _to_float(s: str) -> Optional[float]:
    if s is None:
        return None
    s = s.strip()
    s = re.sub(r"[\$€£₹¥]", "", s)
    s = s.replace(",", "").replace(" ", "")
    if not re.search(r"\d", s):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _detect_currency(s: str) -> Optional[str]:
    if not s:
        return None
    m = _CURRENCY_RE.search(s)
    if not m:
        return None
    code, symbol = m.group(1), m.group(2)
    if code:
        return code.upper()
    return {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY"}.get(symbol)


def _detect_vendor(text: str) -> Optional[str]:
    """First plausible non-header line in the document.

    Skips common header keywords and lines that are mostly digits / punctuation.
    Real vendor names usually appear before 'Invoice No', 'Date', etc.
    """
    skip_prefixes = (
        "invoice", "tax invoice", "receipt", "bill", "statement",
        "order", "quote", "estimate", "date", "number", "invoice no",
        "invoice number", "inv no", "inv.", "due date", "due",
        "subtotal", "total", "amount", "balance", "payment",
        "bill to", "ship to", "from:", "to:", "customer", "client",
        "po ", "p.o.", "po#",
    )
    for raw in text.splitlines():
        line = raw.strip(" \t-=*•·:")
        if not line or len(line) < 3 or len(line) > 120:
            continue
        low = line.lower()
        if any(low.startswith(p) for p in skip_prefixes):
            continue
        alpha = sum(c.isalpha() for c in line)
        digit = sum(c.isdigit() for c in line)
        if alpha == 0:
            continue
        if digit > alpha:
            continue
        # Avoid lines that are obviously all-caps section headers
        return line[:255]
    return None


# --- main entry -----------------------------------------------------------------


def parse_invoice_text(text: str) -> ParsedInvoice:
    parsed = ParsedInvoice()
    if not text or not text.strip():
        parsed.warnings.append("No text to parse")
        return parsed

    parsed.vendor_name = _detect_vendor(text)

    m = _INVOICE_NO_RE.search(text)
    if m:
        parsed.invoice_number = (m.group(1) or m.group(2) or "").strip().strip(".#:")

    md = _INVOICE_DATE_RE.search(text)
    if md:
        parsed.invoice_date = md.group(1).strip().rstrip(",.;")
    else:
        # Fallback to the first date-looking token
        any_date = _DATE_RE.search(text)
        if any_date:
            parsed.invoice_date = any_date.group(1)

    mdd = _DUE_DATE_RE.search(text)
    if mdd:
        parsed.due_date = mdd.group(1).strip().rstrip(",.;")
    else:
        dates = _DATE_RE.findall(text)
        if parsed.invoice_date and len(dates) >= 2:
            # Pick the second date if it differs from invoice_date
            for d in dates[1:]:
                if d != parsed.invoice_date:
                    parsed.due_date = d
                    break

    parsed.currency = _detect_currency(text)

    mt = _TOTAL_RE.search(text)
    if mt:
        # group(1) is the whole match (e.g. " $ 1061.40"); group(2)
        # is the number itself.
        parsed.total_amount = _to_float(mt.group(2) or mt.group(1))

    ms = _SUBTOTAL_RE.search(text)
    if ms:
        parsed.subtotal = _to_float(ms.group(2) or ms.group(1))

    mx = _TAX_RE.search(text)
    if mx:
        parsed.tax = _to_float(mx.group(2) or mx.group(1))

    # Line items: only attempt if there are tabular-looking rows
    for line in text.splitlines():
        line = line.strip()
        mli = _LINE_ITEM_RE.match(line)
        if mli:
            # group layout: 1=desc, 2=qty, 3=unit (full, with optional
            # symbol), 4=unit (number only), 5=total (full), 6=total
            # (number only).
            qty = _to_float(mli.group(2))
            unit = _to_float(mli.group(4) or mli.group(3))
            tot = _to_float(mli.group(6) or mli.group(5))
            if qty is not None and unit is not None and tot is not None:
                parsed.line_items.append(
                    ParsedLineItem(
                        description=mli.group(1).strip(),
                        quantity=qty,
                        unit_price=unit,
                        line_total=tot,
                    )
                )

    # Compute a simple confidence
    score = 0.0
    if parsed.vendor_name: score += 0.2
    if parsed.invoice_number: score += 0.2
    if parsed.invoice_date: score += 0.15
    if parsed.total_amount is not None: score += 0.25
    if parsed.currency: score += 0.05
    if parsed.subtotal is not None: score += 0.05
    if parsed.tax is not None: score += 0.05
    if parsed.line_items: score += 0.05
    parsed.confidence = min(1.0, round(score, 3))

    # Warnings
    if not parsed.vendor_name: parsed.warnings.append("vendor_name missing")
    if not parsed.invoice_number: parsed.warnings.append("invoice_number missing")
    if not parsed.invoice_date: parsed.warnings.append("invoice_date missing")
    if parsed.total_amount is None: parsed.warnings.append("total_amount missing")
    if parsed.line_items:
        # Consistency: subtotal vs sum of lines
        try:
            line_sum = round(sum(li.line_total for li in parsed.line_items), 2)
            if parsed.subtotal is not None and abs(line_sum - parsed.subtotal) > 0.05:
                parsed.warnings.append(
                    f"subtotal ({parsed.subtotal}) != sum of line items ({line_sum})"
                )
        except Exception:
            pass

    return parsed
