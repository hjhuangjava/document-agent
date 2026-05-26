"""Workflow engine integration tests.

Exercises Graph + GraphEngine + EdgeProcessor + SkipPropagator + StateManager
without depending on real LLM/tool executors. Uses fake nodes that just emit
NodeRunSucceededEvent (or NodeRunFailedEvent) deterministically.
"""

from __future__ import annotations

import asyncio

from app.engine.workflow.events import (
    GraphRunStartedEvent,
    GraphRunSucceededEvent,
    NodeRunFailedEvent,
    NodeRunStartedEvent,
    NodeRunSucceededEvent,
)
from app.engine.workflow.graph import Edge, Graph
from app.engine.workflow.graph_engine import GraphEngine
from app.engine.workflow.runtime_state import GraphRuntimeState
from app.engine.workflow.variable_pool import VariablePool


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class FakeNode:
    """Minimal node that yields started + succeeded with given outputs."""

    def __init__(self, node_id: str, outputs: dict | None = None, fail: bool = False):
        self.id = node_id
        self.name = node_id
        self._outputs = outputs or {}
        self._fail = fail
        self.executed = 0

    async def run_async(self):
        self.executed += 1
        yield NodeRunStartedEvent(node_id=self.id, node_name=self.name)
        if self._fail:
            yield NodeRunFailedEvent(
                node_id=self.id, node_name=self.name, error="boom"
            )
        else:
            yield NodeRunSucceededEvent(
                node_id=self.id, node_name=self.name, outputs=self._outputs
            )


def build_graph(
    node_specs: list[tuple[str, dict]] | list[str],
    edge_specs: list[tuple],
) -> Graph:
    """Build a Graph manually.

    ``node_specs`` is either list of node ids or (id, outputs) tuples.
    ``edge_specs`` is list of (eid, tail, head) or (eid, tail, head, condition).
    """
    g = Graph()
    for spec in node_specs:
        if isinstance(spec, tuple):
            nid, outputs = spec
            g.nodes[nid] = FakeNode(nid, outputs=outputs)
        else:
            nid = spec
            g.nodes[nid] = FakeNode(nid)
        g.in_edges[nid] = []
        g.out_edges[nid] = []
        g.node_names[nid] = nid

    for spec in edge_specs:
        if len(spec) == 3:
            eid, tail, head = spec
            cond = None
        else:
            eid, tail, head, cond = spec
        edge = Edge(id=eid, tail=tail, head=head, condition=cond)
        g.edges[eid] = edge
        if tail != "__start__":
            g.out_edges.setdefault(tail, []).append(eid)
        if head != "__end__":
            g.in_edges.setdefault(head, []).append(eid)

    # Find root
    roots = [nid for nid in g.nodes if not g.in_edges.get(nid)]
    g.root_node_id = roots[0] if roots else next(iter(g.nodes))
    g._compute_back_edges()
    return g


async def run_to_completion(graph: Graph, runtime: GraphRuntimeState | None = None):
    runtime = runtime or GraphRuntimeState()
    engine = GraphEngine(graph, runtime)
    events = []
    async for evt in engine.run():
        events.append(evt)
    return events, engine


