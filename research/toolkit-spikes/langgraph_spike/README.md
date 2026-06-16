# LangGraph Spike

## What this is

A self-contained spike that models the **Phase 3 invoice approval
workflow** as a LangGraph state machine with a human-in-the-loop
pause, and proves the graph can be **interrupted and resumed**.

It does **not** touch the production `backend/` code. It only depends
on `langgraph` and runs entirely in-memory.

## Why

Our Phase 3 trust layer is essentially a state machine:
`imported → extracting → ready_for_approval → approved → exported`
(with side-paths for `needs_review`, `rejected`, and `duplicate`).
LangGraph formalizes this, gives us **durable resume after a crash**,
**retries**, and **typed human-in-the-loop nodes** — three things we
do not have today.

This spike is the prototype that decides whether Phase 6 is worth
adopting.

## Install

```bash
pip install langgraph
```

This is a quick install (~30 s) — no GPU, no large model weights.

## Run

```bash
python spike.py
```

The spike runs two scenarios end-to-end:

1. **High-confidence invoice, human approves.**
   The graph runs `extract → confidence_check → human_approval`,
   pauses for the human decision, then resumes into `export`.
2. **Low-confidence invoice, parks at needs_review.**
   The graph short-circuits to a `needs_review` terminal node.

The two final states are written to `out/langgraph_runs.json`.

## What worked

- Modelling the Phase 3 state machine as a graph: 5 nodes, 7 edges.
- The conditional edges correctly route on the confidence threshold.
- The "human_approval" node is a clean seam: the graph pauses there,
  the spike simulates a human decision by mutating state, and the
  graph resumes from that point onward.
- The `audit_log` field accumulates one entry per node, which is the
  shape we need for our `AuditLog` table in Phase 6.

## What failed / could not be measured here

- We did not wire up **real persistence** (SQLite checkpointer).
  `langgraph-checkpoint-sqlite` is the canonical store and would be
  Phase 6 work.
- We did not wire up **real human-in-the-loop interrupts** with the
  newer `interrupt()` API; we simulated them by mutating state
  between two `invoke()` calls. Both are valid patterns; the
  production spike would use the real API.
- We did not test the **time-travel** features of LangGraph (replay
  from a checkpoint). That belongs in Phase 6.

## Security / privacy

- Pure in-memory state. Nothing leaves the process.
- The spike uses synthetic invoice data (`../sample_fixtures/`).

## Performance

- The graph runs in microseconds for the synthetic input. Real
  invoice processing latency will be dominated by the LLM node (if
  we add one in Phase 6) or the file organizer (already a Phase 3
  feature).

## Recommendation

**Adopt (Phase 6)**. The spike fits our existing model cleanly: the
graph is a thin, typed, observable layer on top of the same status
machine we already have, and the human-in-the-loop primitive is
exactly what our Phase 3 trust layer was reaching for.
