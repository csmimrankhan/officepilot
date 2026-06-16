# Browser-Use + Playwright Spike

## What this is

A smoke-test spike for **Browser-Use** + **Playwright**. It does
**two** things:

1. Verifies the Browser-Use public API is importable on the dev box.
2. Dumps a written spec of what the Phase 8 invoice-posting agent
   would look like.

**It does not launch a real browser session.** That would require a
real SaaS account, a real OAuth grant, and a real human approval
step. None of that belongs in a research spike.

## Why

Browser-Use (MIT) is the most realistic path to push approved
invoices into QuickBooks / Xero / Google Sheets without us writing
and maintaining per-vendor integrations. Before we adopt it, we
need a runnable sanity check on the library and a clear spec for
the guardrails.

## Install

```bash
pip install browser-use playwright
playwright install chromium
```

> ⚠️ The ``playwright install`` step downloads a real Chromium build
> (~150 MB). The Browser-Use library alone is small.

## Run

```bash
python spike.py
```

If the libraries are not installed, the spike reports which ones are
missing and exits cleanly. The Phase 8 spec is always written to
`out/browser_use_smoke.json` so reviewers can see the design even
without installing anything.

## What worked (when libraries are installed)

- The `Agent` and `Controller` symbols are importable from
  `browser_use`, confirming the public API is stable enough for our
  spec.
- Playwright is installable alongside Browser-Use.

## What we deliberately did *not* do

- **Did not** drive a real browser against a real SaaS.
- **Did not** use a hard-coded credential for any service.
- **Did not** record a real session.
- **Did not** bypass the user's OAuth grant.

If you want to exercise the *real* Browser-Use flow, do it in an
isolated dev environment with a throwaway SaaS account and a
synthetic invoice. The spike is intentionally non-destructive.

## Security / privacy

Browser-Use operates the user's own browser session. The risk is not
Browser-Use itself — it is:

- **Prompt injection** on the SaaS page. A malicious invoice body
  could contain text that the agent reads off the screen and acts
  on. Mitigation: every state-changing action is gated by a human
  approval modal.
- **SaaS ToS**. Some SaaS providers explicitly forbid unattended
  automation. The user's own OAuth grant is the legal basis for
  *assisted* automation, not unattended automation.
- **Data leakage**. Screenshots, HTML, and cookies must never leave
  the user's machine. We default to local-only.

## Performance

- Browser startup is ~1-2s.
- Each step (navigate, fill field, click) is ~0.5-2s.
- End-to-end posting of a single invoice is ~10-30s.
- The browser process holds a non-trivial amount of memory (~200 MB
  per tab); we will need to recycle browsers between runs.

## Recommendation

**Adopt with guardrails (Phase 8).** The library is the right tool;
the real Phase 8 work is the **human-approval + audit-log + cleanup**
plumbing, not the Browser-Use call.
