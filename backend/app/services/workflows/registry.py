"""Phase 6 — graph registry.

A :class:`GraphSpec` bundles a compiled LangGraph ``StateGraph``
with a small dict of "node handlers" — Python callables the runner
uses to step through the graph and write per-node log rows.

The reason we don't just call ``app.stream()`` on the LangGraph
graph is persistence + audit: we need a row per node transition,
and we need a clean place to interrupt for human approval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from .invoice_upload import (
    INVOICE_UPLOAD_NODES,
    InvoiceUploadState,
    build_invoice_upload_graph,
)
from .email_import import (
    EMAIL_IMPORT_NODES,
    EmailImportState,
    build_email_import_graph,
)
from .excel_export import (
    EXCEL_EXPORT_NODES,
    ExcelExportState,
    build_excel_export_graph,
)
from .browser_automation import (
    BROWSER_AUTOMATION_NODES,
    build_browser_automation_graph,
)

logger = logging.getLogger(__name__)


@dataclass
class GraphSpec:
    """A compiled LangGraph graph + a flat list of node names +
    handlers in execution order. The runner walks ``node_names``;
    each handler does the work for that node and returns the
    partial state update (which is then merged with the current
    state and persisted)."""

    name: str
    description: str
    # Compiled graph — used to compute edges / start node ordering.
    compiled: Any
    # Ordered list of node names (the runner walks this).
    node_names: list[str]
    # Node name → (state_in, runner) -> state_update callable.
    handlers: dict[str, Callable[[dict, Any], dict]]
    # Start node (entry point of the graph).
    start: str
    # End sentinel (we treat the runner's "no next node" as END).
    end: str = END

    @property
    def node_handlers_dict(self) -> dict[str, Callable[[dict, Any], dict]]:
        """Alias for clarity when passing to the runner."""
        return self.handlers

    @property
    def state_type(self) -> type:
        # We don't need this for the runner; it's only for
        # documentation / IDE help.
        return dict


GRAPHS: dict[str, GraphSpec] = {}


def _register(spec: GraphSpec) -> None:
    GRAPHS[spec.name] = spec


def _make_invoice_upload_spec() -> GraphSpec:
    g, nodes = build_invoice_upload_graph()
    return GraphSpec(
        name="invoice_upload_processing",
        description="Parse a single uploaded invoice: store, dedupe, parse, validate, route by confidence, create review item, audit.",
        compiled=g,
        node_names=INVOICE_UPLOAD_NODES,
        handlers=nodes,
        start="store_file",
    )


def _make_email_import_spec() -> GraphSpec:
    g, nodes = build_email_import_graph()
    return GraphSpec(
        name="email_invoice_import",
        description="Pull invoice attachments from a connected Gmail account, score, download, process, create review items, audit.",
        compiled=g,
        node_names=EMAIL_IMPORT_NODES,
        handlers=nodes,
        start="check_email_connection",
    )


def _make_excel_export_spec() -> GraphSpec:
    g, nodes = build_excel_export_graph()
    return GraphSpec(
        name="approved_invoice_export",
        description="Export approved invoices to Excel with a mandatory human approval checkpoint; organize files and mark exported on success.",
        compiled=g,
        node_names=EXCEL_EXPORT_NODES,
        handlers=nodes,
        start="select_approved_invoices",
    )


def _make_browser_automation_spec() -> GraphSpec:
    g, handlers, nodes = build_browser_automation_graph()
    return GraphSpec(
        name="browser_automation",
        description=(
            "Phase 12: drive a (Playwright-backed or dry-run) browser "
            "through prepare -> domain check -> preview -> approval -> "
            "execute -> validate -> audit log. Every risky action "
            "requires explicit user approval and writes to the audit log."
        ),
        compiled=g,
        node_names=nodes,
        handlers=handlers,
        start="browser_prepare",
    )


_register(_make_invoice_upload_spec())
_register(_make_email_import_spec())
_register(_make_excel_export_spec())
_register(_make_browser_automation_spec())


def get_graph(name: str) -> GraphSpec:
    if name not in GRAPHS:
        raise KeyError(f"unknown workflow: {name!r}")
    return GRAPHS[name]


def list_graphs() -> list[dict]:
    return [
        {"name": g.name, "description": g.description, "nodes": g.node_names}
        for g in GRAPHS.values()
    ]


__all__ = [
    "GraphSpec",
    "GRAPHS",
    "get_graph",
    "list_graphs",
    "InvoiceUploadState",
    "EmailImportState",
    "ExcelExportState",
    "BROWSER_AUTOMATION_NODES",
    "build_browser_automation_graph",
    "START",
    "END",
]
