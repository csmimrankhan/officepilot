"""Phase 12 — browser automation service.

The service is split into four small pieces:

* :class:`DomainPolicy` — allowlist / blocklist decisioning and
  URL parsing helpers.
* :func:`classify_risk` — maps an action descriptor (action
  type, target URL, policy flags) to ``low`` / ``medium`` / ``high``
  and the matching ``requires_approval`` boolean.
* :func:`redact_value` / :func:`looks_sensitive` — never store
  raw passwords, 2FA codes, etc. in the action run or step log.
* :class:`BrowserAdapter` — the (currently dry-run) browser
  controller. The real Playwright import is attempted lazily and
  we fall back to a "preview only" mode if it is not installed so
  the sidecar still boots and the UI still works.

The router in :mod:`app.routers.browser` is the only place that
talks to the database; this module is deliberately side-effect
free apart from writing screenshot PNGs into
``settings.browser_snapshots_dir``.
"""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

from ..config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain policy
# ---------------------------------------------------------------------------


SENSITIVE_FIELD_PATTERNS = (
    re.compile(r"passw(or)?d", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"api[_-]?key", re.IGNORECASE),
    re.compile(r"2fa|otp|mfa|verification", re.IGNORECASE),
    re.compile(r"cvv|cvc|ssn|sin|tax[_-]?id", re.IGNORECASE),
    re.compile(r"pin", re.IGNORECASE),
)

# Fields we are willing to write from an Invoice row without
# marking the action as "high risk". Anything not in this list
# that comes from the UI must go through the redactor + risk
# classifier.
SAFE_INVOICE_FIELDS = {
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "subtotal",
    "tax",
    "total_amount",
    "currency",
    "notes",
    "po_number",
    "due_date",
}

# Domain allowlist / blocklist decision: we use a small struct
# rather than passing the raw settings everywhere so the service
# is easy to unit-test in isolation.
@dataclass
class DomainPolicy:
    allowed: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)

    @classmethod
    def from_settings(cls) -> "DomainPolicy":
        s = get_settings()
        return cls(
            allowed=list(s.browser_allowed_domain_list),
            blocked=list(s.browser_blocked_domain_list),
        )

    @classmethod
    def from_lists(
        cls, allowed: Iterable[str], blocked: Iterable[str]
    ) -> "DomainPolicy":
        return cls(
            allowed=[d.strip().lower() for d in allowed if d and d.strip()],
            blocked=[d.strip().lower() for d in blocked if d and d.strip()],
        )

    def decide(self, url: str) -> "DomainDecision":
        """Default-deny: returns a decision object that explains
        why we allowed, blocked, or rejected a URL."""
        if not url or not isinstance(url, str):
            return DomainDecision(False, "", "empty url")
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return DomainDecision(
                False,
                parsed.hostname or "",
                f"unsupported scheme {parsed.scheme!r}; only http(s) is allowed",
            )
        host = (parsed.hostname or "").lower()
        if not host:
            return DomainDecision(False, "", "no host in url")
        # Blocklist wins over allowlist — a banking site should
        # never be automated even if the user added it to the
        # allowlist.
        for b in self.blocked:
            if host == b or host.endswith("." + b):
                return DomainDecision(
                    False, host, f"host matches blocked domain {b!r}"
                )
        for a in self.allowed:
            if host == a or host.endswith("." + a):
                return DomainDecision(True, host, f"host matches allowed domain {a!r}")
        return DomainDecision(
            False,
            host,
            f"host {host!r} is not in the browser allowlist "
            "(default-deny: add the domain in Settings to enable)",
        )


@dataclass
class DomainDecision:
    allowed: bool
    host: str
    reason: str

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "host": self.host, "reason": self.reason}


# ---------------------------------------------------------------------------
# Sensitive value redaction
# ---------------------------------------------------------------------------


def looks_sensitive(label: str) -> bool:
    """Return True if a field label looks like it wants a password,
    2FA code, or other token we must never log / write through
    the browser adapter."""
    if not label:
        return False
    text = str(label)
    return any(p.search(text) for p in SENSITIVE_FIELD_PATTERNS)


