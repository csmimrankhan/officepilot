# Toolkit Decision Matrix

> Read with `LICENSE_NOTES.md`. "Final decision" reflects both license
> safety **and** the engineering value we measured (or could measure) on
> this machine.
>
> **Status (2026-06-05)**: Phase 5 + Phase 6 + **Phase 7** are shipped.
> - **Phase 5**: Docling + PaddleOCR are wired in behind
>   `OFFICEPILOT_PARSER_ENGINE` (default still `existing`).
> - **Phase 6**: LangGraph is now the workflow runtime for the upload
>   / email-import / excel-export pipelines, with a `WorkflowRunner`
>   that persists state to the database between nodes and pauses on
>   a human-approval checkpoint before any risky step.
> - **Phase 7**: A Windows-native Tauri 2 (MIT) shell now hosts the
>   React UI and supervises the Python FastAPI agent as a sidecar.
>   The shell adds a system tray (Open / Sync / Approvals / Settings
>   / Exit), polls `/api/health` every 15 s, and restarts the agent
>   on failure. Three new sidebar pages — **Local Agent**, **Storage**,
>   **Privacy Dashboard** — make the local-first storage model
>   visible to the user. **No** new third-party toolkit is integrated
>   for Phase 7; the shell is pure Tauri.

## At-a-glance

| # | Tool | License | Use Case | Phase | Commercial Safety | Tech Difficulty | MVP Value | Risk | Final Decision |
|---|------|---------|----------|-------|-------------------|-----------------|-----------|------|----------------|
| 1 | Docling | MIT | PDF/table/layout parsing | 5 | ✅ Safe | Medium | High | Low | **Adopt (Phase 5)** |
| 2 | PaddleOCR | Apache-2.0 | OCR for scanned images | 5 | ✅ Safe | Medium | Medium | Medium (binary, size) | **Adopt, optional (Phase 5)** |
| 3 | LangGraph | MIT | Durable workflow + HITL | 6 | ✅ Safe | Medium-High | High | Low | **Adopt (Phase 6)** |
| 4 | Browser-Use + Playwright | MIT / Apache-2.0 | Browser automation | 8 | ✅ Safe (lib) / ⚠️ ToS risk (sites) | High | High | High (ToS, prompt injection) | **Adopt with guardrails (Phase 8)** |
| 5 | OpenAdapt | MIT | GUI workflow recording | 9 | ✅ Safe (lib) / ⚠️ Privacy risk (data) | High | Medium | High (screen capture) | **Defer, local-only (Phase 9)** |
| 6 | self-operating-computer | MIT | Vision-action loop | 10 | ✅ Safe (lib) / ⚠️ Loop risk | High | Low | Very High (mouse takeover) | **Reference only (Phase 10)** |
| 7 | Open Interpreter | **AGPL-3.0** | NL computer/code exec | n/a | ❌ Copyleft | High | Medium | **Critical** | **Never integrate directly** |
| 8 | TaskWeaver | MIT | Code-first data workflows | 6/8 | ✅ Safe | Medium | Low-Medium | Low | **Optional (Phase 6/8)** |
| 9 | Tauri 2 | MIT / Apache-2.0 | Windows desktop shell + sidecar supervisor | 7 | ✅ Safe | Medium | High (UX) | Low | **Adopt (Phase 7)** |

## What "MVP Value" means here

A tool's MVP value is the **incremental, shippable user benefit** for an
SME accountant using OfficePilot AI — *not* novelty. A high-value tool
saves a real workflow; a low-value tool is technically interesting but
doesn't justify the maintenance cost.

- **High** — directly accelerates a real Phase 3 user action
  (e.g. faster extraction, fewer manual edits, durable approval
  state, browser-based posting to QuickBooks).
- **Medium** — useful for a specific subset of users (e.g. native OCR
  for shops that ban cloud OCR).
- **Low** — interesting in a demo, doesn't move the product forward
  for the target user.

## What "Risk" means here

Composite of:

- **Security** (prompt injection, network calls, data exfiltration).
- **Operational** (large downloads, GPU, model churn).
- **Legal** (license, third-party ToS).
- **UX** (silent actions, transparency, reversibility).

## Decisions, line by line

