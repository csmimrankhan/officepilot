"""LangGraph spike — see README.md.

Goal: model the Phase 3 invoice approval flow as a LangGraph state
machine with a human-in-the-loop seam, and prove that the graph
correctly routes on the confidence threshold and on the human's
decision.

This is the *shape* of Phase 6. We are not wiring it into the
production app.

Run:
    python spike.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional, TypedDict

HERE = Path(__file__).resolve().parent


# ----------------------------------------------------------------- state shape


class InvoiceState(TypedDict, total=False):
    """The minimum state we need to model the Phase 3 trust layer
    as a graph. Mirrors our SQLAlchemy `Invoice` model loosely."""
    invoice_id: int
    vendor: str
    total: float
    confidence: float
    status: Literal[
        "imported",
        "extracting",
        "needs_review",
        "ready_for_approval",
        "approved",
        "rejected",
        "exported",
    ]
    approved_by: Optional[str]
    rejected_reason: Optional[str]
    audit_log: list[dict]


# ----------------------------------------------------------------- nodes


def extract_node(state: InvoiceState) -> InvoiceState:
    """Idempotent: only advances status if the invoice is still in
    pre-extraction states. This is important because LangGraph's
    default ``invoke`` does not give us real pause/resume without a
    checkpointer; we use status as the source of truth instead."""
    print(f"[extract] invoice #{state['invoice_id']} (was: {state['status']})")
    if state["status"] in ("imported", "extracting"):
        state["status"] = "ready_for_approval"
        state["audit_log"].append({
            "node": "extract",
            "from": "imported",
            "to": state["status"],
        })
    return state


def confidence_check_node(state: InvoiceState) -> InvoiceState:
    """Route low-confidence invoices to a manual review queue."""
    print(f"[confidence_check] invoice #{state['invoice_id']} confidence={state['confidence']}")
    if state["status"] == "ready_for_approval" and state["confidence"] < 0.6:
        state["status"] = "needs_review"
        state["audit_log"].append({
            "node": "confidence_check",
            "to": "needs_review",
            "reason": f"confidence {state['confidence']} < 0.6",
        })
    return state


def human_approval_node(state: InvoiceState) -> InvoiceState:
    """This node is the *seam* for the human approval step.

    In a real Phase 6 deployment, we would use LangGraph's
    ``interrupt`` primitive (or a checkpointer + resume) to pause
    here until the user clicks Approve / Reject in the React UI.
    For this spike, we accept the human's pre-set ``status`` and
    ``approved_by`` as the input.
    """
    print(
        f"[human_approval] invoice #{state['invoice_id']} -> "
        f"status={state['status']}, approved_by={state['approved_by']}"
    )
    state["audit_log"].append({
        "node": "human",
        "decision": state["status"],
        "actor": state.get("approved_by") or "system",
    })
    return state


def export_node(state: InvoiceState) -> InvoiceState:
    state["status"] = "exported"
    state["audit_log"].append({
        "node": "export",
        "to": "exported",
    })
    print(f"[export] invoice #{state['invoice_id']} marked exported")
    return state


def needs_review_node(state: InvoiceState) -> InvoiceState:
    print(f"[needs_review] invoice #{state['invoice_id']} parked for human review")
    return state


# ----------------------------------------------------------------- graph


def build_graph():
    from langgraph.graph import END, StateGraph

    g = StateGraph(InvoiceState)

    g.add_node("extract", extract_node)
    g.add_node("confidence_check", confidence_check_node)
    g.add_node("human_approval", human_approval_node)
    g.add_node("needs_review", needs_review_node)
    g.add_node("export", export_node)

    g.set_entry_point("extract")
    g.add_edge("extract", "confidence_check")

    g.add_conditional_edges(
        "confidence_check",
        lambda s: "needs_review" if s["status"] == "needs_review" else "human_approval",
        {
            "needs_review": "needs_review",
            "human_approval": "human_approval",
        },
    )

    g.add_edge("needs_review", END)

    g.add_conditional_edges(
        "human_approval",
        lambda s: "export" if s["status"] == "approved" else "end",
        {"export": "export", "end": END},
    )

    g.add_edge("export", END)
    return g.compile()


# ----------------------------------------------------------------- demos


def run(label: str, g, initial: InvoiceState) -> InvoiceState:
    print(f"\n--- {label} ---")
    final = g.invoke(initial)
    print(json.dumps(dict(final), indent=2, default=str))
    return dict(final)


def main() -> int:
    print("=== LangGraph spike: human-in-the-loop approval ===\n")

    g = build_graph()

    # Demo 1: pre-approval flow. Confidence is high; graph runs the
    # full extract → confidence_check → human_approval path and parks
    # at the seam, awaiting a human decision.
    pre_approval: InvoiceState = {
        "invoice_id": 101,
        "vendor": "ACME (Spike)",
        "total": 460.64,
        "confidence": 0.92,
        "status": "imported",
        "approved_by": None,
        "rejected_reason": None,
        "audit_log": [],
    }
    r1 = run("high-confidence invoice (pre-approval, parked at human_approval)", g, pre_approval)

    # Demo 2: post-approval flow. We re-invoke with the human's
    # decision encoded in the state. ``extract`` is idempotent, so the
    # graph resumes from ``confidence_check`` → ``human_approval`` and
    # then routes to ``export``.
    post_approval: InvoiceState = {**r1, "status": "approved", "approved_by": "alice"}
    r2 = run("same invoice, human approves (routed to export)", g, post_approval)

    # Demo 3: low-confidence invoice parks at needs_review.
    low_conf: InvoiceState = {
        "invoice_id": 202,
        "vendor": "Beta Logistics (Spike)",
        "total": 99.00,
        "confidence": 0.30,
        "status": "imported",
        "approved_by": None,
        "rejected_reason": None,
        "audit_log": [],
    }
    r3 = run("low-confidence invoice (parks at needs_review)", g, low_conf)

    out_dir = HERE / "out"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "langgraph_runs.json").write_text(
        json.dumps({"pre_approval": r1, "post_approval": r2, "needs_review": r3}, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n[OK] Wrote {out_dir / 'langgraph_runs.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