def redact_value(label: str, value: Any) -> str:
    """Return a redacted placeholder for ``value`` if the field
    label matches a sensitive pattern. Otherwise return ``value``
    untouched (cast to ``str``)."""
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    if looks_sensitive(label):
        return "[REDACTED]"
    # If the *content* looks like a credit card / ssn, redact
    # even if the label is innocent.
    digits_only = re.sub(r"\D", "", text)
    if len(digits_only) in (13, 14, 15, 16, 9) and looks_sensitive(label):
        return "[REDACTED]"
    # Truncate huge strings to keep the DB small.
    if len(text) > 512:
        return text[:512] + "…"
    return text


# ---------------------------------------------------------------------------
# Risk classifier
# ---------------------------------------------------------------------------


# Verb → risk level. "open" is low because it just navigates.
# "fill" is medium because it changes the form state. "click" of
# a "submit" / "save" / "finalize" verb is always high.
SUBMIT_VERBS = {
    "submit",
    "save",
    "send",
    "publish",
    "finalize",
    "sync",
    "post",
    "confirm",
    "update",
    "delete",
    "remove",
    "pay",
    "approve",
}

WRITE_VERBS = {"append", "fill", "type", "input", "set", "replace"}


def classify_risk(
    *,
    action_type: str,
    target_url: Optional[str] = None,
    submit: bool = False,
    write: bool = False,
    policy: Optional[DomainPolicy] = None,
) -> "RiskAssessment":
    """Map an action descriptor to a risk level and approval
    requirement. The policy argument lets callers force
    ``require_approval_for_submit`` / ``..._write`` from the
    active policy row."""
    s = get_settings()
    p = policy or DomainPolicy.from_settings()
    action = (action_type or "").lower().strip()
    risk = "low"
    reasons: list[str] = []
    requires_approval = False
    if action == "open_url":
        risk = "low"
        reasons.append("navigation only; no DOM mutation")
    elif action in WRITE_VERBS:
        risk = "medium"
        reasons.append("fills a form field; modifies the page state")
        if s.browser_require_approval_for_write or (p and (p.allowed or p.blocked)):
            requires_approval = True
    elif action in SUBMIT_VERBS or submit:
        risk = "high"
        reasons.append("submits / finalizes the form; data leaves the page")
        requires_approval = True
    elif action == "click_approved_button":
        risk = "medium"
        reasons.append("clicks an approved button on the page")
        if s.browser_require_approval_for_write:
            requires_approval = True
    elif action == "append_invoice_row":
        risk = "high"
        reasons.append("writes invoice data to a remote spreadsheet")
        requires_approval = True
    elif action == "validate_result":
        risk = "low"
        reasons.append("read-only validation; no DOM mutation")
    else:
        # Unknown action type — treat as medium to be safe.
        risk = "medium"
        reasons.append(f"unknown action_type {action_type!r}; defaulting to medium")

    if target_url:
        decision = p.decide(target_url)
        if not decision.allowed:
            # Blocked or unknown domain should *not* be
            # auto-approvable; we surface this as a high-risk
            # failed precheck in the preview.
            reasons.append("target domain is not in the allowlist")
            risk = "high"
    if write and s.browser_require_approval_for_write:
        requires_approval = True
    if submit and s.browser_require_approval_for_submit:
        requires_approval = True
    return RiskAssessment(
        risk_level=risk,
        requires_approval=requires_approval,
        reasons=reasons,
    )


@dataclass
class RiskAssessment:
    risk_level: str
    requires_approval: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "reasons": list(self.reasons),
        }


# ---------------------------------------------------------------------------
# Required invoice field validation
# ---------------------------------------------------------------------------


REQUIRED_INVOICE_FIELDS = (
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "total_amount",
    "currency",
)


def validate_invoice_payload(payload: dict) -> "ValidationResult":
    """Return a list of missing required fields and a normalised
    value dict with redacted sensitive entries."""
    if not isinstance(payload, dict):
        return ValidationResult(
            ok=False,
            missing=list(REQUIRED_INVOICE_FIELDS),
            normalized={},
        )
    missing = [f for f in REQUIRED_INVOICE_FIELDS if not payload.get(f)]
    normalized: dict[str, str] = {}
    for k, v in payload.items():
        if not isinstance(k, str):
            continue
        normalized[k] = redact_value(k, v)
    return ValidationResult(
        ok=not missing,
        missing=missing,
        normalized=normalized,
    )


@dataclass
class ValidationResult:
    ok: bool
    missing: list[str]
    normalized: dict

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "missing": list(self.missing),
            "normalized": dict(self.normalized),
        }


