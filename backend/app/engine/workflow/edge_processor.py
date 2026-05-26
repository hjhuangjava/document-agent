"""EdgeProcessor – handles post-node-success edge traversal and branch routing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from app.engine.workflow.enums import NodeState

if TYPE_CHECKING:
    from app.engine.workflow.graph import Graph
    from app.engine.workflow.state_manager import GraphStateManager
    from app.engine.workflow.variable_pool import VariablePool


class EdgeProcessor:
    def __init__(
        self,
        graph: Graph,
        state_manager: GraphStateManager,
        variable_pool: VariablePool,
        enqueue_callback: Callable[[str], None],
        skip_callback: Callable[[str], None],
    ):
        self._graph = graph
        self._sm = state_manager
        self._pool = variable_pool
        self._enqueue = enqueue_callback
        self._skip = skip_callback

    def process_node_success(self, node_id: str) -> None:
        """Process outgoing edges of *node_id*.

        Non-conditional edges are marked TAKEN immediately.
        Conditional edges are handled by ``_process_branch`` (one TAKEN, rest SKIPPED).
        """
        out_ids = self._graph.out_edges.get(node_id, [])
        cond_edge_ids = {
            eid for eid in out_ids if self._graph.edges[eid].condition
        }

        # --- Plain (non-conditional) edges ---
        for eid in out_ids:
            if eid in cond_edge_ids:
                continue  # handled by _process_branch

            edge = self._graph.edges[eid]
            if edge.head == "__end__":
                self._sm.mark_edge_taken(eid)
                continue

            self._sm.mark_edge_taken(eid)
            target = edge.head
            in_ids = self._graph.forward_in_edges(target)
            if self._sm.is_node_ready(target, in_ids):
                self._enqueue(target)

        # --- Conditional (branch) edges ---
        if cond_edge_ids:
            cond_edges = [(eid, self._graph.edges[eid]) for eid in cond_edge_ids]
            self._process_branch(node_id, cond_edges)

    def _process_branch(
        self,
        node_id: str,
        cond_edges: list[tuple[str, object]],
    ) -> None:
        """Evaluate conditions and select the matching branch edge.

        The first matching edge gets TAKEN; all other conditional edges are
        skip-propagated.  Non-conditional outgoing edges (if any) are processed
        normally via ``process_node_success`` logic.
        """
        # Evaluate conditions — first match wins
        selected_eid: str | None = None
        for eid, edge in cond_edges:
            if self._eval_condition(edge.condition):
                selected_eid = eid
                break

        max_retries = max((e.max_retries for _, e in cond_edges), default=3)

        if selected_eid is None:
            # No condition matched — go to END
            return

        selected_edge = self._graph.edges[selected_eid]

        # Back-edge retry guard
        meta = self._pool.get_system("_meta", {})
        count = meta.get(node_id, 0)
        if selected_edge.head != "__end__" and count >= max_retries:
            # Max retries exceeded; route to END instead
            self._sm.mark_edge_taken(selected_eid)
            # Skip all other conditional edges
            for eid, edge in cond_edges:
                if eid != selected_eid:
                    self._skip(eid)
            return

        # Increment retry counter for back-edges
        if selected_edge.head != "__end__":
            meta[node_id] = count + 1
            self._pool.set_system("_meta", meta)

        # Mark selected edge as TAKEN
        self._sm.mark_edge_taken(selected_eid)
        target = selected_edge.head
        in_ids = self._graph.forward_in_edges(target)
        if self._sm.is_node_ready(target, in_ids):
            self._enqueue(target)

        # Skip all non-selected conditional edges
        for eid, edge in cond_edges:
            if eid != selected_eid:
                self._skip(eid)

    # ------------------------------------------------------------------
    # Condition evaluation (mirrors builder._eval_condition)
    # ------------------------------------------------------------------

    def _eval_condition(self, cond: dict) -> bool:
        field_path = cond["field"]
        operator = cond["operator"]
        expected = cond["value"]
        actual = self._pool.resolve_path(field_path)

        ops = {
            "eq": lambda a, b: a == b,
            "ne": lambda a, b: a != b,
            "gt": lambda a, b: a is not None and b is not None and a > b,
            "lt": lambda a, b: a is not None and b is not None and a < b,
            "gte": lambda a, b: a is not None and b is not None and a >= b,
            "lte": lambda a, b: a is not None and b is not None and a <= b,
            "in": lambda a, b: a in b if isinstance(b, list) else False,
            "contains": lambda a, b: b in a if isinstance(a, str) else False,
        }
        return ops.get(operator, lambda a, b: False)(actual, expected)
