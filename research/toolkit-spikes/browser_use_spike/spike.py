"""Browser-Use + Playwright spike — see README.md.

Goal: prove that the Browser-Use API surface we would integrate with
is importable, and that we can build a *spec* of a Phase 8 invoice
posting agent — without actually launching a browser or hitting a
real SaaS.

**We do not run a real browser session in this spike.** Driving a
real browser against QuickBooks / Xero / Google Sheets requires:
  1. A real account on the target SaaS.
  2. The user's explicit OAuth grant.
  3. A human-approval step in the audit log per state-changing action.

None of that belongs in a research spike. The spike is a smoke test
that the library is importable, plus a draft of the agent spec for
Phase 8 to build on.

Run:
    python spike.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def smoke_test_imports() -> dict:
    """Try to import the Browser-Use public API and report what's
    available. We do not instantiate ``Agent`` or launch a browser."""
    info = {
        "browser_use_installed": False,
        "playwright_installed": False,
        "agent_class": False,
        "controller_class": False,
        "errors": [],
    }
    try:
        import browser_use  # type: ignore
        info["browser_use_installed"] = True
        info["browser_use_version"] = getattr(browser_use, "__version__", "unknown")
    except ImportError as exc:
        info["errors"].append(f"browser_use: {exc}")
    try:
        from browser_use import Agent  # type: ignore
        info["agent_class"] = True
    except ImportError as exc:
        info["errors"].append(f"Agent: {exc}")
    try:
        from browser_use import Controller  # type: ignore
        info["controller_class"] = True
    except ImportError as exc:
        info["errors"].append(f"Controller: {exc}")
    try:
        import playwright  # type: ignore
        info["playwright_installed"] = True
        info["playwright_version"] = getattr(playwright, "__version__", "unknown")
    except ImportError as exc:
        info["errors"].append(f"playwright: {exc}")
    return info


def draft_phase8_spec() -> dict:
    """The shape of the Phase 8 agent — a written spec, not code.
    This is what we *would* build if we adopt Browser-Use."""
    return {
        "agent_name": "post_invoice_to_quickbooks",
        "phase_target": 8,
        "input": {
            "approved_invoice_id": "<int from our DB>",
            "target_saas": "<quickbooks | xero | google_sheets>",
            "user_oauth_token": "<refresh token, stored encrypted>",
        },
        "steps": [
            {
                "id": 1,
                "name": "authenticate",
                "description": "Open a browser, navigate to the SaaS, "
                               "use the stored OAuth refresh token to "
                               "obtain an access token. NEVER use a "
                               "hard-coded credential.",
                "approval_required": False,
                "audit_log": "auth.attempted",
            },
            {
                "id": 2,
                "name": "open_invoice_form",
                "description": "Navigate to the invoice creation form.",
                "approval_required": False,
                "audit_log": "nav.invoice_form",
            },
            {
                "id": 3,
                "name": "preview_post",
                "description": "Fill the form with our extracted fields. "
                               "Take a screenshot and present it to the user "
                               "for review.",
                "approval_required": False,
                "audit_log": "preview.screenshot",
            },
            {
                "id": 4,
                "name": "await_human_approval",
                "description": "Block on a user click in the React UI. "
                               "Store a pending-action token in the DB so "
                               "the workflow can resume after a crash.",
                "approval_required": True,
                "audit_log": "approval.requested",
            },
            {
                "id": 5,
                "name": "submit",
                "description": "Click 'Save' / 'Post' in the SaaS. "
                               "Take a confirmation screenshot. "
                               "Store the SaaS-side invoice ID in our DB.",
                "approval_required": True,
                "audit_log": "submit.clicked",
            },
            {
                "id": 6,
                "name": "verify",
                "description": "Navigate to the invoice list and confirm the "
                               "new row is present. Capture a final screenshot.",
                "approval_required": False,
                "audit_log": "verify.completed",
            },
        ],
        "guardrails": [
            "No real SaaS credentials in the spike or in the repo.",
            "Every state-changing step is gated by a human approval modal.",
            "Screenshots and HTML traces are written to disk and gitignored.",
            "The browser process is killed if approval is not received in N minutes.",
            "Errors cause the agent to abort and emit an audit-log entry; "
            "no partial state is committed.",
        ],
        "license_blockers": [
            "Browser-Use is MIT — fine for embedding.",
            "QuickBooks / Xero / Google Sheets ToS may restrict automated "
            "posting. The user's own OAuth grant is the legal basis; we "
            "do not bypass it.",
        ],
    }


def main() -> int:
    print("=== Browser-Use + Playwright spike ===\n")

    print("--- import smoke test ---")
    info = smoke_test_imports()
    print(json.dumps(info, indent=2))
    if not info["browser_use_installed"]:
        print(
            "\n[NEXT] To complete the install on a workstation with a real "
            "browser:\n"
            "    pip install browser-use playwright\n"
            "    playwright install chromium\n"
            "  Then re-run this spike to confirm the API is importable."
        )

    print("\n--- Phase 8 agent spec (draft) ---")
    spec = draft_phase8_spec()
    print(json.dumps(spec, indent=2))

    out_dir = HERE / "out"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "browser_use_smoke.json").write_text(
        json.dumps({"imports": info, "phase8_spec": spec}, indent=2),
        encoding="utf-8",
    )
    print(f"\n[OK] Wrote {out_dir / 'browser_use_smoke.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
