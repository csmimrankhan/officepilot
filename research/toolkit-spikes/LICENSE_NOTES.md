# License Notes — Toolkit-by-Toolkit Review

> ⚠️ **Read this before any integration decision.** This document is the
> canonical license review for Phase 4. When in doubt, defer to legal
> counsel — these notes are engineering opinion, not legal advice.

## TL;DR

| Toolkit | License (SPDX) | Commercial verdict | Adopt? |
|---|---|---|---|
| Docling | MIT | ✅ Safe | Yes (Phase 5) |
| PaddleOCR | Apache-2.0 | ✅ Safe | Yes, optional (Phase 5) |
| LangGraph | MIT | ✅ Safe | Yes (Phase 6) |
| Browser-Use | MIT | ✅ Safe (network risk, not license) | Yes (Phase 8) |
| OpenAdapt | MIT (server) + Apache-2.0 (some modules) | ✅ Safe (desktop-control risk) | Later (Phase 9) |
| self-operating-computer | MIT | ✅ Safe (vision-loop risk) | Reference only (Phase 10) |
| Open Interpreter | **AGPL-3.0** | ❌ Direct integration = copyleft on the whole product | **Never, directly** |
| TaskWeaver | MIT | ✅ Safe | Optional (Phase 6/8) |

The big yellow flag is **Open Interpreter (AGPL-3.0)**. Everything else is
permissive and fine to embed in a commercial product, subject to
attribution.

---

## 1. Docling — MIT

- **SPDX**: `MIT`
- **Copyright**: IBM Research and contributors.
- **Commercial use**: ✅ Permitted, including proprietary SaaS. Attribution
  required.
- **Distribution**: Linking statically or dynamically is fine. No copyleft
  on our product.
- **Third-party deps**: Docling pulls in `pypdfium2`, `transformers`,
  PyTorch. These are also permissive (Apache-2.0 / BSD). Verify any
  model weights' licenses before shipping.
- **Recommendation**: Adopt. Phase 5 candidate.

## 2. PaddleOCR — Apache-2.0

- **SPDX**: `Apache-2.0`
- **Copyright**: PaddlePaddle Authors and contributors.
- **Commercial use**: ✅ Permitted. Explicit patent grant. Attribution
  required.
- **Distribution**: The Apache-2.0 grant of patent rights is a meaningful
  plus over MIT for a vendor that ships models in a desktop product.
- **Third-party deps**: ONNX runtime (MIT), OpenCV (Apache-2.0), and
  PaddlePaddle inference engine (Apache-2.0).
- **Recommendation**: Adopt, optional, as a fallback OCR. Tesseract
  (Apache-2.0) remains the default for transparency.

## 3. LangGraph — MIT

- **SPDX**: `MIT`
- **Copyright**: LangChain, Inc. and contributors.
- **Commercial use**: ✅ Permitted. No copyleft. LangChain also sells
  a hosted "LangGraph Platform" — using the open-source library does
  **not** require it.
- **Third-party deps**: `langchain-core` (MIT), `pydantic` (MIT).
- **Distribution**: Library-style use. No service-side obligations.
- **Recommendation**: Adopt. Phase 6 candidate for human-in-the-loop
  workflows.

## 4. Browser-Use — MIT

- **SPDX**: `MIT`
- **Copyright**: Browser-Use contributors.
- **Commercial use**: ✅ Permitted. **But** it drives a real browser via
  Playwright, so the legal question is not Browser-Use's license — it is
  the ToS of whatever site you drive (QuickBooks, Xero, Google Sheets).
- **Distribution**: The library is MIT, but you may be acting on the
  user's behalf against third-party SaaS. Always record a human
  approval step in the audit log before any state-changing action.
- **Third-party deps**: Playwright (Apache-2.0), `pydantic` (MIT).
- **Recommendation**: Adopt, with strict guardrails. Phase 8 candidate.

## 5. OpenAdapt — MIT (+ some Apache-2.0 modules)

- **SPDX**: Mixed `MIT` for the core engine and `Apache-2.0` for some
  utilities. Verify on a per-file basis before release.
- **Copyright**: OpenAdapt contributors.
- **Commercial use**: ✅ Permitted. The license is fine.
- **Risk profile**: OpenAdapt captures screen pixels, mouse moves, and
  window metadata. **The license is not the risk; the data is.** Always
  run with explicit user consent, on a synthetic training set, and
  never upload screen recordings to a cloud endpoint by default.
- **Recommendation**: Defer. Phase 9 candidate, after a dedicated
  privacy review and a local-only mode.

## 6. self-operating-computer — MIT

- **SPDX**: `MIT`
- **Copyright**: OthersideAI contributors.
- **Commercial use**: ✅ Permitted. The library is a thin loop that
  pairs a vision-capable model (e.g. GPT-4V) with PyAutoGUI. The license
  is fine; the **cost, latency, and prompt-injection surface** of
  a vision loop are the risks.
- **Recommendation**: Treat as **reference only** for Phase 10. We are
  not adopting a vision-action loop in production.

## 7. Open Interpreter — ⚠️ **AGPL-3.0**

- **SPDX**: `AGPL-3.0`
- **Copyright**: Killian Lucas and contributors.
- **Commercial use**: ❌ **Direct integration is not safe.**
  The AGPL's "network use is distribution" clause means that if we link
  Open Interpreter into OfficePilot AI and ship the result, we would be
  obligated to offer the entire corresponding source — including any
  modifications and any private orchestration code that "uses" the
  library over a network — to every user, including SaaS users.
- **What "direct integration" means here**:
  - Importing `interpreter` from `app/`.
  - Spawning Open Interpreter as a subprocess that exchanges data
    with our backend.
  - Bundling the Open Interpreter CLI in our installer.
  - Loading its plugins, agents, or model configs.
- **What is OK**:
  - Reading the Open Interpreter source code for inspiration on UX
    patterns (approval-before-code, local-first LLM loops).
  - Citing it in docs.
  - Re-implementing its ideas in our own clean-room code.
- **Workarounds that do NOT make it safe**:
  - "We will only call it from a separate optional service that
    users install themselves." This is still distribution to a
    user; the AGPL attaches to the combined work.
  - "We will only use it locally and not ship it." This is fine
    for internal use, but not for a commercial product that we
    distribute.
- **Recommendation**: **Never integrate directly.** Inspiration and
  research only. If we ever want similar capability, we either
  negotiate a commercial license with Killian / OpenInterpreter
  contributors, or build a small in-house LLM-tool-loop with the
  MIT/Apache pieces we already use.

## 8. TaskWeaver — MIT

- **SPDX**: `MIT`
- **Copyright**: Microsoft and contributors.
- **Commercial use**: ✅ Permitted. The license is fine.
- **Third-party deps**: Requires an LLM provider (OpenAI, Azure OpenAI,
  or a local model). The cost of running it on every Excel report is
  a real consideration; pandas is still faster and cheaper for
  most jobs.
- **Recommendation**: Optional. Only adopt if Phase 6/8 work discovers
  custom pandas scripts that have grown unmaintainable.

---

## Patterns we apply regardless of license

1. **No cloud by default.** Every spike and (future) integration must
   work fully offline. Cloud features are explicit opt-in.
2. **No silent calls.** Every action that hits a third-party service
   is gated by a human approval step and recorded in the audit log.
3. **Sample data only.** Real client invoices, screenshots, or
   workflow recordings are never stored in the repo.
4. **Pinned versions.** When we adopt a library, we pin to a specific
   version in `requirements.txt` and review upgrades.
5. **Vet the model weights.** OCR/embedding model weights often have
   their own license. We document the model + license in the spike
   notes.
