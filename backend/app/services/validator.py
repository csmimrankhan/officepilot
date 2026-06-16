"""Validation, confidence, and status decisioning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..config import Settings
from ..models.invoice import InvoiceStatus
from .parser import ParsedInvoice


REQUIRED_FIELDS = ("vendor_name", "invoice_number", "invoice_date", "total_amount")


# Subtotal + tax should equal total within this tolerance (0.5% of total
# or 0.05 absolute, whichever is larger). Tuned for SME invoices with
# a few cents of rounding.
def _total_tolerance(total: float) -> float:
    return max(0.05, abs(total) * 0.005)


@dataclass
class ValidationResult:
    status: InvoiceStatus
    confidence_score: float
    warnings: list[str] = field(default_factory=list)


def validate_parsed(parsed: ParsedInvoice, settings: Settings) -> ValidationResult:
    """Decide status: needs_review vs ready_for_approval based on required
    fields + threshold.

    Approved/rejected are *user* actions only and are never set here.
    """
    warnings = list(parsed.warnings)
    missing = [f for f in REQUIRED_FIELDS if getattr(parsed, f) in (None, "", 0.0) and f != "total_amount"]
    if parsed.total_amount is None:
        missing.append("total_amount")

    confidence = parsed.confidence
    if missing:
        warnings.append(f"Missing required fields: {', '.join(missing)}")

    # Cross-field check: subtotal + tax ≈ total.
    if (
        parsed.subtotal is not None
        and parsed.tax is not None
        and parsed.total_amount is not None
    ):
        expected_total = round(parsed.subtotal + parsed.tax, 2)
        diff = round(expected_total - parsed.total_amount, 2)
        if abs(diff) > _total_tolerance(parsed.total_amount):
            warnings.append(
                f"Subtotal+tax ({expected_total}) does not match total "
                f"({parsed.total_amount}); Δ={diff}"
            )
        elif abs(diff) > 0.005:
            warnings.append(
                f"Subtotal+tax ({expected_total}) differs from total "
                f"({parsed.total_amount}) by {diff}; within tolerance"
            )

    if missing or confidence < settings.confidence_threshold:
        status = InvoiceStatus.NEEDS_REVIEW
    else:
        status = InvoiceStatus.READY_FOR_APPROVAL

    return ValidationResult(
        status=status,
        confidence_score=round(confidence, 3),
        warnings=warnings,
    )