# ---------------------------------------------------------------------------
# Preview builder
# ---------------------------------------------------------------------------


@dataclass
class StepPreview:
    step_order: int
    step_type: str
    target_description: str
    selector: str
    input_value_redacted: str
    requires_approval: bool

    def to_dict(self) -> dict:
        return {
            "step_order": self.step_order,
            "step_type": self.step_type,
            "target_description": self.target_description,
            "selector": self.selector,
            "input_value_redacted": self.input_value_redacted,
            "requires_approval": self.requires_approval,
        }


@dataclass
class ActionPreview:
    action_type: str
    target_url: Optional[str]
    target_domain: str
    risk: RiskAssessment
    steps: list[StepPreview] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    domain_decision: Optional[DomainDecision] = None

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "target_url": self.target_url,
            "target_domain": self.target_domain,
            "risk": self.risk.to_dict(),
            "steps": [s.to_dict() for s in self.steps],
            "notes": list(self.notes),
            "domain_decision": (
                self.domain_decision.to_dict() if self.domain_decision else None
            ),
        }


def build_fill_form_preview(
    *,
    target_url: str,
    field_values: dict,
    submit: bool = False,
    policy: Optional[DomainPolicy] = None,
) -> ActionPreview:
    """Build the preview for a "fill form" action.

    The caller is expected to have validated the invoice payload
    first via :func:`validate_invoice_payload`. We *also* call it
    here so the router doesn't have to remember.
    """
    p = policy or DomainPolicy.from_settings()
    decision = p.decide(target_url) if target_url else None
    validation = validate_invoice_payload(field_values)
    risk = classify_risk(
        action_type="fill_form",
        target_url=target_url,
        submit=submit,
        write=True,
        policy=p,
    )
    steps: list[StepPreview] = []
    order = 0
    for key, val in (field_values or {}).items():
        if not isinstance(key, str):
            continue
        if looks_sensitive(key):
            # Sensitive values are still redacted in the
            # preview, but we DO NOT generate a fill step for
            # them — the user must enter them manually.
            steps.append(
                StepPreview(
                    step_order=order,
                    step_type="skip_sensitive",
                    target_description=f"Skip {key} (looks sensitive)",
                    selector="",
                    input_value_redacted="[REDACTED]",
                    requires_approval=False,
                )
            )
            order += 1
            continue
        if not val:
            continue
        steps.append(
            StepPreview(
                step_order=order,
                step_type="fill",
                target_description=f"Fill {key} with {str(val)[:40]}",
                selector=_selector_for_label(key),
                input_value_redacted=redact_value(key, val),
                requires_approval=risk.requires_approval,
            )
        )
        order += 1
    if submit:
        steps.append(
            StepPreview(
                step_order=order,
                step_type="click",
                target_description="Click submit / save",
                selector="button[type=submit], input[type=submit], button:has-text('Save'), button:has-text('Submit')",
                input_value_redacted="",
                requires_approval=True,
            )
        )
        order += 1
    notes: list[str] = []
    if decision and not decision.allowed:
        notes.append(f"Domain check failed: {decision.reason}")
    if not validation.ok:
        notes.append(
            "Missing required invoice fields: " + ", ".join(validation.missing)
        )
    if risk.requires_approval:
        notes.append("User approval is required before this action can run.")
    return ActionPreview(
        action_type="fill_form" if not submit else "submit_form",
        target_url=target_url,
        target_domain=decision.host if decision else "",
        risk=risk,
        steps=steps,
        notes=notes,
        domain_decision=decision,
    )


def build_open_url_preview(
    *, target_url: str, policy: Optional[DomainPolicy] = None
) -> ActionPreview:
    p = policy or DomainPolicy.from_settings()
    decision = p.decide(target_url) if target_url else None
    risk = classify_risk(
        action_type="open_url", target_url=target_url, policy=p
    )
    notes: list[str] = []
    if decision and not decision.allowed:
        notes.append(f"Domain check failed: {decision.reason}")
    steps = [
        StepPreview(
            step_order=0,
            step_type="navigate",
            target_description=f"Open {target_url}",
            selector="",
            input_value_redacted="",
            requires_approval=risk.requires_approval,
        ),
        StepPreview(
            step_order=1,
            step_type="screenshot",
            target_description="Capture page screenshot",
            selector="",
            input_value_redacted="",
            requires_approval=False,
        ),
    ]
    return ActionPreview(
        action_type="open_url",
        target_url=target_url,
        target_domain=decision.host if decision else "",
        risk=risk,
        steps=steps,
        notes=notes,
        domain_decision=decision,
    )