### 1. Docling — **Adopt (Phase 5)**
Strong fit: we already have a PDF parser; Docling's table-aware
extraction should reduce manual line-item entry. MIT license is clean.
Integration difficulty is medium because we must run Docling as a
sidecar or in a worker, not in the FastAPI request thread.

### 2. PaddleOCR — **Adopt, optional (Phase 5)**
Already ship Tesseract (Apache-2.0). PaddleOCR is a drop-in alternative
that often handles noisy scans better, but it ships a 100+ MB model.
Keep Tesseract as the default and add PaddleOCR as an opt-in option
in the Folder/Extraction settings.

### 3. LangGraph — **Adopt (Phase 6)**
Our Phase 3 trust layer is essentially a state machine
(`imported → extracting → ready_for_approval → approved → exported`).
LangGraph formalizes that, plus gives us durable resume after
crash, retries, and human-in-the-loop nodes. MIT, safe.

### 4. Browser-Use + Playwright — **Adopt with guardrails (Phase 8)**
This is the only realistic path to push approved invoices into
QuickBooks Online / Xero without us writing and maintaining per-vendor
integrations. The library is MIT, but the **legal** risk lives in the
ToS of the target site. Default behavior must be:
1. User connects their own SaaS account (OAuth where possible).
2. Every state-changing action is gated by an in-app approval modal.
3. The audit log records the action, the user, and a screenshot.
4. We never hard-code credentials to a SaaS in the product.

### 5. OpenAdapt — **Defer, local-only (Phase 9)**
OpenAdapt is the only realistic path to "record once, replay forever"
workflows for the legacy desktop apps accountants still use. License
is fine. The risk is **screen capture** — recordings of a bank login,
payroll screen, or CRM contain PII. Defer until we have a local-only
mode, encryption at rest for recordings, and a clear consent flow.

### 6. self-operating-computer — **Reference only (Phase 10)**
We are not adopting a vision-action loop in production. The risk
profile is wrong for a financial product:
- prompt injection via the screen,
- non-deterministic actions,
- no per-action approval.
We may keep it as a README reference for educational purposes.

### 7. Open Interpreter — **Never integrate directly**
AGPL-3.0. The "use the network = distribute" clause makes a
commercial, multi-user, or SaaS-shaped product unsafe. If a similar
capability is needed, build a small in-house LLM-tool loop with our
existing MIT/Apache dependencies and pin the model locally.

### 8. TaskWeaver — **Optional**
Pandas handles the Excel transformations we need today. If Phase 6/8
produces custom data workflows that have grown messy, TaskWeaver is
a sane upgrade. We are not adopting it now.

### 9. Tauri 2 — **Adopt (Phase 7)**
Licensed MIT / Apache-2.0 (split between the framework core and
individual plugins). Tauri is the lightest way to ship a native
Windows shell that embeds the existing React UI and supervises the
Python agent as a child process, without pulling in Electron
(~150 MB runtime, GPL-style concerns about Chromium bundling) or
shipping a separate .NET host. The supervisor is plain Rust with
`std::process::Command` + a TCP-connect health probe; no extra
runtime deps.

Phase 7 ships only the **shell + sidecar + tray + health
supervisor**. It does **not** add full desktop control (no
global hotkeys, no screen capture, no UI automation), so the
risk profile stays close to the web app. The next phases can
add: bundled-Python sidecar, MSI code signing, auto-updates,
and (much later) optional workflow recording via OpenAdapt.

## Next phase ordering

Based on the matrix above:

1. **Phase 5 — Better extraction**: Docling + (optional) PaddleOCR.
2. **Phase 6 — Durable workflow**: LangGraph, layered on top of
   Phase 3 status machine.
3. **Phase 7 — Local desktop shell**: Tauri 2, with system tray,
   sidecar supervisor, and a privacy/storage dashboard. **DONE.**
4. **Phase 8 — Browser automation**: Browser-Use + Playwright, with
   the guardrails in the Browser-Use note.
5. **Phase 9 — Workflow recording**: OpenAdapt, local-only.
6. **Phase 10 — Reference**: self-operating-computer stays as a
   research artifact, not a product feature.

## What to update this matrix with

When we actually adopt a tool in a later phase, add a row at the
bottom:

```
| 9 | <tool> | <SPDX> | <use> | <phase adopted> | <verdict> | ... | <evidence> |
```

This keeps the matrix useful as a living document, not a snapshot.
