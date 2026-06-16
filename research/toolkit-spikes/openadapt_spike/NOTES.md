# OpenAdapt — Notes Only

> Phase 9 candidate. **No runnable spike** is shipped with Phase 4
> because OpenAdapt captures the user's screen, mouse, and keyboard
> — and we do not want raw screen recordings in the repo, even
> synthetic ones, without a privacy review.

## What it is

OpenAdapt is an MIT-licensed open-source framework for **GUI
workflow recording and replay**: a human performs a task once on
their desktop, OpenAdapt records the screen pixels, mouse events,
keyboard events, and window metadata, and a multimodal model learns
to reproduce the task.

It is the only realistic path to "record once, replay forever"
workflows for the legacy desktop apps accountants still use (legacy
ERP, in-house tools, etc.).

## Install

```bash
pip install openadapt
# Optional but recommended: a local multimodal model server
# (e.g. an OpenAI-compatible local server, or Ollama).
```

OpenAdapt's own setup is multi-step (Python deps + a model backend).
Read the upstream docs carefully before installing.

## What we did *not* do

- We did **not** install OpenAdapt in this spike. The license is fine
  (MIT, see `LICENSE_NOTES.md`); the *risk* is the data it captures.
- We did **not** record a real screen session.
- We did **not** upload any screenshots or recordings to a cloud
  model.

## What worked (research)

- The OpenAdapt repository and docs are public, MIT, and well
  documented. The architecture is sound: a recorder captures
  `(screen, mouse, keyboard, window)` tuples, a multimodal model
  learns the policy, a runner replays it.
- The license is permissive — fine for a commercial product.
- It is the only open-source project in this space that ships a
  end-to-end recording → replay pipeline.

## What failed / open questions

- **Privacy**: recordings of a bank login, payroll screen, or CRM
  contain PII. We need a local-only mode, encryption at rest, and a
  consent flow before we can ship this. None of that exists upstream.
- **Cost**: a multimodal model that can read the screen well is
  expensive (vision tokens). Per-replay costs add up.
- **Robustness**: GUI automations are notoriously brittle when a
  vendor changes a button label or layout. We do not have a clear
  answer from the OpenAdapt project on long-term replay stability.
- **Local model quality**: open multimodal models (e.g. LLaVA,
  Qwen-VL) are improving but still trail GPT-4V on dense desktop
  UIs.

## Security / privacy

- Recordings are PII. We must never:
  - upload recordings to a cloud model by default,
  - log raw screen pixels in the audit trail,
  - replay a workflow that touches credentials without an explicit
    re-auth step.
- Phase 9 work should add a **screen-capture consent banner** and
  an **exclusion list** (e.g. "do not record when the active window
  is `1Password` or a banking site").

## Performance

- Recording: ~1-5 GB of disk per hour of activity, depending on
  frame rate and resolution.
- Training: hours, on a single GPU.
- Replay: ~1-3x the human's original time.

## Recommendation

**Defer to Phase 9.** Do the privacy + cost work *before* we install
or integrate. By the time we get to Phase 9 we should also have a
clear answer on whether the open multimodal models have caught up to
GPT-4V on dense desktop UIs.