def build_append_invoice_row_preview(
    *,
    target_url: str,
    invoice_payload: dict,
    policy: Optional[DomainPolicy] = None,
) -> ActionPreview:
    """Preview for "append this invoice as a row in a Google
    Sheet / web form" workflows. Fills the form, then clicks
    submit."""
    fill_preview = build_fill_form_preview(
        target_url=target_url,
        field_values=invoice_payload,
        submit=True,
        policy=policy,
    )
    fill_preview.action_type = "append_invoice_row"
    fill_preview.risk = classify_risk(
        action_type="append_invoice_row",
        target_url=target_url,
        submit=True,
        write=True,
        policy=policy,
    )
    if not fill_preview.notes:
        fill_preview.notes = []
    fill_preview.notes.append(
        "Appends a new row in the target sheet with this invoice's data."
    )
    return fill_preview


def _selector_for_label(label: str) -> str:
    """A best-effort CSS selector for a form field given its label.

    The adapter resolves the selector against the actual page at
    run time. We keep this deliberately small; sites that need
    more (XPath, aria-label, etc.) are not in the default
    allowlist."""
    safe = re.sub(r"[^a-z0-9_-]+", "_", (label or "").lower()).strip("_")
    if not safe:
        return "input, textarea"
    return (
        f"input[name={safe}], input[id={safe}], "
        f"textarea[name={safe}], textarea[id={safe}], "
        f"[aria-label='{label}']"
    )


# ---------------------------------------------------------------------------
# Browser adapter
# ---------------------------------------------------------------------------


@dataclass
class AdapterResult:
    ok: bool
    payload: dict = field(default_factory=dict)
    error: str = ""
    screenshot_path: str = ""


class BrowserAdapter:
    """Thin wrapper over the real browser (Playwright) with a
    deterministic "preview only" fallback.

    The real Playwright import is deferred until the first call
    to :meth:`open_url` / :meth:`fill_field` so the app keeps
    booting (and the sidecar can ship) without Playwright
    installed. The dry-run path is what the tests and the local
    test form use.
    """

    def __init__(self, *, headless: bool, screenshots_enabled: bool) -> None:
        self.headless = headless
        self.screenshots_enabled = screenshots_enabled
        self._playwright = None
        self._browser = None
        self._page = None
        self._mode = "dry-run"
        self._last_url: str = ""
        self._last_title: str = ""
        self._last_text: str = ""

    @property
    def mode(self) -> str:
        return self._mode

    def is_live(self) -> bool:
        return self._mode == "playwright"

    def _ensure_playwright(self) -> None:
        if self._playwright is not None:
            return
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as exc:  # pragma: no cover - import guarded
            logger.info("playwright not available; staying in dry-run: %s", exc)
            return
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless
            )
            self._page = self._browser.new_page()
            self._mode = "playwright"
            logger.info("playwright launched (headless=%s)", self.headless)
        except Exception as exc:  # pragma: no cover - environment guarded
            logger.warning("playwright launch failed; staying in dry-run: %s", exc)
            self._playwright = None
            self._browser = None
            self._page = None
            self._mode = "dry-run"

    def open_url(self, url: str) -> AdapterResult:
        self._ensure_playwright()
        self._last_url = url
        if self._mode == "playwright" and self._page is not None:
            try:
                self._page.goto(url, timeout=10_000)
                self._last_title = self._page.title() or ""
                self._last_text = (self._page.inner_text("body") or "")[:2000]
            except Exception as exc:
                return AdapterResult(ok=False, error=str(exc))
            return AdapterResult(
                ok=True,
                payload={"url": url, "title": self._last_title, "text_excerpt": self._last_text},
            )
        # Dry run.
        self._last_title = f"(dry-run) {url}"
        self._last_text = (
            "[dry-run] Playwright is not installed; the adapter is simulating page load."
        )
        return AdapterResult(
            ok=True,
            payload={
                "url": url,
                "title": self._last_title,
                "text_excerpt": self._last_text,
            },
        )

    def fill_field(self, selector: str, value: str) -> AdapterResult:
        if not selector:
            return AdapterResult(ok=True, payload={"note": "no-op (empty selector)"})
        if self._mode == "playwright" and self._page is not None:
            try:
                self._page.fill(selector, value)
            except Exception as exc:
                return AdapterResult(ok=False, error=str(exc))
            return AdapterResult(ok=True, payload={"selector": selector})
        return AdapterResult(ok=True, payload={"selector": selector, "dry_run": True})

    def click(self, selector: str) -> AdapterResult:
        if self._mode == "playwright" and self._page is not None:
            try:
                self._page.click(selector)
            except Exception as exc:
                return AdapterResult(ok=False, error=str(exc))
            return AdapterResult(ok=True, payload={"selector": selector})
        return AdapterResult(ok=True, payload={"selector": selector, "dry_run": True})

    def screenshot(self, run_id: int, step: str) -> AdapterResult:
        if not self.screenshots_enabled:
            return AdapterResult(ok=True, payload={"skipped": True})
        settings = get_settings()
        target_dir = settings.browser_snapshots_dir / f"run_{run_id}"
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return AdapterResult(ok=False, error=f"mkdir failed: {exc}")
        path = target_dir / f"{step}_{int(time.time())}.png"
        if self._mode == "playwright" and self._page is not None:
            try:
                self._page.screenshot(path=str(path))
            except Exception as exc:
                return AdapterResult(ok=False, error=str(exc))
            return AdapterResult(ok=True, screenshot_path=str(path))
        # Dry run: write a 1x1 placeholder so the file exists.
        try:
            _write_placeholder_png(path)
        except Exception as exc:
            return AdapterResult(ok=False, error=f"placeholder png failed: {exc}")
        return AdapterResult(ok=True, screenshot_path=str(path))

    def stop(self) -> None:
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:  # pragma: no cover
                pass
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:  # pragma: no cover
                pass
        self._browser = None
        self._page = None
        self._playwright = None
        self._mode = "dry-run"

    def status(self) -> dict:
        return {
            "mode": self._mode,
            "live": self.is_live(),
            "headless": self.headless,
            "screenshots_enabled": self.screenshots_enabled,
            "last_url": self._last_url,
            "last_title": self._last_title,
        }


