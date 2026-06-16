"""Phase 6 — graph runner.

Drives any registered LangGraph workflow one node at a time and
persists state to the database between nodes. The runner is the
*only* thing that touches the DB; the node handlers are pure
state-in / state-out functions that operate on the dict directly.

Why the split? Two reasons:

1. **Testability.** A handler that takes a runner can be unit-tested
   with a fake runner that captures log rows and approval calls.
2. **One place for the audit/approval side effects.** The runner
   always writes a ``workflow_logs`` row after a node completes and
   always checks for pending approvals before the next node, so no
   individual handler has to remember.

The LangGraph graph itself is built and compiled by
:mod:`app.services.workflows.registry`. We don't use the LangGraph
runtime's checkpointer; we persist state to our own
:class:`WorkflowRun` row.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from ...models.workflow_approval import ApprovalStatus, WorkflowApproval
from ...models.workflow_log import NodeLogStatus, WorkflowLog
from ...models.workflow_run import WorkflowRun, WorkflowStatus
from .registry import get_graph

logger = logging.getLogger(__name__)


NodeHandler = Callable[[dict, "WorkflowRunner"], dict]


class WorkflowRunner:
    """Drives one :class:`WorkflowRun` through its graph."""

    def __init__(self, db: Session, run: WorkflowRun, settings: Any = None) -> None:
        self.db = db
        self.run = run
        self.spec = get_graph(run.workflow_name)
        self.settings = settings

    # -------------------------------------------------------------- DB helpers

    def mark_status(
        self,
        status: WorkflowStatus,
        *,
        error_message: Optional[str] = None,
        completed: bool = False,
    ) -> None:
        self.run.status = status.value
        if error_message is not None:
            self.run.error_message = error_message
        if completed:
            self.run.completed_at = datetime.utcnow()
        self.db.add(self.run)
        self.db.commit()

    def append_log(
        self,
        node_name: str,
        status: NodeLogStatus,
        message: Optional[str] = None,
        data: Optional[dict] = None,
    ) -> None:
        self.db.add(WorkflowLog(
            workflow_run_id=self.run.id,
            node_name=node_name,
            status=status.value,
            message=message,
            data_json=data or {},
        ))
        self.db.commit()

    def pending_approval(self, node_name: str) -> Optional[WorkflowApproval]:
        return (
            self.db.query(WorkflowApproval)
            .filter(
                WorkflowApproval.workflow_run_id == self.run.id,
                WorkflowApproval.node_name == node_name,
                WorkflowApproval.status == ApprovalStatus.PENDING.value,
            )
            .order_by(WorkflowApproval.id.desc())
            .first()
        )

    def create_approval(
        self,
        node_name: str,
        message: str,
        *,
        before: Optional[dict] = None,
        after: Optional[dict] = None,
    ) -> WorkflowApproval:
        row = WorkflowApproval(
            workflow_run_id=self.run.id,
            node_name=node_name,
            approval_message=message,
            before_data_json=before,
            after_data_json=after,
            status=ApprovalStatus.PENDING.value,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def save_state(self, state: dict, current_node: Optional[str] = None) -> None:
        self.run.state_json = state
        if current_node is not None:
            self.run.current_node = current_node
        self.db.add(self.run)
        self.db.commit()

    def _load_state(self) -> dict:
        """Read the persisted state_json and return it as a dict."""
        import json as _json
        raw = self.run.state_json
        if not raw:
            return {}
        if isinstance(raw, dict):
            return dict(raw)
        return _json.loads(raw)

    # -------------------------------------------------------------- main loop

    def advance(
        self,
        handlers: dict[str, NodeHandler],
        *,
        from_node: Optional[str] = None,
    ) -> dict:
        """Run the graph from ``from_node`` (or ``current_node`` /
        start) up to the next approval checkpoint, error, or
        terminal node. Returns the final state.

        The runner stops early if it hits a handler that called
        :meth:`create_approval` — in that case the run is marked
        ``awaiting_approval`` and we return the state.
        """
        # Starting point.
        if from_node is None:
            from_node = self.run.current_node or self.spec.start

        # Pending-approval guard: if a previous run halted at
        # ``from_node``, do not re-execute that node; wait for an
        # approve / reject.
        if self.run.current_node == from_node and self.pending_approval(from_node):
            return self._load_state()

        # Initial state: prefer the persisted state_json (for
        # retries / resumption), but on the very first run fall
        # back to the run's input_json so the first node has
        # access to the workflow input.
        if self.run.state_json:
            state: dict = self._load_state()
        elif self.run.input_json:
            import json as _json
            raw = self.run.input_json
            state = raw if isinstance(raw, dict) else _json.loads(raw)
        else:
            state = {}
        node_names = self.spec.node_names
        try:
            start_idx = node_names.index(from_node)
        except ValueError:
            self.mark_status(
                WorkflowStatus.FAILED,
                error_message=f"unknown node: {from_node!r}",
                completed=True,
            )
            return state

        self.run.status = WorkflowStatus.RUNNING.value
        self.run.error_message = None
        self.db.add(self.run)
        self.db.commit()

        for node_name in node_names[start_idx:]:
            handler = handlers.get(node_name)
            if handler is None:
                # No handler means "no-op" (e.g. an end marker).
                self.append_log(node_name, NodeLogStatus.SKIPPED, message="no handler")
                self.save_state(state, node_name)
                continue

            self.run.current_node = node_name
            self.save_state(state, node_name)
            self.append_log(node_name, NodeLogStatus.OK, message="started")
            try:
                update = handler(state, self) or {}
            except Exception as exc:  # handler crashed
                logger.exception("node %s raised", node_name)
                self.append_log(
                    node_name, NodeLogStatus.FAILED, message=str(exc)
                )
                self.mark_status(
                    WorkflowStatus.FAILED,
                    error_message=f"{node_name}: {exc}",
                    completed=True,
                )
                return {**state, "error": str(exc)}

            state = {**state, **update}
            # If a node returned an error marker, halt the run with
            # status FAILED so the operator can retry. We log the
            # error and keep the partial state for inspection.
            if state.get("error"):
                self.append_log(
                    node_name, NodeLogStatus.FAILED,
                    message=f"node returned error: {state['error']}",
                )
                self.mark_status(
                    WorkflowStatus.FAILED,
                    error_message=f"{node_name}: {state['error']}",
                    completed=True,
                )
                return state
            self.save_state(state, node_name)

            # Did this node create a pending approval? If so, halt.
            if self.pending_approval(node_name):
                self.append_log(
                    node_name, NodeLogStatus.AWAITING_APPROVAL,
                    message="awaiting human approval",
                )
                self.mark_status(WorkflowStatus.AWAITING_APPROVAL)
                return state

            self.append_log(node_name, NodeLogStatus.OK, message="ok")

        # All nodes done.
        self.run.current_node = None
        self.mark_status(WorkflowStatus.COMPLETED, completed=True)
        return state

    def cancel(self, *, reason: Optional[str] = None, actor: str = "user") -> dict:
        self.mark_status(
            WorkflowStatus.CANCELLED,
            error_message=reason or "cancelled by user",
            completed=True,
        )
        self.append_log("__cancel__", NodeLogStatus.SKIPPED, message=f"cancelled by {actor}")
        return self._load_state()

    def reject(self, node_name: str, *, actor: str, note: Optional[str] = None) -> dict:
        """Mark the run rejected because the user rejected the
        pending approval at ``node_name``. We mark the approval
        row rejected, mark the run rejected, and skip ahead."""
        approval = self.pending_approval(node_name)
        if approval is None:
            raise ValueError(f"no pending approval at node {node_name!r}")
        approval.status = ApprovalStatus.REJECTED.value
        approval.approved_by = actor
        approval.approved_at = datetime.utcnow()
        approval.decision_note = note
        self.db.add(approval)
        self.db.commit()
        self.append_log(node_name, NodeLogStatus.OK, message=f"rejected by {actor}: {note or ''}")
        self.mark_status(
            WorkflowStatus.REJECTED,
            error_message=f"rejected at {node_name}: {note or ''}",
            completed=True,
        )
        return self._load_state()


__all__ = ["WorkflowRunner", "NodeHandler", "WorkflowStatus", "NodeLogStatus", "ApprovalStatus"]
