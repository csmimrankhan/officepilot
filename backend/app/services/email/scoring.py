"""Scoring of Gmail messages for invoice-likelihood.

Pure-function module. Scoring is intentionally conservative and explainable:
each signal contributes a weight and we return the full breakdown so the
UI can show *why* a message was selected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------- config

SUBJECT_KEYWORDS = (
    "invoice", "tax invoice", "receipt", "bill", "billing",
    "payment due", "payment confirmation", "order invoice",
    "statement", "remittance",
)

BODY_KEYWORDS = (
    "invoice", "total amount", "amount due", "subtotal",
    "tax invoice", "tax:", "vat:", "gst:",
    "bill to", "remit to", "payment terms", "net 30", "net 14",
    "thank you for your business", "thank you for your payment",
)

NEGATIVE_SUBJECT_KEYWORDS = (
    "out of office", "auto-reply", "automatic reply",
    "newsletter", "unsubscribe", "promotion", "promo",
    "order confirmation", "shipping confirmation",
    "tracking number", "delivery update",
)

ATTACHMENT_KEYWORDS = (
    "invoice", "receipt", "bill", "statement", "tax", "remit",
    "inv-", "inv_", "facture", "factuur", "rechnung",
)

ALLOWED_ATTACHMENT_MIMES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}

ATTACHMENT_EXTS = {".pdf", ".png", ".jpg", ".jpeg"}

# Subject keyword weights
W_SUBJECT_KEYWORD = 0.30
W_BODY_KEYWORD = 0.20
W_ATTACHMENT_TYPE = 0.20
W_ATTACHMENT_NAME = 0.15
W_KNOWN_VENDOR = 0.15
NEG_SUBJECT_PENALTY = 0.30

MAX_SCORE = 1.0


# --------------------------------------------------------------------- data


@dataclass
class AttachmentHint:
    filename: str
    mime_type: Optional[str] = None
    size: int = 0


@dataclass
class ScoredMessage:
    score: float = 0.0
    matched: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    eligible_attachments: list[AttachmentHint] = field(default_factory=list)

    def to_breakdown(self) -> dict:
        return {
            "score": round(self.score, 3),
            "matched": self.matched,
            "reasons": self.reasons,
            "eligible_attachments": [
                {"filename": a.filename, "mime_type": a.mime_type, "size": a.size}
                for a in self.eligible_attachments
            ],
        }


# --------------------------------------------------------------------- helpers


def _norm(text: str | None) -> str:
    return (text or "").lower()


def _has_any(text: str, keywords) -> list[str]:
    found = []
    for kw in keywords:
        if kw in text:
            found.append(kw)
    return found


def _vendor_match(sender: str | None, known_vendors) -> list[str]:
    if not sender or not known_vendors:
        return []
    s = sender.lower()
    hits = []
    for v in known_vendors:
        v = (v or "").strip().lower()
        if v and v in s:
            hits.append(v)
    return hits


# --------------------------------------------------------------------- main


def score_message(
    *,
    subject: str | None,
    body: str | None,
    sender: str | None,
    attachments: list[AttachmentHint],
    known_vendors: list[str] | None = None,
) -> ScoredMessage:
    """Return a ScoredMessage with a 0..MAX_SCORE score and explanation.

    Known vendors are typically the list of approved vendor names in the
    system; the caller passes them in.
    """
    known_vendors = known_vendors or []
    sub = _norm(subject)
    body_low = _norm(body)
    combined = f"{sub}\n{body_low}"
    sm = ScoredMessage()

    if not combined.strip() and not attachments:
        sm.reasons.append("empty message")
        return sm

    # 1) Subject keywords
    subject_hits = _has_any(sub, SUBJECT_KEYWORDS)
    if subject_hits:
        sm.score += W_SUBJECT_KEYWORD
        sm.matched.extend(f"subject:{kw}" for kw in subject_hits)
        sm.reasons.append(f"subject matched: {', '.join(subject_hits)}")

    # 2) Body keywords
    body_hits = _has_any(body_low, BODY_KEYWORDS)
    if body_hits:
        sm.score += W_BODY_KEYWORD
        sm.matched.extend(f"body:{kw}" for kw in body_hits[:5])
        sm.reasons.append(f"body matched: {', '.join(body_hits[:5])}")

    # 3) Attachments of the right type
    type_hits: list[str] = []
    name_hits: list[str] = []
    for a in attachments:
        eligible = False
        mt = (a.mime_type or "").lower()
        ext_match = re.search(r"\.([a-z0-9]+)$", (a.filename or "").lower())
        ext = "." + ext_match.group(1) if ext_match else ""
        if mt in ALLOWED_ATTACHMENT_MIMES:
            eligible = True
            type_hits.append(a.filename)
        elif ext in ATTACHMENT_EXTS:
            eligible = True
            type_hits.append(a.filename)
        if not eligible:
            continue
        # 4) Filename hint
        fkey_hits = [kw for kw in ATTACHMENT_KEYWORDS if kw in (a.filename or "").lower()]
        if fkey_hits:
            name_hits.extend(fkey_hits)
        sm.eligible_attachments.append(a)

    if type_hits:
        sm.score += W_ATTACHMENT_TYPE
        sm.reasons.append(f"{len(type_hits)} PDF/image attachment(s)")
    if name_hits:
        sm.score += W_ATTACHMENT_NAME
        sm.matched.extend(f"filename:{kw}" for kw in set(name_hits))
        sm.reasons.append(f"filename hint: {', '.join(sorted(set(name_hits)))}")

    # 5) Known vendor (only meaningful if we actually have a known list)
    vendor_hits = _vendor_match(sender, known_vendors)
    if vendor_hits:
        sm.score += W_KNOWN_VENDOR
        sm.matched.extend(f"vendor:{v}" for v in vendor_hits)
        sm.reasons.append(f"known vendor: {', '.join(vendor_hits)}")

    # Negative subject hints
    neg = _has_any(sub, NEGATIVE_SUBJECT_KEYWORDS)
    if neg:
        sm.score = max(0.0, sm.score - NEG_SUBJECT_PENALTY)
        sm.reasons.append(f"penalized for: {', '.join(neg)}")

    # No eligible attachments at all -> can't be ingested.
    if not sm.eligible_attachments:
        sm.score = 0.0
        sm.reasons.append("no PDF/image attachments")

    sm.score = min(MAX_SCORE, round(sm.score, 3))
    return sm