def _write_placeholder_png(path: Any) -> None:
    """Write the smallest valid PNG (1x1 transparent) so the
    screenshot file exists in dry-run mode. 67 bytes."""
    import base64

    data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgAAIAAAUAAen63NgAAAAASUVORK5CYII="
    )
    with open(str(path), "wb") as fh:
        fh.write(data)


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------


_ADAPTER: Optional[BrowserAdapter] = None


def get_adapter() -> BrowserAdapter:
    global _ADAPTER
    if _ADAPTER is None:
        s = get_settings()
        _ADAPTER = BrowserAdapter(
            headless=s.browser_headless,
            screenshots_enabled=s.browser_screenshots_enabled,
        )
    return _ADAPTER


def reset_adapter() -> None:
    global _ADAPTER
    if _ADAPTER is not None:
        _ADAPTER.stop()
    _ADAPTER = None


# ---------------------------------------------------------------------------
# Policy service helpers
# ---------------------------------------------------------------------------


def get_or_create_policy(db) -> "BrowserAutomationPolicyRow":
    from ..models.browser_automation_policy import (
        BrowserAutomationPolicy,
        DEFAULT_ALLOWED_DOMAINS,
        DEFAULT_BLOCKED_DOMAINS,
    )

    row = db.query(BrowserAutomationPolicy).order_by(BrowserAutomationPolicy.id.asc()).first()
    if row is not None:
        return row
    settings = get_settings()
    row = BrowserAutomationPolicy(
        allowed_domains_json=list(settings.browser_allowed_domain_list)
        or list(DEFAULT_ALLOWED_DOMAINS),
        blocked_domains_json=list(settings.browser_blocked_domain_list)
        or list(DEFAULT_BLOCKED_DOMAINS),
        require_approval_for_submit=settings.browser_require_approval_for_submit,
        require_approval_for_write=settings.browser_require_approval_for_write,
        screenshots_enabled=settings.browser_screenshots_enabled,
        enabled=settings.browser_enabled,
        headless=settings.browser_headless,
        notes="Initialized by OfficePilot backend on first run.",
    )
    db.add(row)
    db.flush()
    return row


