"""SkipPropagator – recursively mark downstream nodes as SKIPPED when a branch
edge is not taken."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from app.engine.workflow.debug_log import wflog
from app.engine.workflow.enums import NodeState

if TYPE_CHECKING:
    from app.engine.workflow.graph import Graph
    from app.engine.workflow.state_manager import GraphStateManager


class SkipPropagator:
    def __init__(
        self,
        graph: Graph,
        state_manager: GraphStateManager,
        enqueue_callback: Callable[[str], None],
    ):
        self._graph = graph
        self._sm = state_manager
        self._enqueue = enqueue_callback

    def skip_branch_edge(self, edge_id: str) -> None:
        """Mark *edge_id* as SKIPPED and recursively propagate downstream."""
        self._sm.mark_edge_skipped(edge_id)

        edge = self._graph.edges[edge_id]
        target_id = edge.head

        if target_id == "__end__":
            return

        edge_src = edge.tail
        wflog(f"  edge SKIPPED: {edge_src} -> {target_id}")

        in_edges = self._graph.forward_in_edges(target_id)

        # If all incoming (forward) are SKIPPED → node is unreachable
        if self._sm.is_all_incoming_skipped(target_id, in_edges):
            self._sm.mark_node_skipped(target_id)
            wflog(f"  node SKIPPED (all incoming skipped): {target_id}")

            # Recursively skip all outgoing edges
            for out_eid in self._graph.out_edges.get(target_id, []):
                self.skip_branch_edge(out_eid)

        # AND-join: enqueue only when no UNKNOWN forward incoming remain
        # and at least one is TAKEN (and the node hasn't already executed).
        elif (
            self._sm.get_node_state(target_id) != NodeState.TAKEN
            and self._sm.is_node_ready(target_id, in_edges)
        ):
            wflog(f"    ✓ READY (after skip) → enqueue {target_id}")
            self._enqueue(target_id)