def succeeded_node_ids(events) -> list[str]:
    return [e.node_id for e in events if isinstance(e, NodeRunSucceededEvent)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_linear_chain():
    """A → B → C executes in order, all succeed."""
    g = build_graph(
        [("a", {"v": 1}), ("b", {"v": 2}), ("c", {"v": 3})],
        [("e_ab", "a", "b"), ("e_bc", "b", "c")],
    )
    events, engine = asyncio.run(run_to_completion(g))

    order = succeeded_node_ids(events)
    assert order == ["a", "b", "c"]
    assert isinstance(events[0], GraphRunStartedEvent)
    assert isinstance(events[-1], GraphRunSucceededEvent)
    assert events[-1].outputs == {"a": {"v": 1}, "b": {"v": 2}, "c": {"v": 3}}


def test_diamond_and_join():
    """A → B, A → C, B → D, C → D. D must run exactly once and only after both B and C."""
    g = build_graph(
        ["a", "b", "c", "d"],
        [
            ("e_ab", "a", "b"),
            ("e_ac", "a", "c"),
            ("e_bd", "b", "d"),
            ("e_cd", "c", "d"),
        ],
    )
    events, engine = asyncio.run(run_to_completion(g))

    order = succeeded_node_ids(events)
    # AND-join: D must come last
    assert order[-1] == "d"
    assert order.count("d") == 1
    # Both B and C must precede D
    assert order.index("b") < order.index("d")
    assert order.index("c") < order.index("d")
    assert g.nodes["d"].executed == 1


def test_diamond_with_skipped_branch():
    """A is conditional; branch to B taken, branch to C skipped.
    D depends on B and C — must still execute (1 TAKEN, 1 SKIPPED is ready)."""
    # A produces flag=True; cond1 matches → B; cond2 doesn't → C skipped
    g = build_graph(
        [("a", {"flag": True}), "b", "c", "d"],
        [
            ("e_ab", "a", "b", {"field": "flag", "operator": "eq", "value": True}),
            ("e_ac", "a", "c", {"field": "flag", "operator": "eq", "value": False}),
            ("e_bd", "b", "d"),
            ("e_cd", "c", "d"),
        ],
    )
    events, engine = asyncio.run(run_to_completion(g))

    order = succeeded_node_ids(events)
    assert "a" in order
    assert "b" in order
    assert "c" not in order  # skipped
    assert "d" in order
    assert order.index("b") < order.index("d")


def test_no_branch_match_terminates():
    """No condition matches → engine terminates with only the source node executed."""
    g = build_graph(
        [("a", {"x": 99}), "b", "c"],
        [
            ("e_ab", "a", "b", {"field": "x", "operator": "eq", "value": 1}),
            ("e_ac", "a", "c", {"field": "x", "operator": "eq", "value": 2}),
        ],
    )
    events, engine = asyncio.run(run_to_completion(g))

    order = succeeded_node_ids(events)
    assert order == ["a"]
    assert isinstance(events[-1], GraphRunSucceededEvent)


def test_back_edge_retry_loop_bounded():
    """A → B; B has conditional back-edge to A and forward to __end__.
    Back-edge retry should stop at max_retries."""
    # B always picks back-edge (cond evaluates true on field set by A)
    g = Graph()
    g.nodes = {
        "a": FakeNode("a", outputs={"flag": True}),
        "b": FakeNode("b", outputs={"done": True}),
    }
    g.in_edges = {"a": [], "b": []}
    g.out_edges = {"a": [], "b": []}
    g.node_names = {"a": "a", "b": "b"}

    edges = [
        Edge(id="e_ab", tail="a", head="b"),
        Edge(
            id="e_ba",
            tail="b",
            head="a",
            condition={"field": "flag", "operator": "eq", "value": True},
            max_retries=3,
        ),
        Edge(
            id="e_bend",
            tail="b",
            head="__end__",
            condition={"field": "flag", "operator": "eq", "value": False},
        ),
    ]
    for e in edges:
        g.edges[e.id] = e
        g.out_edges.setdefault(e.tail, []).append(e.id)
        if e.head != "__end__":
            g.in_edges.setdefault(e.head, []).append(e.id)
    g.root_node_id = "a"
    g._compute_back_edges()

    # Back-edge e_ba must be detected
    assert "e_ba" in g.back_edges
    # Forward edges should NOT be in back_edges
    assert "e_ab" not in g.back_edges

    events, engine = asyncio.run(run_to_completion(g))

    # A executed initially + max_retries times back from B
    # B always picks back-edge, but counter caps at max_retries=3
    assert g.nodes["a"].executed >= 1
    assert g.nodes["a"].executed <= 4  # 1 initial + at most 3 retries
    assert isinstance(events[-1], GraphRunSucceededEvent)


def test_failed_node_does_not_block_engine_termination():
    """Failed node's downstream never enqueues; engine still terminates."""
    g = build_graph(
        [("a", {"v": 1})],
        [("e_ab", "a", "b")],
    )
    # Replace 'a' with failing node
    g.nodes["a"] = FakeNode("a", fail=True)
    g.nodes["b"] = FakeNode("b")
    g.in_edges["b"] = ["e_ab"]
    g.out_edges["b"] = []
    g.node_names["b"] = "b"

    runtime = GraphRuntimeState()
    events, engine = asyncio.run(run_to_completion(g, runtime))

    failed = [e for e in events if isinstance(e, NodeRunFailedEvent)]
    assert len(failed) == 1
    assert failed[0].node_id == "a"
    # B never ran (no NodeRunSucceededEvent for b)
    assert "b" not in succeeded_node_ids(events)
    # Engine terminated cleanly
    assert isinstance(events[-1], GraphRunSucceededEvent)
    # Runtime tracked failure
    assert runtime.exception_count == 1
    assert "a" in runtime.failed_node_ids


def test_and_join_waits_for_both_branches():
    """Verify the AND-join fix: D should NOT execute when only one parent is done."""
    g = build_graph(
        ["a", "b", "c", "d"],
        [
            ("e_ab", "a", "b"),
            ("e_ac", "a", "c"),
            ("e_bd", "b", "d"),
            ("e_cd", "c", "d"),
        ],
    )
    events, engine = asyncio.run(run_to_completion(g))

    # D executed exactly once (would be 2 under old OR-join semantics)
    assert g.nodes["d"].executed == 1


def test_full_skip_propagation():
    """Fully unreachable downstream gets cascaded SKIPPED."""
    # A → B (cond=True path) → D
    # A → C (cond=False path) → E → F   (entire C/E/F chain unreachable)
    g = build_graph(
        [("a", {"flag": True}), "b", "c", "d", "e", "f"],
        [
            ("e_ab", "a", "b", {"field": "flag", "operator": "eq", "value": True}),
            ("e_ac", "a", "c", {"field": "flag", "operator": "eq", "value": False}),
            ("e_bd", "b", "d"),
            ("e_ce", "c", "e"),
            ("e_ef", "e", "f"),
        ],
    )
    events, engine = asyncio.run(run_to_completion(g))

    order = succeeded_node_ids(events)
    assert set(order) == {"a", "b", "d"}
    assert "c" not in order
    assert "e" not in order
    assert "f" not in order


def test_variable_pool_data_flow():
    """Outputs from node A become readable by downstream nodes via VariablePool."""
    pool = VariablePool()
    runtime = GraphRuntimeState(variable_pool=pool)

    g = build_graph(
        [("a", {"draft_content": "hello"}), "b"],
        [("e_ab", "a", "b")],
    )
    asyncio.run(run_to_completion(g, runtime))

    assert pool.get("draft_content") == "hello"
    assert pool.get_node_outputs("a") == {"draft_content": "hello"}
    assert pool.resolve_path("draft_content") == "hello"