def policy_to_dict(row) -> dict:
    return {
        "id": row.id,
        "allowed_domains": list(row.allowed_domains_json or []),
        "blocked_domains": list(row.blocked_domains_json or []),
        "require_approval_for_submit": bool(row.require_approval_for_submit),
        "require_approval_for_write": bool(row.require_approval_for_write),
        "screenshots_enabled": bool(row.screenshots_enabled),
        "enabled": bool(row.enabled),
        "headless": bool(row.headless),
        "notes": row.notes or "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def policy_decision(policy_row, url: str) -> DomainDecision:
    p = DomainPolicy.from_lists(
        policy_row.allowed_domains_json or [],
        policy_row.blocked_domains_json or [],
    )
    return p.decide(url)


# ---------------------------------------------------------------------------
# Voice intent stubs
# ---------------------------------------------------------------------------


# Phase 12: voice intents that are allowed to *open* a URL but
# not to *submit / write* without an explicit UI approval step.
# Anything that maps to a write action goes through
# :func:`build_fill_form_preview` first.
VOICE_INTENTS = {
    "open_google_sheet": {
        "action_type": "open_url",
        "default_url": "https://sheets.google.com",
        "needs_approval": False,
    },
    "append_invoice_to_sheet": {
        "action_type": "append_invoice_row",
        "needs_approval": True,
    },
    "fill_invoice_test_form": {
        "action_type": "fill_form",
        "default_url": "http://127.0.0.1:8000/api/browser/test-form",
        "needs_approval": True,
    },
    "open_quickbooks_dashboard": {
        "action_type": "open_url",
        "default_url": "https://sandbox.qbo.intuit.com",
        "needs_approval": False,
        "note": "Read-only navigation. Creating accounting records is out of scope.",
    },
    "open_xero_dashboard": {
        "action_type": "open_url",
        "default_url": "https://go.xero.com",
        "needs_approval": False,
        "note": "Read-only navigation. Creating accounting records is out of scope.",
    },
    "create_quickbooks_entry": {
        "blocked": True,
        "note": "Out of scope: real accounting sync must use the API integration.",
    },
    "create_xero_entry": {
        "blocked": True,
        "note": "Out of scope: real accounting sync must use the API integration.",
    },
}


def voice_intent_preview(intent: str, *, target_url: Optional[str] = None) -> Optional[ActionPreview]:
    spec = VOICE_INTENTS.get(intent)
    if spec is None:
        return None
    if spec.get("blocked"):
        p = DomainPolicy.from_settings()
        risk = RiskAssessment(
            risk_level="high",
            requires_approval=True,
            reasons=[spec.get("note", "voice intent is blocked in this phase")],
        )
        return ActionPreview(
            action_type="blocked_voice_intent",
            target_url=target_url,
            target_domain="",
            risk=risk,
            steps=[],
            notes=[spec.get("note", "voice intent is blocked in this phase")],
        )
    url = target_url or spec.get("default_url") or ""
    if spec["action_type"] == "open_url":
        preview = build_open_url_preview(target_url=url)
    else:
        preview = build_fill_form_preview(
            target_url=url, field_values={}, submit=False
        )
        preview.notes.append(
            "Voice-driven action; will require explicit user approval before execution."
        )
    return preview


# ---------------------------------------------------------------------------
# Test form helpers
# ---------------------------------------------------------------------------


TEST_FORM_HTML = """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>OfficePilot — Local Test Web Form</title>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; max-width: 540px; margin: 32px auto; padding: 0 16px; color: #1c2024; }
    h1 { font-size: 1.4rem; margin-bottom: 4px; }
    p.lead { color: #5a6573; margin-top: 0; }
    label { display: block; margin-top: 12px; font-size: 0.9rem; font-weight: 600; }
    input { width: 100%; padding: 8px 10px; margin-top: 4px; font-size: 0.95rem; box-sizing: border-box; border: 1px solid #cbd2d9; border-radius: 4px; }
    button { margin-top: 20px; padding: 10px 16px; background: #2f6feb; color: white; border: 0; border-radius: 4px; font-size: 0.95rem; cursor: pointer; }
    button.secondary { background: #5a6573; margin-left: 8px; }
    pre { background: #f4f5f7; padding: 12px; border-radius: 4px; white-space: pre-wrap; word-break: break-word; }
    .row { display: flex; gap: 8px; }
    .row > div { flex: 1; }
  </style>
</head>
<body>
  <h1>OfficePilot — Local Test Web Form</h1>
  <p class=\"lead\">A safe target for browser automation. Filled in-memory only; nothing is sent off-host.</p>
  <form id=\"op-test-form\" onsubmit=\"return submitForm(event)\">
    <label for=\"vendor_name\">Vendor name</label>
    <input id=\"vendor_name\" name=\"vendor_name\" autocomplete=\"off\" />
    <div class=\"row\">
      <div>
        <label for=\"invoice_number\">Invoice number</label>
        <input id=\"invoice_number\" name=\"invoice_number\" autocomplete=\"off\" />
      </div>
      <div>
        <label for=\"invoice_date\">Invoice date</label>
        <input id=\"invoice_date\" name=\"invoice_date\" autocomplete=\"off\" />
      </div>
    </div>
    <div class=\"row\">
      <div>
        <label for=\"subtotal\">Subtotal</label>
        <input id=\"subtotal\" name=\"subtotal\" autocomplete=\"off\" />
      </div>
      <div>
        <label for=\"tax\">Tax</label>
        <input id=\"tax\" name=\"tax\" autocomplete=\"off\" />
      </div>
      <div>
        <label for=\"total_amount\">Total</label>
        <input id=\"total_amount\" name=\"total_amount\" autocomplete=\"off\" />
      </div>
    </div>
    <label for=\"currency\">Currency</label>
    <input id=\"currency\" name=\"currency\" autocomplete=\"off\" />
    <div>
      <button type=\"submit\" id=\"op-submit\">Save draft</button>
      <button type=\"button\" class=\"secondary\" onclick=\"resetForm()\">Reset</button>
    </div>
  </form>
  <h2>Last saved draft</h2>
  <pre id=\"op-result\">No draft saved yet.</pre>
  <script>
    function submitForm(ev) {
      ev.preventDefault();
      const f = document.getElementById('op-test-form');
      const data = Object.fromEntries(new FormData(f).entries());
      window.__lastTestFormSubmission = data;
      document.getElementById('op-result').textContent = JSON.stringify(data, null, 2);
      return false;
    }
    function resetForm() {
      document.getElementById('op-test-form').reset();
      document.getElementById('op-result').textContent = 'No draft saved yet.';
    }
  </script>
</body>
</html>
"""


def render_test_form_html() -> str:
    return TEST_FORM_HTML


def invoice_to_test_form_payload(invoice) -> dict:
    """Pull a flat payload suitable for the test form from an
    Invoice row. Returns redacted strings; callers should not
    write the raw SQLAlchemy object to the response."""
    return {
        "vendor_name": redact_value("vendor_name", getattr(invoice, "vendor_name", "") or ""),
        "invoice_number": redact_value("invoice_number", getattr(invoice, "invoice_number", "") or ""),
        "invoice_date": redact_value("invoice_date", getattr(invoice, "invoice_date", "") or ""),
        "subtotal": redact_value("subtotal", getattr(invoice, "subtotal", None)),
        "tax": redact_value("tax", getattr(invoice, "tax", None)),
        "total_amount": redact_value("total_amount", getattr(invoice, "total_amount", None)),
        "currency": redact_value("currency", getattr(invoice, "currency", "") or "USD"),
    }


def gen_idempotency_key() -> str:
    return f"op_{uuid.uuid4().hex[:12]}_{int(time.time())}"


__all__ = [
    "ACTION_RUN_STATUSES",
    "APPROVAL_STATUSES",
    "ActionPreview",
    "AdapterResult",
    "BrowserAdapter",
    "DEFAULT_ALLOWED_DOMAINS",
    "DEFAULT_BLOCKED_DOMAINS",
    "DomainDecision",
    "DomainPolicy",
    "RISK_LEVELS",
    "REQUIRED_INVOICE_FIELDS",
    "RiskAssessment",
    "SAFE_INVOICE_FIELDS",
    "SENSITIVE_FIELD_PATTERNS",
    "STEP_STATUSES",
    "StepPreview",
    "TEST_FORM_HTML",
    "ValidationResult",
    "VOICE_INTENTS",
    "build_append_invoice_row_preview",
    "build_fill_form_preview",
    "build_open_url_preview",
    "classify_risk",
    "gen_idempotency_key",
    "get_adapter",
    "get_or_create_policy",
    "invoice_to_test_form_payload",
    "looks_sensitive",
    "policy_decision",
    "policy_to_dict",
    "redact_value",
    "render_test_form_html",
    "reset_adapter",
    "validate_invoice_payload",
    "voice_intent_preview",
]
