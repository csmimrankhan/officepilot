# Open Interpreter — ⚠️ AGPL-3.0 — DO NOT INTEGRATE

> **This document is the canonical AGPL warning for OfficePilot AI.**
> The license review in `LICENSE_NOTES.md` is the source of truth;
> this file is the long-form version with concrete examples.

## What it is

Open Interpreter is a popular open-source project that lets a
language model execute code and shell commands on a local machine.
You give it a goal in natural language; it proposes shell commands,
Python snippets, or browser actions; it asks for your approval; and
it runs them.

It is one of the best-known implementations of the
"approval-before-code" UX pattern.

## License

**AGPL-3.0.**

This is a copyleft license with a network clause. The "network clause
is distribution" wording is the part that breaks commercial products.

## Why we are not adopting it

The AGPL-3.0 says, in summary:

> If you modify the program and you make it available over a network
> to users, you must offer the entire corresponding source —
> including your modifications and any "derivative work" — to those
> users.

For a single-user desktop product this is a tolerable burden. For a
multi-user product, a SaaS, or any distribution that involves users
other than the developer, AGPL-3.0 is a hard problem.

Concretely, in the OfficePilot AI context:

| Integration shape | AGPL impact |
|---|---|
| Import `interpreter` from `app/` | **Hard copyleft on our product.** Any user with network access to OfficePilot AI (including a hosted future version) would be entitled to our source. |
| Spawn `interpreter` as a subprocess that exchanges data with our backend | Same — the combined work is the user's perspective. |
| Bundle the `interpreter` CLI in our installer | Same. |
| Use `interpreter` only on a developer's local machine, never ship it | **OK** for internal use. **Not OK** for a distributed product. |
| Read the Open Interpreter source for inspiration, write our own clean-room implementation | **OK.** This is the recommended path. |

The "separate optional service" workaround that some teams reach for
**does not save us**. The AGPL's "use over a network" clause
applies to the combined work, not to a single binary.

## What we *do* take from Open Interpreter

The library has genuinely good UX ideas that are worth re-implementing
in our own clean-room code:

1. **Approval-before-code.** The model proposes a shell command; the
   user sees a diff and clicks "Run" or "Skip". We should adopt this
   pattern in any Phase 8+ work that involves executing user-driven
   code (e.g. Excel transformations, custom data workflows).
2. **Local-first by default.** Open Interpreter runs locally. We
   should default to local for any code execution.
3. **Model-agnostic.** Open Interpreter is not coupled to a single
   LLM vendor. We should keep our model layer vendor-agnostic too.
4. **Explicit modes.** Open Interpreter distinguishes "chat", "code",
   and "shell" modes. We may want a similar "what kind of action is
   this?" distinction in our agent layer.

These are **patterns**, not code. We can implement all four in ~200
lines of our own code without touching the AGPL library.

## What we explicitly do *not* do

- We do **not** add `open-interpreter` to `backend/requirements.txt`.
- We do **not** import `interpreter` from anywhere in `app/`.
- We do **not** invoke the `interpreter` CLI from our backend.
- We do **not** document a "how to use Open Interpreter with
  OfficePilot AI" path in the product docs.

## What we *do* do, to honour the project's good ideas

- We cite Open Interpreter in our Phase 4 notes as a source of UX
  inspiration.
- We may, in a later phase, build a small `LocalToolAgent` class that
  implements the approval-before-code pattern, with our own audit
  log integration, and document it as "inspired by Open Interpreter".
- We track the project's license on every dependency upgrade. If
  Killian / OpenInterpreter contributors ever offer a commercial
  license, we revisit this decision.

## Alternatives we *do* use

| Need | Use this | License |
|---|---|---|
| Workflow orchestration with HITL | LangGraph | MIT |
| Code execution in a sandbox | `subprocess` with a restricted env, or `RestrictedPython` | PSF / ZPL |
| Data workflows | pandas (BSD), or TaskWeaver (MIT) | permissive |
| Browser automation | Browser-Use + Playwright | MIT / Apache-2.0 |
| LLM tool-use loop | Our own ~200-line clean-room implementation | ours |

## Recommendation

**Never integrate Open Interpreter directly into OfficePilot AI.**
If a similar capability becomes product-critical, we build it
in-house, and we cite Open Interpreter in the source comments.
