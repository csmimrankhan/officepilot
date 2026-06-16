"""Tests for the invoice-candidate scoring module."""

from app.services.email.scoring import AttachmentHint, score_message


def test_empty_message_scores_zero():
    sm = score_message(subject=None, body=None, sender=None, attachments=[])
    assert sm.score == 0.0
    assert any("empty" in r for r in sm.reasons)


def test_subject_keyword_alone_is_not_enough_without_attachment():
    sm = score_message(
        subject="Invoice INV-001 attached",
        body="",
        sender="noreply@example.com",
        attachments=[],
    )
    assert sm.score == 0.0
    assert any("no PDF/image attachments" in r for r in sm.reasons)


def test_subject_plus_pdf_attachment_scores_high():
    sm = score_message(
        subject="Invoice INV-001",
        body="Please find your invoice attached.",
        sender="billing@acme.com",
        attachments=[AttachmentHint(filename="INV-001.pdf", mime_type="application/pdf", size=12345)],
    )
    assert sm.score >= 0.5
    assert sm.eligible_attachments
    assert any("subject" in m for m in sm.matched)


def test_newsletter_is_penalized():
    sm = score_message(
        subject="Monthly newsletter — unsubscribe anytime",
        body="Lots of marketing copy here",
        sender="promo@vendor.com",
        attachments=[AttachmentHint(filename="newsletter.pdf", mime_type="application/pdf", size=10)],
    )
    # The negative subject penalty should keep this below 0.5.
    assert sm.score < 0.5


def test_filename_hint_adds_score():
    sm_no_hint = score_message(
        subject="Documents",
        body="see attached",
        sender="x@y.com",
        attachments=[AttachmentHint(filename="random.pdf", mime_type="application/pdf", size=10)],
    )
    sm_with_hint = score_message(
        subject="Documents",
        body="see attached",
        sender="x@y.com",
        attachments=[AttachmentHint(filename="invoice-2026-05.pdf", mime_type="application/pdf", size=10)],
    )
    assert sm_with_hint.score > sm_no_hint.score


def test_known_vendor_match_adds_score():
    sm = score_message(
        subject="Your statement",
        body="please pay",
        sender="accounts@acme.com",
        attachments=[AttachmentHint(filename="doc.pdf", mime_type="application/pdf", size=10)],
        known_vendors=["acme"],
    )
    assert any(m.startswith("vendor:") for m in sm.matched)


def test_image_attachment_eligible():
    sm = score_message(
        subject="Receipt",
        body="",
        sender="x@y.com",
        attachments=[AttachmentHint(filename="receipt.jpg", mime_type="image/jpeg", size=10)],
    )
    assert sm.eligible_attachments
    assert sm.score >= 0.2


def test_non_invoice_attachment_does_not_promote():
    sm = score_message(
        subject="Hi",
        body="",
        sender="x@y.com",
        attachments=[AttachmentHint(filename="photo.zip", mime_type="application/zip", size=10)],
    )
    assert sm.score == 0.0
    assert sm.eligible_attachments == []


def test_breakdown_includes_score_and_matched():
    sm = score_message(
        subject="Invoice INV-9",
        body="",
        sender="x@y.com",
        attachments=[AttachmentHint(filename="INV-9.pdf", mime_type="application/pdf", size=10)],
    )
    bd = sm.to_breakdown()
    assert "score" in bd and "matched" in bd and "reasons" in bd
    assert isinstance(bd["eligible_attachments"], list)
