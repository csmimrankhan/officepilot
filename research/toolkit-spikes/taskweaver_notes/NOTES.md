# TaskWeaver — Optional

> Optional Phase 6/8 candidate. We are **not** adopting TaskWeaver
> now; we are documenting why and under what conditions we would.

## What it is

TaskWeaver (Microsoft, MIT) is a code-first agent framework for data
workflows. You describe a task in natural language; TaskWeaver
generates a Python plan, executes the plan against your data, and
returns the result. It is designed for "I have a CSV, a SQL
database, and an Excel report; turn them into an answer."

It is conceptually similar to Open Interpreter (and shares the
"approval-before-code" pattern) but with a stronger focus on
**structured data** rather than arbitrary shell commands.

## License

**MIT.** Clean. Safe to embed in a commercial product. See
`LICENSE_NOTES.md` for the full review.

## Why we are not adopting it now

We do not yet have a use case that demands it. Our current Excel
export (`backend/app/services/excel_export.py`) is ~120 lines of
pandas + openpyxl, and it works. Our future reporting needs (Phase 7)
are well-served by pandas.

Adopting TaskWeaver now would mean:

- A new runtime (TaskWeaver is not a library, it's a service).
- A new LLM dependency (TaskWeaver is model-bound — it needs a
  capable LLM to plan).
- New failure modes (LLM-generated code can be wrong, slow, or
  expensive).

We do not have the user need yet.

## When we *would* adopt it

A clear signal that pandas is no longer enough is when one of the
following happens:

1. **Custom Excel transforms grow past ~500 lines** in
   `excel_export.py` and start to need conditional logic, joins
   across many sheets, and per-user rules.
2. **Users start asking for "if this vendor, then this column"
   style conditional reports.** That is exactly the
   "code-first data workflow" shape TaskWeaver is good at.
3. **A user wants to upload their own CSV / Excel template** and
   have us populate it. Pandas can do this; TaskWeaver can do it
   without us writing a custom code path per template.

If any of those happen, we revisit this document.

## Security / privacy

- TaskWeaver executes generated Python in a sandbox. The default
  sandbox is the same process; for an SME product we would want a
  per-task subprocess with a restricted environment, no network
  access, and a timeout.
- Generated code can leak data if it logs or prints sensitive
  values. We would need to redact.

## Performance

- Each plan/execute round-trip is ~5-15s with a hosted LLM, plus the
  actual data-processing time.
- For large DataFrames the LLM-generated code is often slower than
  hand-written pandas because the model defaults to row-iteration.
- A local LLM (e.g. Llama-3-8B-instruct) is fast enough for the
  planning step but its code is often buggy.

## Recommendation

**Optional.** Defer until a Phase 6/8 user need makes pandas
insufficient. When that happens, run a small spike against a
synthetic dataset first (similar to the LangGraph and Docling
spikes) before any production integration.
