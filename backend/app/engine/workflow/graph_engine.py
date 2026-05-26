"""GraphEngine – core execution engine (single-threaded, event-driven).

Replaces LangGraph's StateGraph with a custom run loop.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncGenerator

from app.engine.workflow.edge_processor import EdgeProcessor
from app.engine.workflow.event_handler import EventHandler
from app.engine.workflow.events import (
    GraphEngineEvent,
    GraphRunFailedEvent,
    GraphRunStartedEvent,
    GraphRunSucceededEvent,
)
from app.engine.workflow.graph import Graph
from app.engine.workflow.runtime_state import GraphRuntimeState
from app.engine.workflow.skip_propagator import SkipPropagator
from app.engine.workflow.state_manager import GraphStateManager


class GraphEngine:
    def __init__(self, graph: Graph, runtime_state: GraphRuntimeState):
        self._graph = graph
        self._runtime = runtime_state

        self._ready_queue: deque[str] = deque()
        self._state_manager = GraphStateManager()
        self._pool = runtime_state.variable_pool

        # Wire up components with callbacks
        self._skip_propagator = SkipPropagator(
            graph=self._graph,
            state_manager=self._state_manager,
            enqueue_callback=self._enqueue_node,
        )

        self._edge_processor = EdgeProcessor(
            graph=self._graph,
            state_manager=self._state_manager,
            variable_pool=self._pool,
            enqueue_callback=self._enqueue_node,
            skip_callback=self._skip_propagator.skip_branch_edge,
        )

        self._event_handler = EventHandler(
            state_manager=self._state_manager,
            variable_pool=self._pool,
            runtime_state=self._runtime,
            edge_processor=self._edge_processor,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> AsyncGenerator[GraphEngineEvent, None]:
        """Execute the workflow from root to completion.

        Yields ``GraphEngineEvent`` for each lifecycle transition.
        """
        yield GraphRunStartedEvent()

        all_node_ids = list(self._graph.nodes.keys())

        # Enqueue root node
        root = self._graph.root_node_id
        self._ready_queue.append(root)
        self._state_manager.mark_node_taken(root)

        try:
            while self._ready_queue:
                node_id = self._ready_queue.popleft()

                node = self._graph.nodes.get(node_id)
                if node is None:
                    continue

                # Execute node via BaseNode.run_async lifecycle
                async for event in node.run_async():
                    # Internal dispatch → state updates + edge processing
                    self._event_handler.handle(event)
                    # External yield → SSE translator
                    yield event

                # Edge processing may have happened during event dispatch above,
                # which enqueues subsequent nodes. Loop continues.

            # All nodes resolved
            outputs = {
                nid: self._pool.get_node_outputs(nid)
                for nid in all_node_ids
                if self._pool.get_node_outputs(nid)
            }
            yield GraphRunSucceededEvent(outputs=outputs)

        except Exception as e:
            yield GraphRunFailedEvent(error=str(e))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _enqueue_node(self, node_id: str) -> None:
        """Callback for EdgeProcessor / SkipPropagator to schedule a node."""
        if node_id not in self._ready_queue:
            self._ready_queue.append(node_id)

    @property
    def exception_count(self) -> int:
        return self._runtime.exception_count

    @property
    def graph(self) -> Graph:
        return self._graph
