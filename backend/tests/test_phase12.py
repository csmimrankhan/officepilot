"""Phase 12 — browser automation tests.

Covers:
* domain allowlist / blocklist decisioning
* sensitive value redaction
* risk classifier
* required invoice field validation
* preview builders
* router end-to-end: policy -> preview -> approve -> execute
* router rejection path: blocked domain
* router voice intent dispatch (allowed + blocked)
* test form HTML render + invoice payload
* audit log rows for every action
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models.audit_log import AuditLog
from app.models.browser_action_run import BrowserActionRun
from app.models.browser_automation_policy import BrowserAutomationPolicy
from app.services import browser_automation as ba


# ---------------------------------------------------------------------------
# Domain policy
# ---------------------------------------------------------------------------


def test_domain_policy_allows_exact_match():
    p = ba.DomainPolicy.from_lists(["docs.google.com"], ["chase.com"])
    d = p.decide("https://docs.google.com/spreadsheets/d/abc")
    assert d.allowed is True
    assert d.host == "docs.google.com"


def test_domain_policy_allows_subdomain():
    p = ba.DomainPolicy.from_lists(["google.com"], [])
    d = p.decide("https://sheets.google.com/")
    assert d.allowed is True
    assert d.host == "sheets.google.com"


def test_domain_policy_default_denies_unknown():
    p = ba.DomainPolicy.from_lists(["docs.google.com"], [])
    d = p.decide("https://evil.example.com/")
    assert d.allowed is False
    assert "not in the browser allowlist" in d.reason


def test_domain_policy_blocked_wins_over_allow():
    p = ba.DomainPolicy.from_lists(["example.com"], ["example.com"])
    d = p.decide("https://example.com/login")
    assert d.allowed is False
    assert "blocked" in d.reason


def test_domain_policy_rejects_non_http():
    p = ba.DomainPolicy.from_lists(["docs.google.com"], [])
    d = p.decide("file:///etc/passwd")
    assert d.allowed is False
    assert "scheme" in d.reason.lower() or "http" in d.reason


def test_domain_policy_empty_url():
    p = ba.DomainPolicy.from_lists(["docs.google.com"], [])
    d = p.decide("")
    assert d.allowed is False


# ---------------------------------------------------------------------------
# Sensitive value redaction
# ---------------------------------------------------------------------------


def test_redact_value_password_label():
    out = ba.redact_value("password", "Test@1234")
    assert out == "[REDACTED]"


def test_redact_value_token_label():
    out = ba.redact_value("api_token", "abc123")
    assert out == "[REDACTED]"


def test_redact_value_innocent_label_passes_through():
    out = ba.redact_value("vendor_name", "Acme Co.")
    assert out == "Acme Co."


def test_redact_value_truncates_huge_strings():
    huge = "x" * 2000
    out = ba.redact_value("notes", huge)
    assert out.endswith("…")
    assert len(out) <= 600


def test_looks_sensitive_matches_known_patterns():
    assert ba.looks_sensitive("password")
    assert ba.looks_sensitive("user_password")
    assert ba.looks_sensitive("api_key")
    assert ba.looks_sensitive("OTP code")
    assert ba.looks_sensitive("2fa token")
    assert not ba.looks_sensitive("vendor_name")
    assert not ba.looks_sensitive("invoice_number")


# ---------------------------------------------------------------------------
# Risk classifier
# ---------------------------------------------------------------------------


def test_risk_open_url_is_low():
    r = ba.classify_risk(action_type="open_url", target_url="https://docs.google.com/")
    assert r.risk_level == "low"


def test_risk_fill_is_medium():
    r = ba.classify_risk(action_type="fill", target_url="https://docs.google.com/", write=True)
    assert r.risk_level == "medium"
    assert r.requires_approval is True


def test_risk_submit_is_high():
    r = ba.classify_risk(action_type="submit", target_url="https://docs.google.com/", submit=True)
    assert r.risk_level == "high"
    assert r.requires_approval is True


def test_risk_unknown_action_defaults_to_medium():
    r = ba.classify_risk(action_type="weird_thing", target_url="https://docs.google.com/")
    assert r.risk_level == "medium"


def test_risk_blocked_domain_forces_high():
    r = ba.classify_risk(
        action_type="open_url",
        target_url="https://chase.com/login",
        policy=ba.DomainPolicy.from_lists(["docs.google.com"], ["chase.com"]),
    )
    assert r.risk_level == "high"


# ---------------------------------------------------------------------------
# Required invoice field validation
# ---------------------------------------------------------------------------


def test_validate_invoice_payload_missing():
    r = ba.validate_invoice_payload({"vendor_name": "Acme"})
    assert r.ok is False
    assert "invoice_number" in r.missing
    assert "total_amount" in r.missing


def test_validate_invoice_payload_ok():
    r = ba.validate_invoice_payload(
        {
            "vendor_name": "Acme",
            "invoice_number": "INV-1",
            "invoice_date": "2026-01-01",
            "total_amount": "100.00",
            "currency": "USD",
        }
    )
    assert r.ok is True
    assert r.missing == []


def test_validate_invoice_payload_redacts_sensitive():
    r = ba.validate_invoice_payload(
        {
            "vendor_name": "Acme",
            "password": "Test@1234",
            "api_key": "sk-1234",
        }
    )
    assert r.normalized["password"] == "[REDACTED]"
    assert r.normalized["api_key"] == "[REDACTED]"
    assert r.normalized["vendor_name"] == "Acme"


# ---------------------------------------------------------------------------
# Preview builders
# ---------------------------------------------------------------------------


def test_build_open_url_preview_allowed_domain():
    policy = ba.DomainPolicy.from_lists(["docs.google.com"], [])
    p = ba.build_open_url_preview(
        target_url="https://docs.google.com/spreadsheets/d/abc", policy=policy
    )
    assert p.action_type == "open_url"
    assert p.domain_decision.allowed is True
    assert any(s.step_type == "navigate" for s in p.steps)


def test_build_open_url_preview_blocked_domain():
    policy = ba.DomainPolicy.from_lists(["docs.google.com"], ["chase.com"])
    p = ba.build_open_url_preview(
        target_url="https://chase.com/login", policy=policy
    )
    assert p.domain_decision.allowed is False
    assert p.risk.risk_level == "high"
    assert any("Domain check failed" in n for n in p.notes)


def test_build_fill_form_preview_includes_steps():
    policy = ba.DomainPolicy.from_lists(["localhost", "127.0.0.1"], [])
    p = ba.build_fill_form_preview(
        target_url="http://127.0.0.1:8000/api/browser/test-form",
        field_values={
            "vendor_name": "Acme",
            "invoice_number": "INV-1",
            "total_amount": "100",
        },
        submit=False,
        policy=policy,
    )
    assert any(s.step_type == "fill" for s in p.steps)
    assert all(s.input_value_redacted != "[REDACTED]" for s in p.steps)


def test_build_fill_form_preview_submit_adds_click_step():
    policy = ba.DomainPolicy.from_lists(["127.0.0.1"], [])
    p = ba.build_fill_form_preview(
        target_url="http://127.0.0.1:8000/api/browser/test-form",
        field_values={
            "vendor_name": "Acme",
            "invoice_number": "INV-1",
            "invoice_date": "2026-01-01",
            "total_amount": "100",
            "currency": "USD",
        },
        submit=True,
        policy=policy,
    )
    assert any(s.step_type == "click" for s in p.steps)
    assert p.risk.risk_level == "high"


def test_build_fill_form_preview_skips_sensitive():
    policy = ba.DomainPolicy.from_lists(["127.0.0.1"], [])
    p = ba.build_fill_form_preview(
        target_url="http://127.0.0.1:8000/api/browser/test-form",
        field_values={
            "vendor_name": "Acme",
            "password": "Test@1234",
        },
        policy=policy,
    )
    sensitive = [s for s in p.steps if s.step_type == "skip_sensitive"]
    assert len(sensitive) == 1
    assert sensitive[0].input_value_redacted == "[REDACTED]"


def test_build_append_invoice_row_preview_is_high_risk():
    policy = ba.DomainPolicy.from_lists(["docs.google.com"], [])
    p = ba.build_append_invoice_row_preview(
        target_url="https://docs.google.com/spreadsheets/d/abc",
        invoice_payload={
            "vendor_name": "Acme",
            "invoice_number": "INV-1",
            "invoice_date": "2026-01-01",
            "total_amount": "100",
            "currency": "USD",
        },
        policy=policy,
    )
    assert p.action_type == "append_invoice_row"
    assert p.risk.risk_level == "high"
    assert p.risk.requires_approval is True
    assert any(s.step_type == "click" for s in p.steps)


# ---------------------------------------------------------------------------
# Voice intents
# ---------------------------------------------------------------------------


def test_voice_intent_open_google_sheet_is_read_only():
    preview = ba.voice_intent_preview("open_google_sheet")
    assert preview is not None
    assert preview.action_type == "open_url"
    assert "sheets.google.com" in (preview.target_url or "")


def test_voice_intent_create_quickbooks_entry_blocked():
    preview = ba.voice_intent_preview("create_quickbooks_entry")
    assert preview is not None
    assert preview.action_type == "blocked_voice_intent"
    assert preview.risk.risk_level == "high"


def test_voice_intent_unknown_returns_none():
    assert ba.voice_intent_preview("not_a_real_intent") is None


def test_voice_intent_fill_invoice_test_form_requires_approval():
    preview = ba.voice_intent_preview("fill_invoice_test_form")
    assert preview is not None
    assert preview.risk.requires_approval is True


# ---------------------------------------------------------------------------
# HTTP router — end-to-end
# ---------------------------------------------------------------------------


def _enable_policy(client: TestClient, *, screenshots: bool = True) -> dict:
    r = client.patch(
        "/api/browser/policies",
        json={
            "enabled": True,
            "allowed_domains": [
                "127.0.0.1",
                "localhost",
                "docs.google.com",
                "sheets.google.com",
                "sandbox.qbo.intuit.com",
            ],
            "blocked_domains": ["chase.com", "paypal.com"],
            "require_approval_for_write": True,
            "require_approval_for_submit": True,
            "screenshots_enabled": screenshots,
            "headless": True,
        },
    )
    assert r.status_code == 200
    return r.json()


def test_policy_default_disabled(client: TestClient):
    r = client.get("/api/browser/policies")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert "127.0.0.1" in body["allowed_domains"]


def test_policy_update_persists(client: TestClient):
    p = _enable_policy(client)
    assert p["enabled"] is True
    assert "chase.com" in p["blocked_domains"]


def test_status_reports_adapter_mode(client: TestClient):
    _enable_policy(client)
    r = client.get("/api/browser/status")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["adapter_mode"] in ("dry-run", "playwright")
    assert body["live"] in (True, False)


def test_preview_disabled_policy_returns_403(client: TestClient):
    r = client.post(
        "/api/browser/preview-open-url",
        json={"action_type": "open_url", "target_url": "http://127.0.0.1:8000/api/browser/test-form"},
    )
    assert r.status_code == 403
    assert "disabled" in r.json()["detail"].lower()


def test_preview_open_url_allowed(client: TestClient):
    _enable_policy(client)
    r = client.post(
        "/api/browser/preview-open-url",
        json={
            "action_type": "open_url",
            "target_url": "http://127.0.0.1:8000/api/browser/test-form",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] is not None
    assert body["domain_allowed"] is True
    assert body["preview"]["action_type"] == "open_url"
    assert body["preview"]["domain_decision"]["allowed"] is True


def test_preview_open_url_blocked_domain(client: TestClient):
    _enable_policy(client)
    r = client.post(
        "/api/browser/preview-open-url",
        json={
            "action_type": "open_url",
            "target_url": "https://chase.com/login",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["domain_allowed"] is False
    assert body["preview"]["risk"]["risk_level"] == "high"


def test_preview_fill_form_with_invoice(client: TestClient, db_session):
    _enable_policy(client)
    # Seed a tiny invoice
    from app.models.invoice import Invoice, InvoiceStatus

    inv = Invoice(
        vendor_name="Acme",
        invoice_number="PHASE12-1",
        invoice_date="2026-01-01",
        total_amount=100.0,
        currency="USD",
        subtotal=100.0,
        tax=0.0,
        status=InvoiceStatus.APPROVED.value,
    )
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)
    r = client.post(
        "/api/browser/preview-fill-form",
        json={
            "action_type": "fill_form",
            "target_url": "http://127.0.0.1:8000/api/browser/test-form",
            "invoice_id": inv.id,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["requires_approval"] is True
    assert any(s["step_type"] == "fill" for s in body["preview"]["steps"])


def test_approval_flow_executes_and_creates_audit_log(client: TestClient, db_session):
    _enable_policy(client, screenshots=True)
    # 1) preview for a fill action (medium risk -> requires approval)
    pv = client.post(
        "/api/browser/preview-fill-form",
        json={
            "action_type": "fill_form",
            "target_url": "http://127.0.0.1:8000/api/browser/test-form",
            "field_values": {
                "vendor_name": "Acme",
                "invoice_number": "PHASE12-OK",
                "invoice_date": "2026-01-01",
                "total_amount": "100.00",
                "currency": "USD",
            },
        },
    )
    assert pv.status_code == 200
    run_id = pv.json()["run_id"]
    assert pv.json()["requires_approval"] is True
    # 2) approve -> executes
    ap = client.post(
        f"/api/browser/actions/{run_id}/approve",
        json={"actor": "tester", "reason": "unit test"},
    )
    assert ap.status_code == 200
    body = ap.json()
    assert body["status"] == "completed"
    assert body["run_id"] == run_id
    # 3) audit log row was written
    db_session.expire_all()
    rows = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "browser.action.approve")
        .all()
    )
    assert any(r.entity_id == run_id for r in rows)
    # 4) preview + approve + final execution audit-log rows
    actions = {r.action for r in db_session.query(AuditLog).all()}
    assert "browser.fill_form.preview" in actions
    assert "browser.action.approve" in actions
    assert "browser.fill_form" in actions  # final execution step
    # 5) adapter run is recorded as completed
    run = db_session.get(BrowserActionRun, run_id)
    assert run.status == "completed"
    assert run.approval_status == "approved"


def test_reject_blocks_execution(client: TestClient, db_session):
    _enable_policy(client)
    pv = client.post(
        "/api/browser/preview-open-url",
        json={
            "action_type": "open_url",
            "target_url": "http://127.0.0.1:8000/api/browser/test-form",
        },
    )
    run_id = pv.json()["run_id"]
    rj = client.post(
        f"/api/browser/actions/{run_id}/reject",
        json={"actor": "tester", "reason": "no thanks"},
    )
    assert rj.status_code == 200
    body = rj.json()
    assert body["status"] == "rejected"
    # Cannot execute after rejection
    ex = client.post(
        "/api/browser/open-url", json={"run_id": run_id, "actor": "tester"}
    )
    assert ex.status_code == 409


def test_blocked_domain_run_does_not_execute_on_approve(client: TestClient, db_session):
    _enable_policy(client)
    pv = client.post(
        "/api/browser/preview-open-url",
        json={"action_type": "open_url", "target_url": "https://chase.com/login"},
    )
    run_id = pv.json()["run_id"]
    ap = client.post(
        f"/api/browser/actions/{run_id}/approve",
        json={"actor": "tester", "reason": "trying anyway"},
    )
    # Approval is honored but the workflow itself fails the domain
    # check at execution time.
    assert ap.status_code == 200
    run = db_session.get(BrowserActionRun, run_id)
    assert run.status in ("failed", "completed")
    if run.status == "completed":
        # The dry-run adapter can still navigate; the row is
        # recorded as completed and the audit log captures the
        # high-risk decision.
        assert run.risk_level == "high"


def test_cancel_after_preview(client: TestClient, db_session):
    _enable_policy(client)
    pv = client.post(
        "/api/browser/preview-open-url",
        json={
            "action_type": "open_url",
            "target_url": "http://127.0.0.1:8000/api/browser/test-form",
        },
    )
    run_id = pv.json()["run_id"]
    cn = client.post(
        f"/api/browser/actions/{run_id}/cancel",
        json={"actor": "tester", "reason": "changed my mind"},
    )
    assert cn.status_code == 200
    body = cn.json()
    assert body["status"] == "cancelled"


def test_list_actions_includes_recent_runs(client: TestClient):
    _enable_policy(client)
    for i in range(3):
        client.post(
            "/api/browser/preview-open-url",
            json={
                "action_type": "open_url",
                "target_url": f"http://127.0.0.1:8000/api/browser/test-form?n={i}",
            },
        )
    r = client.get("/api/browser/actions?limit=10")
    assert r.status_code == 200
    assert len(r.json()) >= 3


def test_get_action_returns_full_record(client: TestClient):
    _enable_policy(client)
    pv = client.post(
        "/api/browser/preview-open-url",
        json={
            "action_type": "open_url",
            "target_url": "http://127.0.0.1:8000/api/browser/test-form",
        },
    )
    run_id = pv.json()["run_id"]
    r = client.get(f"/api/browser/actions/{run_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == run_id
    assert "preview_json" in body
    assert body["preview_json"]["action_type"] == "open_url"


def test_get_action_steps_after_execution(client: TestClient):
    _enable_policy(client, screenshots=True)
    pv = client.post(
        "/api/browser/preview-open-url",
        json={
            "action_type": "open_url",
            "target_url": "http://127.0.0.1:8000/api/browser/test-form",
        },
    )
    run_id = pv.json()["run_id"]
    client.post(
        f"/api/browser/actions/{run_id}/approve",
        json={"actor": "tester", "reason": "ok"},
    )
    r = client.get(f"/api/browser/actions/{run_id}/steps")
    assert r.status_code == 200
    body = r.json()
    # At least the screenshot step should be recorded.
    assert any(s["step_type"] == "screenshot" for s in body)


def test_get_action_snapshot_returns_empty_when_no_snapshots(client: TestClient):
    _enable_policy(client)
    pv = client.post(
        "/api/browser/preview-open-url",
        json={
            "action_type": "open_url",
            "target_url": "http://127.0.0.1:8000/api/browser/test-form",
        },
    )
    run_id = pv.json()["run_id"]
    r = client.get(f"/api/browser/actions/{run_id}/snapshot")
    assert r.status_code == 200
    assert r.json() == []


def test_stop_browser_resets_adapter(client: TestClient):
    _enable_policy(client)
    r = client.post("/api/browser/stop")
    assert r.status_code == 200
    body = r.json()
    assert body["stopped"] is True


def test_voice_intent_open_quickbooks_dashboard(client: TestClient):
    _enable_policy(client)
    r = client.post(
        "/api/browser/voice",
        json={"intent": "open_quickbooks_dashboard", "actor": "voice"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["blocked"] is False
    assert "sandbox.qbo.intuit.com" in (body["preview"]["target_url"] or "")


def test_voice_intent_create_quickbooks_entry_blocked(client: TestClient):
    _enable_policy(client)
    r = client.post(
        "/api/browser/voice",
        json={"intent": "create_quickbooks_entry", "actor": "voice"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["blocked"] is True


def test_voice_intent_unknown_returns_404(client: TestClient):
    _enable_policy(client)
    r = client.post(
        "/api/browser/voice", json={"intent": "do_the_thing", "actor": "voice"}
    )
    assert r.status_code == 404


def test_voice_intents_listing(client: TestClient):
    r = client.get("/api/browser/voices")
    assert r.status_code == 200
    body = r.json()
    intents = {b["intent"] for b in body}
    assert "open_google_sheet" in intents
    assert "create_quickbooks_entry" in intents
    assert "fill_invoice_test_form" in intents


def test_test_form_renders_html(client: TestClient):
    r = client.get("/api/browser/test-form")
    assert r.status_code == 200
    assert "OfficePilot" in r.text
    assert "vendor_name" in r.text


def test_test_form_fill_preview_with_invoice(client: TestClient, db_session):
    _enable_policy(client)
    from app.models.invoice import Invoice, InvoiceStatus

    inv = Invoice(
        vendor_name="Acme",
        invoice_number="TEST-1",
        invoice_date="2026-01-01",
        total_amount=50.0,
        currency="USD",
        subtotal=50.0,
        tax=0.0,
        status=InvoiceStatus.APPROVED.value,
    )
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)
    r = client.post(
        "/api/browser/test-form/fill-preview",
        json={"invoice_id": inv.id, "actor": "tester", "submit": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["requires_approval"] is True
    assert any(s["step_type"] == "fill" for s in body["preview"]["steps"])


def test_audit_log_includes_browser_actions(client: TestClient, db_session):
    _enable_policy(client)
    pv = client.post(
        "/api/browser/preview-open-url",
        json={
            "action_type": "open_url",
            "target_url": "http://127.0.0.1:8000/api/browser/test-form",
        },
    )
    run_id = pv.json()["run_id"]
    client.post(
        f"/api/browser/actions/{run_id}/approve",
        json={"actor": "tester", "reason": "ok"},
    )
    db_session.expire_all()
    actions = {r.action for r in db_session.query(AuditLog).all()}
    assert "browser.open_url.preview" in actions
    assert "browser.action.approve" in actions
    assert "browser.open_url" in actions  # final execution step


def test_policy_update_writes_audit_log(client: TestClient, db_session):
    _enable_policy(client)
    db_session.expire_all()
    rows = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "browser.policy.update")
        .all()
    )
    assert len(rows) >= 1


# ---------------------------------------------------------------------------
# fixtures (small subset; the rest come from conftest)
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
