"""GraphStateManager – tracks node/edge states and determines readiness."""

from __future__ import annotations

from app.engine.workflow.enums import NodeState


class GraphStateManager:
    def __init__(self):
        self._node_states: dict[str, NodeState] = {}
        self._edge_states: dict[str, NodeState] = {}
        self._executing_nodes: set[str] = set()

    # ------------------------------------------------------------------
    # Node state
    # ------------------------------------------------------------------

    def set_node_state(self, node_id: str, state: NodeState) -> None:
        self._node_states[node_id] = state

    def get_node_state(self, node_id: str) -> NodeState:
        return self._node_states.get(node_id, NodeState.UNKNOWN)

    def mark_node_taken(self, node_id: str) -> None:
        self._node_states[node_id] = NodeState.TAKEN

    def mark_node_skipped(self, node_id: str) -> None:
        self._node_states[node_id] = NodeState.SKIPPED

    # ------------------------------------------------------------------
    # Edge state
    # ------------------------------------------------------------------

    def set_edge_state(self, edge_id: str, state: NodeState) -> None:
        self._edge_states[edge_id] = state

    def get_edge_state(self, edge_id: str) -> NodeState:
        return self._edge_states.get(edge_id, NodeState.UNKNOWN)

    def mark_edge_taken(self, edge_id: str) -> None:
        self._edge_states[edge_id] = NodeState.TAKEN

    def mark_edge_skipped(self, edge_id: str) -> None:
        self._edge_states[edge_id] = NodeState.SKIPPED

    # ------------------------------------------------------------------
    # Execution tracking
    # ------------------------------------------------------------------

    def mark_executing(self, node_id: str) -> None:
        self._executing_nodes.add(node_id)

    def mark_completed(self, node_id: str) -> None:
        self._executing_nodes.discard(node_id)

    def is_executing(self, node_id: str) -> bool:
        return node_id in self._executing_nodes

    # ------------------------------------------------------------------
    # Readiness checks
    # ------------------------------------------------------------------

    def is_node_ready(
        self,
        node_id: str,
        in_edge_ids: list[str],
    ) -> bool:
        """AND-join: a node is ready when NO incoming edge is UNKNOWN
        and at least one is TAKEN.

        Callers should pass *forward* incoming edges (excluding back-edges)
        so that retry/back-edges still UNKNOWN do not block forward execution.
        """
        if not in_edge_ids:
            return False

        # All incoming edges must be resolved (no UNKNOWN)
        if any(self.get_edge_state(eid) == NodeState.UNKNOWN for eid in in_edge_ids):
            return False

        # At least one must be TAKEN (not all SKIPPED)
        return self.has_taken_incoming(node_id, in_edge_ids)

    def is_all_incoming_skipped(
        self,
        node_id: str,
        in_edge_ids: list[str],
    ) -> bool:
        """Check whether every incoming edge to *node_id* is SKIPPED."""
        if not in_edge_ids:
            return False
        return all(
            self.get_edge_state(eid) == NodeState.SKIPPED
            for eid in in_edge_ids
        )

    def has_taken_incoming(
        self,
        node_id: str,
        in_edge_ids: list[str],
    ) -> bool:
        """Check whether any incoming edge to *node_id* is TAKEN."""
        return any(
            self.get_edge_state(eid) == NodeState.TAKEN
            for eid in in_edge_ids
        )

    # ------------------------------------------------------------------
    # Completion
    # ------------------------------------------------------------------

    def is_execution_complete(self, all_node_ids: list[str]) -> bool:
        """Execution is complete when all nodes are resolved and nothing is executing."""
        if self._executing_nodes:
            return False
        for nid in all_node_ids:
            if self.get_node_state(nid) == NodeState.UNKNOWN:
                return False
        return True
