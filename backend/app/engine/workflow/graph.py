"""Graph model – node/edge representation and topology factory."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.engine.workflow.enums import NodeState

if TYPE_CHECKING:
    from app.engine.workflow.node_base import BaseNode
    from app.engine.workflow.runtime_state import GraphRuntimeState


@dataclass
class Edge:
    id: str
    tail: str               # source node id
    head: str               # target node id
    source_handle: str = "source"
    condition: dict | None = None
    max_retries: int = 3
    state: NodeState = NodeState.UNKNOWN


class Graph:
    nodes: dict[str, BaseNode]
    edges: dict[str, Edge]            # edge_id → Edge
    in_edges: dict[str, list[str]]    # node_id → incoming edge_ids
    out_edges: dict[str, list[str]]   # node_id → outgoing edge_ids
    root_node_id: str
    node_names: dict[str, str]        # node_id → display name
    back_edges: set[str]              # edge_ids that close cycles (retry loops)

    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.in_edges = {}
        self.out_edges = {}
        self.node_names = {}
        self.back_edges = set()

    def forward_in_edges(self, node_id: str) -> list[str]:
        """Incoming edges excluding back-edges (cycle-closing edges).

        Used for AND-join readiness so that retry/back-edges still UNKNOWN
        do not gate forward execution.
        """
        return [
            eid for eid in self.in_edges.get(node_id, [])
            if eid not in self.back_edges
        ]

    def _compute_back_edges(self) -> None:
        """DFS from root; mark edges pointing to a node currently on the stack
        as back-edges."""
        self.back_edges = set()
        visited: set[str] = set()
        on_stack: set[str] = set()

        def dfs(nid: str) -> None:
            visited.add(nid)
            on_stack.add(nid)
            for eid in self.out_edges.get(nid, []):
                edge = self.edges[eid]
                head = edge.head
                if head == "__end__":
                    continue
                if head in on_stack:
                    self.back_edges.add(eid)
                elif head not in visited:
                    dfs(head)
            on_stack.discard(nid)

        if getattr(self, "root_node_id", None):
            dfs(self.root_node_id)

    @classmethod
    def from_topology(
        cls,
        topology: dict[str, Any],
        node_factory,
        runtime_state: GraphRuntimeState,
    ) -> Graph:
        """Build a Graph from a topology dict (NodeDef / EdgeDef JSON).

        ``topology`` contains ``{"nodes": [...], "edges": [...]}`` where each
        entry is a JSON-serialised NodeDef / EdgeDef dictionary.
        """
        g = cls()

        # --- Register nodes via factory ---
        for node_cfg in topology.get("nodes", []):
            node = node_factory(node_cfg, runtime_state)
            g.nodes[node.id] = node
            g.in_edges.setdefault(node.id, [])
            g.out_edges.setdefault(node.id, [])

        # --- Register edges ---
        for edge_cfg in topology.get("edges", []):
            eid = edge_cfg.get("id", f"e_{edge_cfg['source']}_{edge_cfg['target']}")
            edge = Edge(
                id=eid,
                tail=edge_cfg["source"],
                head=edge_cfg["target"],
                source_handle=edge_cfg.get("sourceHandle") or (
                    edge_cfg["condition"]["value"]
                    if edge_cfg.get("condition")
                    else "source"
                ),
                condition={
                    "field": edge_cfg["condition"]["field"],
                    "operator": edge_cfg["condition"]["operator"],
                    "value": edge_cfg["condition"]["value"],
                }
                if edge_cfg.get("condition")
                else None,
                max_retries=edge_cfg.get("max_retries", 3),
            )
            g.edges[eid] = edge

            # Wire in/out edges (use internal node ids; __start__ / __end__ are special)
            tail = edge.tail
            head = edge.head
            if tail != "__start__":
                g.out_edges.setdefault(tail, []).append(eid)
            if head != "__end__":
                g.in_edges.setdefault(head, []).append(eid)

        # --- Find root node(s) ---
        # Prefer the target of an explicit __start__ edge; otherwise fall back
        # to nodes with no incoming edges.
        root_id = None
        for edge in g.edges.values():
            if edge.tail == "__start__":
                root_id = edge.head
                break

        if root_id is None:
            # Find nodes whose incoming-edge list is truly empty
            roots = [
                nid for nid in g.nodes
                if not g.in_edges.get(nid)
            ]
            if not roots:
                raise ValueError("No root node found – check topology edges")
            root_id = roots[0]  # first root node
        g.root_node_id = root_id

        # --- Build node name map ---
        g.node_names = {
            n["id"]: n.get("name", n["id"])
            for n in topology.get("nodes", [])
        }

        # --- Detect back-edges (cycle-closing) for retry loops ---
        g._compute_back_edges()

        return g
