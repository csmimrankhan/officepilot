# self-operating-computer — Reference Only

> Phase 10 reference. We are **not** adopting a vision-action loop
> in production. This is a notes-only deliverable so future
> engineers understand *why*.

## What it is

`self-operating-computer` (MIT) is a thin reference implementation
of a vision-action loop:

1. Capture a screenshot of the user's desktop.
2. Send the screenshot to a multimodal model (e.g. GPT-4V) with a
   natural-language goal.
3. Parse the model's response into a mouse + keyboard action.
4. Execute the action with PyAutoGUI.
5. Repeat.

It is the same general shape as OpenAdapt, but **simpler** — there
is no recording/replay, just a live "look at the screen, decide what
to click" loop.

## Install

```bash
pip install self-operating-computer
# Requires PyAutoGUI and a multimodal model API key.
```

## Why we are not adopting it

Three reasons, in order of importance:

1. **No per-action approval.** A vision-action loop is *fundamentally*
   non-interactive. The model sees a screen, decides to click
   something, and the click happens. There is no clean place to put a
   "are you sure?" modal in the middle of a 5-action task. Phase 3's
   trust layer is built around that modal.

2. **Prompt injection on the screen.** If the user has a malicious
   email open in another window, and the screen-recording pass
   happens to include that window, the model may interpret the
   email's content as instructions. This is not hypothetical — it
   has been demonstrated in the research literature.

3. **Cost and latency.** Multimodal tokens are 2-10x more expensive
   than text tokens, and the loop is many turns per task. A
   30-second task at GPT-4V pricing is real money for a product that
   needs to be priced for SME accountants.

## What we *do* take from it

The reference loop is a clean way to think about screen automation
as a state machine:

```
(screenshot, goal) → multimodal_model → action → execute → new_screenshot
```

We are not implementing this loop in production. We may, however,
**cite it in Phase 9** as the simplest possible "what would a
vision-action loop look like?" reference, and contrast it with the
OpenAdapt recording/replay approach (which is more deterministic and
reviewable).

## Security / privacy

- The model sees the user's screen. If the model is cloud-hosted, it
  sees everything: bank balances, customer lists, salaries. This is
  not acceptable for a financial product without an on-prem model
  and a screen-content redaction layer.
- PyAutoGUI runs in the user's session, so the action space is
  effectively the entire OS. There is no sandbox.

## Performance

- Per-turn latency: 1-3s (model) + ~50 ms (PyAutoGUI).
- Cost per turn: ~$0.01-0.05 with a hosted vision model, much less
  with a local model.
- Reliability: a fully autonomous loop is brittle; in practice you
  need a human "abort" hotkey and a watchdog.

## Recommendation

**Reference only.** Do not adopt. If we ever want a vision-action
loop for non-financial tasks (e.g. "open this PDF in the user's
default reader"), we should:

- Constrain the goal to a single, well-defined action,
- Run the model locally, not in the cloud,
- Require a human "Go" click before any mouse move, and
- Show a live preview of the screen capture to the user.

None of those are in the upstream library. We would build them
in-house.
